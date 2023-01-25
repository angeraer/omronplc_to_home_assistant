#!/bin/bash

# Define the process to check
process="plc_app_mqtt_listener.py"

if ! ps -ef | grep -v grep | grep "$process" > /dev/null
then
    # If the process is not running, start it
            nohup python3 /volume1/Data/Scripts/$process &
fi
