#!/usr/bin/python3
# Script gathering product data from Sofar Solar Inverter (K-TLX) via logger module LSW-3/LSE
# by Michalux
# Version: 2.1

import json
import sys

from sofar.sofar import Sofar
from sofar.helpers import get_config, get_parameters


def main():
    config = get_config()
    inverter = Sofar(
        config.get('SofarInverter', 'inverter_ip'),
        config.getint('SofarInverter', 'inverter_port'),
        config.getint('SofarInverter', 'inverter_sn')
    )

    lang = config.get('SofarInverter', 'lang', fallback='EN')
    verbose = config.get('SofarInverter', 'verbose', fallback='0')
    pini = int(config.get('SofarInverter', 'registerhw_start', fallback='0'), 0)
    pfin = int(config.get('SofarInverter', 'registerhw_end', fallback='0'), 0)

    try:
        inverter.connect()
    except Exception as e:
        print(f"Could not connect to inverter: {e}")
        sys.exit(1)

    try:
        response = inverter.send_request(pini, pfin, request_type=b'\x01\x04')
    except Exception as e:
        print(f"Could not read data from inverter: {e}")
        sys.exit(1)

    if verbose == "1":
        print(f"Received data: {response}")

    parameters = get_parameters('./SOFARHWMap.xml')
    output_data = {}
    temp_values = {
        'SN': {'value': '', 'title': ''},
        'SV': {'value': '', 'title': ''},
        'HV': {'value': '', 'title': ''},
        'DSPV': {'value': '', 'title': ''},
    }

    a = 0
    while a <= pfin - pini:
        p1 = 56 + (a * 4)
        p2 = 60 + (a * 4)
        responsereg = ''.join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(response))[p1:p2]
        val1 = chr(int(str(responsereg[0:2]), 16))
        val2 = chr(int(str(responsereg[2:4]), 16))
        hexpos = str("0x") + str(hex(a + pini)[2:].zfill(4)).upper()

        if verbose == "1":
            print(f"Register: {hexpos}, value: {responsereg} ({val1}{val2})")

        for parameter in parameters:
            for item in parameter["items"]:
                if hexpos in item["registers"]:
                    value_type = item.get("value_type", "")
                    if value_type in temp_values:
                        temp_values[value_type]['value'] += val1 + val2
                        if not temp_values[value_type]['title']:
                            temp_values[value_type]['title'] = item[f'title{lang.upper()}']
                    else:
                        for option in item["optionRanges"]:
                            if option["key"] == int(responsereg, 16):
                                title = item[f"title{lang.upper()}"]
                                value = option[f"value{lang.upper()}"]
                                output_data[title] = value
        a += 1

    for value_type in temp_values:
        data = temp_values[value_type]
        if data['value'] and data['title']:
            output_data[data['title']] = data['value']

    print(json.dumps(output_data, indent=4, sort_keys=False, ensure_ascii=False))

    if inverter.client:
        inverter.disconnect()


if __name__ == "__main__":
    main()