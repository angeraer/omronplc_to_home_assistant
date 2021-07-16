import socket
import csv
import re
import dweepy
from influxdb import InfluxDBClient

class PlcObject:
    """ DOCSTRING: the PLC Object Class
        -------------------------------
        description: B_Slaapkamer_Wand1
        address: 191.15
        area: IR
        word: 191
        bit: 15
        command: @00RR01910001
        fcs: 48*
        command_with_fcs: @00RR0191000148*
        response: @00RR0082014B*
        decoded_response: 1
    """

    def __init__(self, description, address):

        self.description = description
        self.address = address

        if (self.address.rfind('.')) > 0:  # Bit (171.09) specified?
            # self.address (HR2.09) strip all numbers and split using the '.'. Take first part => HR2.09 -> HR
            self.area = re.sub(r'[0-9]+', '', self.address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take first part => HR2.09 -> 2
            self.word = re.sub(r'[a-zA-Z]+', '', self.address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take second part => HR2.09 -> 09
            self.bit = self.address.split('.')[1]
        else:  # No bit specified, thus WORD (DM140) address specified, remove all letters => DM140 -> 140
            self.word = re.sub(r'[a-zA-Z]+', '', self.address)
            self.bit = ""
            self.area = re.sub(r'[0-9]+', '', self.address)

        if self.area == "HR":
            self.command = "@00RH"
        elif self.area == "DM":
            self.command = "@00RD"
        elif self.area == "LR":
            self.command = "@00RL"
        else:  # else it's always IR (120.01 = IR120.01
            self.area = "IR"
            self.command = "@00RR"

        # A valid command looks like: @00RH<XXXX begin word ><XXXX No. of words><FCS>*
        self.command = self.command + self.word.rjust(4, '0') + "0001"

        fcs_value = 0
        for i in range(len(self.command)):
            fcs_value = fcs_value ^ ord(self.command[i])

        self.fcs = '%X' % fcs_value
        self.command_with_fcs = self.command + self.fcs + "*"

        # self.response = self.send_command()
        # self.decoded_response = self.decode_response()
        self.response = ""
        self.decoded_response = ""

    def decode_response(self):
        """
            Check for valid response (@00<AREA>00 recieved? + correct FCS?)
            if valid response, convert WORD to BITS
            if BIT in address, store BIT value
            else store WORD value
        """

        if (self.response[:5]) == (self.command[:5]) and (self.response[5:7] == "00"):
            if self.bit == "":
                return self.response[7:-4]
            else:
                # Bit counting is reverse, counting from 0
                # Reverse string search starts at -1
                # Ex: HR5.00 -> 00 -> Integer 0, Add 1 and make negative for reverse string search: -1
                #     HR5.01 -> 01 -> Integer 1, Add 1 and make negative for reverse string search: -2
                #
                # Ex response: @00RR0084004C*
                #                     ^^^^
                #    HEX '8400' converted to binary = '1000010000000000'
                #                                           ^
                #    BIT '10' from this binary value = '1'

                tmp_bit = (int(self.bit) + 1)
                return hex2bin(self.response[7:-4])[-tmp_bit]
        else:
            print("Response BAD")
            return (self.response[7:-4])

    def send_command(self):

        self.host = '192.168.2.153'
        self.port = 4001

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.host, self.port))
            s.send(self.command_with_fcs.encode())  # command 'Status'
            s.send(b'\x0d\x0a')  # send 'newline' to complete command

            result = []
            while 1:
                data = s.recv(1)  # recieve one byte at a time.
                result.append(data.decode())
                if (data == b'\r'): break
                if not data: break

        s.close()
        return ''.join(result)


def read_plcobjects():
    """ Import CSV and convert to list of objects """
    plcobjects = []

    csvfile = r"/volume1/web/PLC_adressen.csv"
    # 'r' in front converts to raw string.

    with open(csvfile, newline='') as csvfile:
        csvlines = csv.reader(csvfile, delimiter=';')
        for row in csvlines:
            plcobject = PlcObject(row[0], row[2])  # Description, Address
            plcobjects.append(plcobject)

    return plcobjects


def hex2bin(s):
    hex_table = ['0000', '0001', '0010', '0011',
                 '0100', '0101', '0110', '0111',
                 '1000', '1001', '1010', '1011',
                 '1100', '1101', '1110', '1111']
    bits = ''
    for i in range(len(s)):
        bits += hex_table[int(s[i], base=16)]
    return bits

def write_to_influxdb(input_dict):
    influxdb_ip = "192.168.2.152"
    influxdb_port = 8086
    influxdb_user = ""
    influxdb_password = ""
    influxdb_database = "dweet_plc"

    """ Try to connect to the InfluxDB"""
    try:
        flux_client = InfluxDBClient(influxdb_ip,
                                     influxdb_port,
                                     influxdb_user,
                                     influxdb_password,
                                     influxdb_database)
    except:
        flux_client = None
        print("[INFO] Failed to connect to InfluxDB")

    """ Write data to influxDB"""
    try:
        if flux_client is not None:
            metrics = {}
            tags = {}
            fields = {}
            metrics['measurement'] = "dweet_plc"
            tags['source'] = "192.168.2.152"
            metrics['tags'] = tags
            metrics['fields'] = input_dict
            flux_client.write_points([metrics])
            flux_client.close()
    except Exception as err:
        print("[ERROR] %s" % err)

# Program

plcobjects = read_plcobjects()

plc_previous_command_with_fcs = ""
plc_previous_response = ""

result_dict = {}

for plcobject in plcobjects:

    # Connect to PLC and read data
    if (plc_previous_command_with_fcs == plcobject.command_with_fcs):
        # If same WORD and thus same RESPONSE as previous record, skip reading from PLC and use previous data.
        plcobject.response = plc_previous_response
        plcobject.decoded_response = plcobject.decode_response()
    else:
        plcobject.response = plcobject.send_command()
        plcobject.decoded_response = plcobject.decode_response()
        plc_previous_command_with_fcs = plcobject.command_with_fcs
        plc_previous_response = plcobject.response

    # Only put interesting stuff in the dweet dict
    # if (plcobject.area == "IR" and plcobject.decoded_response == "1") or plcobject.area == "DM":
    result_dict[plcobject.description] = int(plcobject.decoded_response) #Convert to integers for InfluxDB/Grafana

#write_to_influxdb(result_dict)
dweepy.dweet_for('angeraer-plc', result_dict)

# get_dweet()
#     url = dweepy.get_latest_dweet_for(thing)
#     dict = url[0]
#     content = dict['content']
#     longdate = dict['created']
#     date = longdate[:10]
#     time = longdate[11:19]
#     print("Date:", date)
#     print("Time:", time)
#     print(content)
#     # print(content.values())
