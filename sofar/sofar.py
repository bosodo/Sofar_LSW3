import binascii
import libscrc
import socket


class Sofar:
    def __init__(self, ip, port, serial_number):
        self.ip = ip
        self.port = port
        self.serial_number = serial_number
        self.client = None

    def connect(self):
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_INET, socket.SOCK_STREAM):
            family, socktype, proto, canonname, sockadress = res
            self.client = socket.socket(family, socktype, proto)
            self.client.settimeout(10)
            self.client.connect(sockadress)

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def send_request(self, pini, pfin, request_type=b'\x01\x03'):
        # Data frame begin
        start = binascii.unhexlify('A5')  # start
        length = binascii.unhexlify('1700')  # datalength
        controlcode = binascii.unhexlify('1045')  # controlCode
        serial = binascii.unhexlify('0000')  # serial
        datafield = binascii.unhexlify(
            '020000000000000000000000000000')  # com.igen.localmode.dy.instruction.send.SendDataField
        pos_ini = str(hex(pini)[2:4].zfill(4))
        pos_fin = str(hex(pfin - pini + 1)[2:4].zfill(4))
        businessfield = request_type + binascii.unhexlify(pos_ini + pos_fin)  # sin CRC16MODBUS
        crc = binascii.unhexlify(
            str(hex(libscrc.modbus(businessfield))[4:6]) + str(hex(libscrc.modbus(businessfield))[2:4]))  # CRC16modbus
        checksum = binascii.unhexlify('00')  # checksum F2
        endCode = binascii.unhexlify('15')

        inverter_sn2 = bytearray.fromhex(
            hex(self.serial_number)[8:10] + hex(self.serial_number)[6:8] + hex(self.serial_number)[4:6] + hex(self.serial_number)[2:4])
        frame = bytearray(
            start + length + controlcode + serial + inverter_sn2 + datafield + businessfield + crc + checksum + endCode)
        # Data frame end

        checksum = 0
        frame_bytes = bytearray(frame)
        for i in range(1, len(frame_bytes) - 2, 1):
            checksum += frame_bytes[i] & 255
        frame_bytes[len(frame_bytes) - 2] = int((checksum & 255))

        self.client.sendall(frame_bytes)
        return self.client.recv(1024)