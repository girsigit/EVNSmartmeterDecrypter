#!/usr/bin/env python
# coding: utf-8

# # Version 1.0 - 2022-10-12
# - ) Adapted from Node Red version

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from datetime import datetime
import os
import math
import copy
import logging

from DecodeData import rawByteStringToFeatureDict, decryptADPU, extractValues
from SaveToDB import SaveToDB

APP_MQTT_NAME = "ProcessSmartmeterPythonServer"
DEBOUNCED_STORAGE_INTERVAL_MINUTES = 5

# Set the logging level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load the environment variables
load_dotenv("server.env")

# Create a previous featureDict as helper for storing debounced values
previousData = None

# MQTT connect


# The callback for when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    logging.info("MQTT connected with result code {0}".format(str(rc)))

    client.subscribe(os.getenv('SMARTMETER_RAWDATA_MQTT_TOPIC'))

# Message callback


def on_message(client, userdata, msg):
    # print("Message received-> " + msg.topic + " " + str(msg.payload))  # Print a received msg

    # Create a dict with all the (raw) mbus features
    featureDict = rawByteStringToFeatureDict(msg.payload)

    # Add the EVN Smartmeter key to dict
    featureDict["key"] = os.getenv('SMARTMETER_KEY')

    # Decrypt the adpu frame
    pt = decryptADPU(featureDict['key'], featureDict['systemTitle'],
                     featureDict['frameCount'], featureDict['adpu'])

    # Extract the data values
    data = extractValues(pt['APDU'])

    # Add a timestamp
    data['timestamp'] = {
        "value": round(datetime.utcnow().timestamp()),
        "unit": "s"
    }

    # Save the data to the DB
    SaveToDB(data, os.getenv('SMARTMETER_DB_SCHEMA'),
             os.getenv('SMARTMETER_DB_TABLE'))

    # Check if a debounced save is required
    global previousData
    if (previousData is not None):
        prevDebouncedTimestamp = math.floor(
            previousData['timestamp']['value'] / (DEBOUNCED_STORAGE_INTERVAL_MINUTES * 60.0))
        debouncedTimestamp = math.floor(
            data['timestamp']['value'] / (DEBOUNCED_STORAGE_INTERVAL_MINUTES * 60.0))

        if(prevDebouncedTimestamp != debouncedTimestamp):
            SaveToDB(data, os.getenv('SMARTMETER_DB_SCHEMA'),
                     os.getenv('SMARTMETER_DB_TABLE')+"Debounced")

    previousData = copy.deepcopy(data)

    # Convert data to string and change the quotation marks to allow parsing in node-red
    dataStr = str(data)
    dataStr = dataStr.replace("'", "\"")

    # Publish the decoded values on MQTT
    mqttClient.publish(payload=dataStr, topic=os.getenv(
        'SMARTMETER_VALUES_MQTT_TOPIC'))


# Create a MQTT client
mqttClient = mqtt.Client(APP_MQTT_NAME)
mqttClient.username_pw_set(os.getenv('MQTT_USER'), os.getenv('MQTT_PASSWORD'))

# Callbacks
# Define callback function for successful connection
mqttClient.on_connect = on_connect
# Define callback function for receipt of a message
mqttClient.on_message = on_message

# Connect
mqttClient.connect(os.getenv('MQTT_HOST'), int(os.getenv('MQTT_PORT')))
mqttClient.loop_forever()  # Start networking daemon

logging.info("I did exit")
