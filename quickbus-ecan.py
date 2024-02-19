import can
import time
import paho.mqtt.client as mqtt
import struct
import binascii

# Canbus settings
can_interface = 'vcan0'
can_bus = can.interface.Bus(can_interface, bustype='socketcan')
print(f'Reading from can interface {can_interface}')

# MQTT settings
mqtt_broker = 'venus.local'
mqtt_port = 1883
mqtt_topic = 'quickbus/chaincounter'
mqtt_client = mqtt.Client()
mqtt_client.connect(mqtt_broker, mqtt_port)    
print(f'Connected to MQTT broker {mqtt_broker}')

def on_can_message(can_msg):
    if can_msg is None:
        return
    
    if can_msg.arbitration_id != 0x6C1:
        return
    #print(len(can_msg.data))
    #print(binascii.hexlify(can_msg.data))
    (_, chainOutInFeet, unitOfMeasure)=struct.unpack('<HIH', can_msg.data)
    if unitOfMeasure==1:
        unitOfMeasure="meter"
    elif unitOfMeasure==2:
        unitOfMeasure="feet"
    
    payloadObj={
        "unitOfMeasure":unitOfMeasure,
        "chainOutInFeet":chainOutInFeet,
        "ts":can_msg.timestamp,
    }
    mqtt_client.publish(mqtt_topic, payload=str(payloadObj), retain=False)
    mqtt_client.publish('quickbus/chainoutFeet', payload=chainOutInFeet, retain=False)
    mqtt_client.publish('quickbus/chainoutMeters', payload=chainOutInFeet*0.3048, retain=False)

# Start listening for CAN messages
while True:
    try:
        can_msg = can_bus.recv(1)
        on_can_message(can_msg)
    except can.CanError:
        pass
