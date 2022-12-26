import socket
import csv
import re
import paho.mqtt.client as mqtt
import time
import json
import plc_app_settings

class PlcObject:
    """ DOCSTRING: the PLC Object Class
        -------------------------------
        output_description: c_zolder_klein3
        output_address: 190.03
        output_area: IR
        output_word: 190
        output_bit: 03
        get_command: @00RR01900001
        get_command_with_fcs: @00RR0190000149*
        response: @00RR00000040*
        decoded_response: 0
        set_command_on: @00KSHR 1900359*
        set_command_off: @00KRHR 1900358*
        input_description: c_zolder_klein3_togglebit2
        input_address: HR6.14
        input_area: HR
        input_word: 6
        input_bit: 14
        location: zolder - klein
    """

    def __init__(self, output_description, output_address, input_description, input_address, location):

        self.output_description = output_description
        self.output_address = output_address

        if (self.output_address.rfind('.')) > 0:  # Bit (171.09) specified?
            # self.address (HR2.09) strip all numbers and split using the '.'. Take first part => HR2.09 -> HR
            self.output_area = re.sub(r'[0-9]+', '', self.output_address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take first part => HR2.09 -> 2
            self.output_area_word = re.sub(r'[a-zA-Z]+', '', self.output_address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take second part => HR2.09 -> 09
            self.output_area_bit = self.output_address.split('.')[1]
        else:  # No bit specified, thus WORD (DM140) address specified, remove all letters => DM140 -> 140
            self.output_area_word = re.sub(r'[a-zA-Z]+', '', self.output_address)
            self.output_area_bit = ""
            self.output_area = re.sub(r'[0-9]+', '', self.output_address)

        if self.output_area == "HR":
            self.get_command = "@00RH"
        elif self.output_area == "DM":
            self.get_command = "@00RD"
        elif self.output_area == "LR":
            self.get_command = "@00RL"
        else:  # else it's always IR (120.01 = IR120.01
            self.output_area = "IR"
            self.get_command = "@00RR"

        # A valid command looks like: @00RH<XXXX begin word ><XXXX No. of words><FCS>*
        self.get_command = self.get_command + self.output_area_word.rjust(4, '0') + "0001"
        self.get_command_with_fcs = calc_fcs(self.get_command) + "*"

        self.response = ""
        self.decoded_response = ""
        self.input_description = input_description
        self.input_address = input_address

        if (self.input_address.rfind('.')) > 0:  # Bit (171.09) specified?
            # self.address (HR2.09) strip all numbers and split using the '.'. Take first part => HR2.09 -> HR
            self.input_area = re.sub(r'[0-9]+', '', self.input_address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take first part => HR2.09 -> 2
            self.input_area_word = re.sub(r'[a-zA-Z]+', '', self.input_address.split('.')[0])
            # self.address (HR2.09) strip all letters and split using the '.'. Take second part => HR2.09 -> 09
            self.input_area_bit = self.input_address.split('.')[1]
        else:  # No bit specified, thus WORD (DM140) address specified, remove all letters => DM140 -> 140
            self.input_area_word = re.sub(r'[a-zA-Z]+', '', self.input_address)
            self.input_area_bit = ""
            self.input_area = re.sub(r'[0-9]+', '', self.input_address)

        if self.input_area == "HR":
            self.set_command_on = calc_fcs("@00SC02") + "*;" + calc_fcs("@00KSHR  " + self.input_area_word.rjust(4, '0') + self.input_area_bit) + "*;" + calc_fcs("@00SC03") + "*"
            self.set_command_off = calc_fcs("@00SC02") + "*;" + calc_fcs("@00KRHR  " + self.input_area_word.rjust(4, '0') + self.input_area_bit) + "*;" + calc_fcs("@00SC03") + "*"
        else:
            self.set_command_on = ""
            self.set_command_off = ""

        self.location = location

    def decode_response(self):
        """
            Check for valid response (@00<AREA>00 recieved? + correct FCS?)
            if valid response, convert WORD to BITS
            if BIT in address, store BIT value
            else store WORD value
        """

        if (self.response[:5]) == (self.get_command[:5]) and (self.response[5:7] == "00"):
            if self.output_area_bit == "":
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

                tmp_bit = (int(self.output_area_bit) + 1)
                return hex2bin(self.response[7:-4])[-tmp_bit]
        else:
            print("ERR: Response BAD")
            return (self.response[7:-4])

    def send_command(self):

        global moxa_ip
        global moxa_port

        self.host = plc_app_settings.moxa_ip #IP address of the Moxa IP-2-Serial converter
        self.port = plc_app_settings.moxa_port #TCP port used on the Moxa IP-2-Serial converter

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.host, self.port))
            s.send(self.get_command_with_fcs.encode())  # command 'Status'
            s.send(b'\x0d\x0a')  # send 'newline' to complete command

            result = []
            while 1:
                data = s.recv(1)  # recieve one byte at a time.
                result.append(data.decode())
                if (data == b'\r'): break
                if not data: break


        s.close()
        return ''.join(result)


def calc_fcs(s):
    fcs_value = 0
    fcs = ''
    for i in range(len(s)):
        fcs_value = fcs_value ^ ord(s[i])

    fcs = '%X' % fcs_value
    return s + fcs

def read_plcobjects():
    """ Import CSV and convert to list of objects """
    """ 0        1                     2              3          4               """
    """ --------|---------------------|--------------|----------|----------------"""
    """ Location; Input               ; Input Address; Output   ; Output Address """
    """ Portaal ; A_Portaal_Togglebit2; HR5.06       ; A_Portaal; 171.12         """

    plcobjects = []
    global csvfile

    with open(plc_app_settings.csvfile, newline='') as csvfile:
        csvlines = csv.reader(csvfile, delimiter=';')
        for row in csvlines:
            
            plcobject = PlcObject(row[3].lower(), row[4], row[1].lower(), row[2], row[0].lower())  # output.(lowercased), output address, input.(lowercased), input address, location
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

def on_publish(client, userdata, mid):
    #print("mqtt data published with message id:" + str(mid))
    pass

def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("err: mqtt client connected with result code: " + str(rc))
    pass

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("err: mqtt client disconnect with result code: " + str(rc))
    pass


######################################################################
# Program
######################################################################

# Initialize the MQTT client that should connect to the Mosquitto broker on Home Assistant
client = mqtt.Client()
client.on_connect = on_connect #bind call back function

connOK = False
while (connOK == False):
    try:
        client.username_pw_set(username= plc_app_settings.mqtt_user, password = plc_app_settings.mqtt_password)
        client.connect(plc_app_settings.mqtt_ip, plc_app_settings.mqtt_port, 60)
        connOK = True
    except:
        print("err: wait loop for mqtt connection...")
        connOK = False
    time.sleep(2)

client.on_publish = on_publish #bind call back function

plcobjects = read_plcobjects() #Import .csv file and return a list of objects from class PlcObject

plc_previous_get_command_with_fcs = ""
plc_previous_response = ""

for plcobject in plcobjects:

    # Connect to PLC and read data
    if (plc_previous_get_command_with_fcs == plcobject.get_command_with_fcs):
        # If same WORD and thus same RESPONSE as previous record, skip reading from PLC and use previous data.
        plcobject.response = plc_previous_response
        plcobject.decoded_response = plcobject.decode_response()
    else:
        plcobject.response = plcobject.send_command()
        plcobject.decoded_response = plcobject.decode_response()
        plc_previous_get_command_with_fcs = plcobject.get_command_with_fcs
        plc_previous_response = plcobject.response


    #publish on mqtt broker in format for Home Assistant auto discovery
    payload = {
    "name": f"{plcobject.output_description}",
    "payload_on":f"{plcobject.set_command_on}",
    "payload_off":f"{plcobject.set_command_off}",
    "state_topic": "homeassistant/switch/" + f"{plcobject.output_description}" + "/state",
    "command_topic": "homeassistant/switch/" + f"{plcobject.output_description}" + "/set",
    "state_on":"ON",
    "state_off":"OFF",
    "icon":"mdi:lightbulb",
    "value_template": "{{ value_json.state }}",
    "unique_id": f"{plcobject.output_description}",
    "device": {
        "name": f"{plcobject.output_description}",
        "identifiers": f"{plcobject.input_address}" + ":" + f"{plcobject.decoded_response}"
        },
    }
    ret = client.publish("homeassistant/switch/" + plcobject.output_description + "/config", json.dumps(payload), retain=True)

    if (plcobject.decoded_response == '1'):
        ret = client.publish("homeassistant/switch/" + plcobject.output_description + "/state", "{" + '"state"' + ":" + '"ON"}', retain=True)
    elif (plcobject.decoded_response == '0'):
        ret = client.publish("homeassistant/switch/" + plcobject.output_description + "/state", "{" + '"state"' + ":" + '"OFF"}', retain=True)


    # print("location: " + plcobject.location)
    # print("output_description: " + plcobject.output_description)
    # print("output_address: " + plcobject.output_address)
    # print("output_area: " + plcobject.output_area)
    # print("output_word: " + plcobject.output_area_word)
    # print("output_bit: " + plcobject.output_area_bit)
    # print("get_command: " + plcobject.get_command_with_fcs)
    # print("response: " + plcobject.response)
    # print("decoded_response: " + plcobject.decoded_response)
    # print("input_description: " + plcobject.input_description)
    # print("input_address: " + plcobject.input_address)
    # print("input_area: " + plcobject.input_area)
    # print("input_word: " + plcobject.input_area_word)
    # print("input_bit: " + plcobject.input_area_bit)
    # print("set_command_on: " + plcobject.set_command_on)
    # print("set_command_off: " + plcobject.set_command_off)
    # print("---")


client.on_disconnect = on_disconnect #bind call back function
client.disconnect()
