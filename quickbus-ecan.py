import argparse
import time
import paho.mqtt.client as mqtt
import struct
import binascii
import logging
import socket
from ebyteecan import ebyteecan

def on_can_message(mqtt_client, can_msg):
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='',
                    description='',
                    epilog='')
    parser.add_argument('-c', '--caninterface',  help='The CANBus interface to use locally Default: vcan0')
    parser.add_argument('-n', '--netinterface',  default=None, help='Name of the network interface')
    parser.add_argument('-g', '--gatewayname',  default='A0001', help='Name of the ecanebyte gateway. default: A0001')
    parser.add_argument('-p', '--gatewayport',  help='Port on the ecanebyte gateway')
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
    mqtt_client = mqtt.Client('quickbus-ecan')
    mqtt_port = 1883
    mqtt_client.connect(args.mqttbroker, mqtt_port)
    logging.info(f'Connected to MQTT broker {args.mqttbroker}')

    if(args.caninterface):
        import can
        cansocket=can.interface.Bus(args.caninterface, bustype='socketcan')
        logging.info(f'Reading from can interface {args.caninterface}')
        while True:
            try:
                can_msg = cansocket.recv(1)
                on_can_message(mqtt_client, can_msg)
            except can.CanError:
                pass
    elif(args.gatewayport):
        (gatewayIp, macAddress)=ebyteecan.discoverGatewayByName(args.gatewayname, args.netinterface)
        if gatewayIp is None:
            error('Unable to resolve IP of gateway named %s', deviceName)
            exit(1)
        logging.info(f'Gateway ip is {gatewayIp}, mac {binascii.hexlify(macAddress,":")}')
        sockettogateway=ebyteecan.createTCPSocketToGateway(gatewayIp, int(args.gatewayport))
        sockettogateway.setblocking(True)
        DATA_FRAME_LEN=13
        while True:
            gatewayFormatFrame=sockettogateway.recv(DATA_FRAME_LEN)
            logging.debug("Got a data frame from the gateway: %s", str(binascii.hexlify(gatewayFormatFrame)))
            if(len(gatewayFormatFrame)==DATA_FRAME_LEN):
                canMsg=ebyteecan.convertGatewayFormatToCANBusFrame(gatewayFormatFrame)
                on_can_message(mqtt_client, canMsg)
            else:
                raise Exception("Incompleted gateway message received")

    else:
        logging.error('You must specify either -c or -p')
        exit(1)

