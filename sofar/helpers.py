import argparse
import configparser
import os
import sys
import json
from datetime import datetime

import influxdb_client
import paho.mqtt.client as paho
from influxdb_client.client.write_api import SYNCHRONOUS


def twos_complement_hex(hexval, reg):
    if hexval == "" or (" " in hexval):
        print("No value in response for register " + reg)
        print("Check register start/end values in config.cfg")
        sys.exit(1)
    bits = 16
    val = int(hexval, bits)
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val


def get_config():
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    config = configparser.ConfigParser()
    config.read('./config.ini')

    if os.path.exists('config-custom.ini'):
        config.read('config-custom.ini')

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", type=str, help='Config file')
    args = parser.parse_args()
    if args.config_file:
        config.read(args.config_file)

    return config


def get_parameters(map_file):
    with open(map_file, encoding="utf-8") as txtfile:
        return json.loads(txtfile.read())


def p_metrics(mname, mtype, mlabel, mlvalue, pdata):
    line = "# TYPE " + mname + " " + mtype + "\n" + mname + "{" + mlabel + "=\"" + mlvalue + "\"} " + str(pdata) + "\n"
    return line


def prepare_influx_data(if_data, fieldname, fieldvalue):
    if_data[0]["fields"][fieldname] = float(fieldvalue)
    return if_data


def write_to_influxdb(config, if_data):
    if_client = influxdb_client.InfluxDBClient(
        url=config.get('InfluxDB', 'influxdb_url'),
        token=config.get('InfluxDB', 'influxdb_token'),
        org=config.get('InfluxDB', 'influxdb_org')
    )
    influxdb_api = if_client.write_api(write_options=SYNCHRONOUS)
    influxdb_api.write(
        config.get('InfluxDB', 'influxdb_bucket'),
        config.get('InfluxDB', 'influxdb_org'),
        if_data
    )


def prepare_domoticz_data(d_data, idx, svalue):
    if isinstance(svalue, str):
        d_data.append('{ "idx": ' + str(idx) + ', "svalue": ' + svalue + ' }')
    else:
        d_data.append('{ "idx": ' + str(idx) + ', "svalue": "' + str(svalue) + '" }')
    return d_data


def write_to_log_file(log, text):
    log.write(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + ": " + text + "\n")


def write_debug(log, text, debug):
    if debug == "1":
        log.write(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + ": " + text + "\n")


def publish_to_mqtt(config, topic, payload, retain=False):
    client = paho.Client("inverter")
    if config.get('MQTT', 'mqtt_tls') == "1":
        client.tls_set(
            config.get('MQTT', 'mqtt_cacert'),
            tls_version=int(config.get('MQTT', 'mqtt_tls_version'))
        )
        client.tls_insecure_set(config.get('MQTT', 'mqtt_tls_insecure'))
    client.username_pw_set(
        username=config.get('MQTT', 'mqtt_username'),
        password=config.get('MQTT', 'mqtt_passwd')
    )
    client.connect(config.get('MQTT', 'mqtt_server'), int(config.get('MQTT', 'mqtt_port')))
    client.loop_start()
    result = client.publish(topic, payload, retain=retain)
    result.wait_for_publish()
    client.loop_stop()
    client.disconnect()
    return result.is_published()