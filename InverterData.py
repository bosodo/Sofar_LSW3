#!/usr/bin/python3
# Script gathering solar data from Sofar Solar Inverter (K-TLX) via logger module LSW-3/LSE
# by Michalux (based on DEYE script by jlopez77, HA initial code by pablolite).
# Version: 2.1
#
import json
import re
import sys
from datetime import datetime
import paho.mqtt.client as paho

from sofar.sofar import Sofar
from sofar.helpers import get_config, get_parameters, p_metrics, prepare_influx_data, \
    write_to_influxdb, prepare_domoticz_data, write_to_log_file, write_debug, publish_to_mqtt, twos_complement_hex


def main():
    config = get_config()
    inverter = Sofar(
        config.get('SofarInverter', 'inverter_ip'),
        config.getint('SofarInverter', 'inverter_port'),
        config.getint('SofarInverter', 'inverter_sn')
    )

    lang = config.get('SofarInverter', 'lang', fallback='EN')
    verbose = config.get('SofarInverter', 'verbose', fallback='0')
    debug = config.get('SofarInverter', 'debug', fallback='0')
    log_file = config.get('SofarInverter', 'log_file', fallback='InverterData.log')
    prometheus = config.get('Prometheus', 'prometheus', fallback='0')
    prometheus_file = config.get('Prometheus', 'prometheus_file')
    influxdb = config.get('InfluxDB', 'influxdb', fallback='0')
    domoticz_support = config.get('Domoticz', 'domoticz_support', fallback='0')
    home_assistant_support = config.get('HomeAssistant', 'homeassistant_support', fallback='0')
    mqtt = config.get('MQTT', 'mqtt', fallback='0')

    log = open(log_file, "a")
    write_debug(log, "Script start", debug)

    inv_status = 1
    try:
        inverter.connect()
        write_debug(log, "Inverter connected successfully!", debug)
    except Exception as e:
        print(f"Could not connect to inverter: {e}")
        write_to_log_file(log, f"Could not connect to inverter: {e}")
        inv_status = 0

    data_store = {'total_power': 0, 'total_time': 0, 'output_parts': [], 'processed_data': {}}
    p_data = []
    d_data = []
    ha_data = []

    parameters = get_parameters('./SOFARMap.xml')

    if inv_status == 1:
        for i, reg_range in enumerate([
            (int(config.get('SofarInverter', 'register_start1', fallback='0'), 0),
             int(config.get('SofarInverter', 'register_end1', fallback='0'), 0)),
            (int(config.get('SofarInverter', 'register_start2', fallback='0'), 0),
             int(config.get('SofarInverter', 'register_end2', fallback='0'), 0))
        ]):
            pini, pfin = reg_range
            if pini == 0 or pfin == 0:
                continue

            try:
                response = inverter.send_request(pini, pfin)
                if verbose == "1": print(f"Received data chunk {i + 1}: {response}")
            except Exception as e:
                print(f"Could not read data from inverter: {e}")
                write_to_log_file(log, f"Could not read data from inverter: {e}")
                inv_status = 0
                break

            a = 0
            while a <= pfin - pini:
                p1 = 56 + (a * 4)
                p2 = 60 + (a * 4)
                hexpos = str("0x") + str(hex(a + pini)[2:].zfill(4)).upper()
                res = twos_complement_hex(
                    str(''.join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(response)))[p1:p2], hexpos)

                for parameter in parameters:
                    for item in parameter["items"]:
                        if hexpos in item["registers"]:
                            process_item(item, res, lang, verbose, prometheus, domoticz_support,
                                         home_assistant_support, p_data, d_data, ha_data, log, data_store)
                a += 1

    output = "{" + ",".join(data_store['output_parts']) + "}"
    if inv_status > 0:
        json_output = json.loads(output)
        print("*** JSON output:")
        print(json.dumps(json_output, indent=4, sort_keys=False, ensure_ascii=False))

    if prometheus == "1" and inv_status == 1:
        with open(prometheus_file, "w") as f:
            f.writelines(p_data)

    if influxdb == "1":
        if_data = [{"measurement": "InverterData", "time": str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
                    "fields": {}}]
        if inv_status == 1:
            for key, value in data_store['processed_data'].items():
                prepare_influx_data(if_data, key, value)
        else: # inv_status == 0
            for parameter in parameters:
                for item in parameter["items"]:
                    if item["graph"] == 1:
                        key = f"{item['metric_name'].split('_')[0]}_{item['label_value']}"
                        prepare_influx_data(if_data, key, 0)
        write_to_influxdb(config, if_data)

    if mqtt == "1":
        handle_mqtt(config, output, d_data, ha_data, inv_status, log)

    if inverter.client:
        inverter.disconnect()
    write_debug(log, "Script end", debug)
    log.close()


def process_item(item, res, lang, verbose, prometheus, domoticz, ha, p_data, d_data, ha_data, log, data_store):
    title = item[f"title{lang.upper()}"]
    ratio = item["ratio"]
    unit = item["unit"]
    graph = item["graph"]
    metric_name = item["metric_name"]
    label_name = item["label_name"]
    label_value = item["label_value"]
    metric_type = item["metric_type"]
    domoticz_idx = item["DomoticzIdx"]
    hexpos = item["registers"][0]

    res = round(res * ratio, 2)
    original_res = res

    for option in item["optionRanges"]:
        if option["key"] == res:
            if label_name == "Status" and res != 2:
                write_to_log_file(log, f"Inverter not ready. Status code: {res}")
            res = f'"{option[f"value{lang.upper()}"]}"'

    key = f"{metric_name.split('_')[0]}_{label_value}"

    def add_output(o_title, o_unit, o_value):
        if o_unit != "":
            data_store['output_parts'].append(f'"{o_title} ({o_unit})":{o_value}')
        else:
            data_store['output_parts'].append(f'"{o_title}":{o_value}')

    if hexpos not in ['0x0015', '0x0016', '0x0017', '0x0018']:
        add_output(title, unit, res)
        if verbose == "1": print(f"{hexpos} - {title}: {res}{unit}")
        if graph == 1: data_store['processed_data'][key] = original_res
        if prometheus == "1" and graph == 1:
            p_data.append(p_metrics(metric_name, metric_type, label_name, label_value, original_res))
        if domoticz == "1" and domoticz_idx > 0:
            prepare_domoticz_data(d_data, domoticz_idx, res)
        if ha == "1":
            ha_data.append([title, ratio, unit, metric_type, metric_name, label_name, label_value, original_res, hexpos])

    if hexpos == '0x0015': data_store['total_power'] += res * 65536
    if hexpos == '0x0016':
        data_store['total_power'] += res
        total_power_val = data_store['total_power']
        add_output(title, unit, total_power_val)
        if verbose == "1": print(f"{hexpos} - {title}: {total_power_val}{unit}")
        if graph == 1: data_store['processed_data'][key] = total_power_val
        if prometheus == "1" and graph == 1:
            p_data.append(p_metrics(metric_name, metric_type, label_name, label_value, total_power_val * 1000))
        if ha == "1":
            ha_data.append([title, ratio, unit, metric_type, metric_name, label_name, label_value, total_power_val, total_power_val * 1000])

    if hexpos == '0x0017': data_store['total_time'] += res * 65536
    if hexpos == '0x0018':
        data_store['total_time'] += res
        total_time_val = data_store['total_time']
        add_output(title, unit, total_time_val)
        if verbose == "1": print(f"{hexpos} - {title}: {total_time_val}{unit}")
        if graph == 1: data_store['processed_data'][key] = total_time_val
        if prometheus == "1" and graph == 1:
            p_data.append(p_metrics(metric_name, metric_type, label_name, label_value, total_time_val))
        if ha == "1":
            ha_data.append([title, ratio, unit, metric_type, metric_name, label_name, label_value, total_time_val, total_time_val])


def handle_mqtt(config, output, d_data, ha_data, inv_status, log):
    if inv_status == 1:
        if config.get('MQTT', 'mqtt_basic') == "1":
            if not publish_to_mqtt(config, config.get('MQTT', 'mqtt_topic'), output):
                write_to_log_file(log, "Error publishing basic data to MQTT")
        if config.get('Domoticz', 'domoticz_support') == "1":
            for mqtt_data in d_data:
                if not publish_to_mqtt(config, config.get('Domoticz', 'domoticz_mqtt_topic'), mqtt_data, retain=True):
                    write_to_log_file(log, "Error publishing data for Domoticz to MQTT")
        if config.get('HomeAssistant', 'homeassistant_support') == "1":
            publish_ha_mqtt(config, ha_data, log)
    else: # inv_status == 0
        if config.get('MQTT', 'mqtt_basic') == "1":
            publish_to_mqtt(config, config.get('MQTT', 'mqtt_topic'), '{"Status": "Offline"}')
        if config.get('HomeAssistant', 'homeassistant_support') == "1":
            ha_topic = config.get('HomeAssistant', 'ha_mqtt_topic')
            inverter_sn = config.get('SofarInverter', 'inverter_sn')
            publish_to_mqtt(config, f"{ha_topic}{inverter_sn}/state/connected", "false")


def publish_ha_mqtt(config, ha_data, log):
    ha_topic = config.get('HomeAssistant', 'ha_mqtt_topic')
    inverter_sn = config.get('SofarInverter', 'inverter_sn')

    client = paho.Client("inverter-ha")
    if config.get('MQTT', 'mqtt_tls') == "1":
        client.tls_set(config.get('MQTT', 'mqtt_cacert'), tls_version=int(config.get('MQTT', 'mqtt_tls_version')))
        client.tls_insecure_set(config.getboolean('MQTT', 'mqtt_tls_insecure'))
    client.username_pw_set(username=config.get('MQTT', 'mqtt_username'), password=config.get('MQTT', 'mqtt_passwd'))

    try:
        client.connect(config.get('MQTT', 'mqtt_server'), config.getint('MQTT', 'mqtt_port'))
    except Exception as e:
        write_to_log_file(log, f"Error connecting to MQTT for HA: {e}")
        return

    client.loop_start()
    client.publish(f"{ha_topic}{inverter_sn}/state/connected", "true", retain=True).wait_for_publish()

    for i, mqtt_data in enumerate(ha_data):
        title, _, unit, _, metric_name, _, label_value, value, _ = mqtt_data
        dev_cla = "energy" if unit in ['kWh', 'Wh', 'W'] else "current"
        state_class = "total_increasing" if dev_cla == "energy" else "measurement"

        config_payload = {
            "avty": {"topic": f"{ha_topic}{inverter_sn}/state/connected", "payload_available": "true",
                     "payload_not_available": "false"},
            "~": f"{ha_topic}{inverter_sn}/",
            "device": {"ids": f"{inverter_sn}", "mf": "Sofar", "name": "WLS-3", "sw": "2.1"},
            "name": f"{title} [{unit}]",
            "uniq_id": f"{inverter_sn}_{i}",
            "qos": 0,
            "unit_of_meas": unit,
            "stat_t": f"~state/{metric_name}{label_value}",
            "val_tpl": "{{ value | round(5) }}",
            "dev_cla": dev_cla,
            "state_class": state_class
        }
        config_topic = f"homeassistant/sensor/SofarLogger/{inverter_sn}_{i}/config"
        state_topic = f"{ha_topic}{inverter_sn}/state/{metric_name}{label_value}"

        client.publish(config_topic, json.dumps(config_payload), retain=True).wait_for_publish()
        client.publish(state_topic, value, retain=True).wait_for_publish()

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()