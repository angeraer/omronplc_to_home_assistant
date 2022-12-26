import socket
import paho.mqtt.client as mqtt
import time
import plc_app_settings

def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("err: mqtt client connected with result code: " + str(rc))
    pass
    client.subscribe("homeassistant/switch/+/set")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("err: mqtt client disconnect with result code: " + str(rc))
    pass

def on_message(client, userdata, message):
    # print("received message: " ,str(message.payload.decode("utf-8")))
    # print("received topic: " ,str(message.topic))
    # print("received retain: " ,str(message.retain))
    # print("received qos: " ,str(message.qos))
    splitser = str(message.payload.decode("utf-8")).split(';')
    for x in splitser:
        print(x)
        print(send_plc_command(x))


def send_plc_command(command):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.connect((plc_app_settings.moxa_ip, plc_app_settings.moxa_port))
        s.send(command.encode())  # command 'Status'
        s.send(b'\x0d\x0a')  # send 'newline' to complete command

        result = []
        while 1:
            data = s.recv(1)  # recieve one byte at a time.
            result.append(data.decode())
            if (data == b'\r'): break
            if not data: break


    s.close()
    return ''.join(result)

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

client.on_message = on_message #bind call back function

client.loop_forever()

client.loop_stop()