import argparse
import can
import time
import paho.mqtt.client as mqtt
import struct
import binascii
import logging
from ebyteecan import ebyteecan

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='',
                    description='',
                    epilog='')
    parser.add_argument('-c', '--caninterface',  default='vcan0', help='The CANBus interface to use locally Default: vcan0')
    parser.add_argument('-m', '--mqttbroker', default='venus.local', help='MQTT broker hostname')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbose output')
    #parser.add_argument('action', choices=['scan','reboot','readconf','writeconf','bridge', 'capture', 'test'])
    args = parser.parse_args()
    if(args.verbose==0):
        logging.basicConfig(level=logging.ERROR)
    elif(args.verbose==1):
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG, style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}')

    logging.debug(args)

    cansocket=can.interface.Bus(args.caninterface, bustype='socketcan')
    logging.info(f'Reading from can interface {args.caninterface}')

    mqtt_client = mqtt.Client('quickbus-ecan')
    mqtt_port = 1883
    mqtt_client.connect(args.mqttbroker, mqtt_port)
    logging.info(f'Connected to MQTT broker {args.mqttbroker}')

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
        mqtt_topic = 'quickbus/chaincounter'
        mqtt_client.publish(mqtt_topic, payload=str(payloadObj), retain=False)
        mqtt_client.publish('quickbus/chainoutFeet', payload=chainOutInFeet, retain=False)
        mqtt_client.publish('quickbus/chainoutMeters', payload=chainOutInFeet*0.3048, retain=False)

    while True:
        try:
            can_msg = cansocket.recv(1)
            on_can_message(can_msg)
        except can.CanError:
            pass
