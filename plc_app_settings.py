##########################################################################################################################
moxa_ip = '192.168.10.153' #IP address of the Moxa IP-2-Serial converter
moxa_port = 4001 #TCP port used on the Moxa IP-2-Serial converter
mqtt_ip = '192.168.10.90' #IP address of the MQTT broker
mqtt_port = 1883 #Port used on the IP of the MQTT broker
mqtt_user = 'mqtt' #mqtt userid
mqtt_password = 'mqtt' #mqtt password
csvfile = r"C:\MyCode\plc_addresses_new.csv" #r in front converts to raw string. Input file.
#
# Example entries in input file:
# ------------------------------
#Portaal;A_Portaal_Togglebit2;HR5.06;A_Portaal;171.12
#Terras;A_Buiten_Achtergevel_Togglebit2;HR5.14;A_Terras_Gevel_Oprit;191.02
#Terras;A_Buiten_Achtergevel_Togglebit2;HR5.14;A_Terras_Gevel_Voordeur;191.03
#Terras;A_Buiten_Togglebit2;HR4.12;A_Terras_Scheidingsmuur_Links;191.11
# ...
##########################################################################################################################


