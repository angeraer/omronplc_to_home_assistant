This program fetches data from Omron PLC and feeds it into Home Assistant via Auto Discovery
---

I have an old Omron PLC that is used for home automation. This PLC is +20 years old but still works like a charm!
The only drawback, it doesn't have an IP interface! As a solution I use a Moxa Nport 5501 Serial-to-IP converter.
This Moxa device enables me to talk to the PLC over TCP.

Setup:
------

                                                Moxa Nport 5501      -------->   Omron PLC C200H
                                                     |
                                                     |
                                                     |
                            Synology NAS running the Python code in a cronjob <----- CSV file as input.
                                                     |
                                                     |
                                                     |
                                    MQTT Broker (running on Home Assistant)
                                                     |
                                                     |
                                                     |                                                                                                 
                                        Home assistant (Raspberry Pi 4)                                      


The script will send the 'read' commands towards the PLC to read out the bit state data. I uses a CSV file as input. 
This data (=symbols) can be exported if you use CX Programmer for example to edit your PLC program.
It simply contains the list of all BOOL bits that represent the state of an output.

CSV:

Name;Data Type;Address;Comment;Extra
------------------------------------
Light1;BOOL;191.01;This is light1;
Light2;BOOL;191.02;This is light2;

191.01 -> represents the address in memory of the PLC. If this bit is 1, the light is ON. If this bit is 0 the light is OFF.

The code will connect to the PLC. Read & validate the data and send the results to the MQTT broker.

[Screenshot MQTT config message](docu/mqtt_1.png)
[Screenshot MQTT state message](docu/mqtt_2.png)
