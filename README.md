# SOFAR Inverter
Small utility to read data from SOFAR K-TLX inverters through the Solarman (WLS-3) datalogger. Tested with logger S/N 17xxxxxxx and 21xxxxxxx (protocol V5).

REMARK: To make it work with other inverter brand/model connected via WLS-3 you need to alter the .xml file accordingly + change pini and pfin values in the InverterData.py to point the register's position start/end.

*Thanks to @jlopez77 https://github.com/jlopez77 for 90% of the code.*

# Configuration

Edit the config.cfg and enter the following data:
```
[SofarInverter]
inverter_ip=X.X.X.X             # data logger IP
inverter_port=8899              # data logger port
inverter_sn=XXXXXXXXXX          # data logger S/N
mqtt=1                          # set to 1 for MQTT output, 0 for JSON output.
mqtt_server=192.168.X.X
mqtt_port=1883
mqtt_topic=XXXXXXXXXXXX
mqtt_username=
mqtt_passwd=
lang=PL/EN                      # Output language
prometheus=0                    # set to 1 to export data in Prometheus metrics format
prometheus_file=/xx/xx/metrics/index.html  # Path to Prometheus metrics file
verbose=0                       # Set to 1 for additional info to be presented (registers, binary packets)

File SOFARMap.xml contains MODBUS inverter's registers mapping for Sofar Solar K-TLX product line and Prometheus metrics configuration.
Eedit i.e. to get different language, other Prometheus metrics names or if Your inverter has different register's numbers.
```

# Run

```python3 InverterData.py

{"Running Status()":"Normal",
"Total Grid Produciton(kwh)":829.5,
"Total Grid Produciton(kwh)":0.0,
"Daily Energy Bought(kwh)":0.0,
"Daily Energy Sold(kwh)":15.0,
"Total Energy Bought(kwh)":21.900000000000002,
"Total Energy Bought(kwh)":0.0,
"Total Energy Sold(kwh)":1103.4,
"Total Energy Sold(kwh)":0.0,
"Daily Load Consumption(KWH)":1.2000000000000002,
"Total Load Consumption(KWH)":365.3,
"Total Load Consumption(KWH)":0.0,
"DC Temperature(℃)":149.5,
"AC Temperature(℃)":152.1,
"Total Production(KWH)":1517.4,
"Total Production(KWH)":0.0,
"Alert()":0,
"Alert()":0,
"Alert()":0,
"Alert()":0,
"Alert()":0,
"Alert()":0,
"Daily Production(KWH)":16.900000000000002,
"PV1 Voltage(V)":342.20000000000005,
"PV1 Current(A)":7.800000000000001,
"PV2 Voltage(V)":8.5,
"PV2 Current(A)":0.0,
"Grid Voltage L1(V)":241.3,
"Grid Voltage L2(V)":0.0,
"Load Voltage(V)":242.9,
"Current L1(A)":10.51,
"Current L2(A)":0.0,
"Micro-inverter Power(W)":0,
"Gen-connected Status()":0,
"Gen Power(W)":0,
"Internal CT L1 Power(W)":-2325,
"Internal CT L2  Power(W)":0,
"Grid Status()":-2365,
"Total Gird Power(W)":-2365,
"External CT L1 Power(W)":-2365,
"External CT L2 Power(W)":0,
"Inverter L1 Power(W)":2558,
"Inverter L2 Power(W)":0,
"Total Power(W)":2558,
"Load L1 Power(W)":193,
"Load L2 Power(W)":0,
"Total Load Power(W)":193,
"Battery Temperature(℃)":125.0,
"Battery Voltage(V)":10.14,
"Battery SOC(%)":0,
"PV1 Power(W)":2619,
"PV2 Power(W)":0,
"Battery Status()":0,
"Battery Power(W)":0,
"Battery Current(A)":-0.01,
"Grid-connected Status()":1,
"SmartLoad Enable Status()":16}
```

# Known Issues
Not sure if four-byte values (Total production and Total generation time) are calculated correctly (when first byte value <>0)
To be checked ...

# Contrib
Feel free to suggest, rewrite or add whatever you feel is necessary.

# Home Assistant support (by jlopez77)
MQTT support into Home Assistant:

```
  - platform: mqtt
    name: "SofarInverter"
    state_topic: "mqtt_topic"
    unit_of_measurement: "W"
    json_attributes_topic: "mqtt_topic/attributes"
```
# Prometheus support (by Michalux).
```
In order to enable Prometheus support:
    1. Configure prometheus options in config.cfg
    2. Serve prometheus metrics file using any web server (name it index.html to be the default page in configured path)
    3. Configure prometheus target to access the file 
```
