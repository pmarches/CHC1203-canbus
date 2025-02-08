import argparse
import time
import paho.mqtt.client as mqtt
import struct
import binascii
import logging
import socket
import time
import json

from enum import Enum

class AnchorState(Enum):
    RAISED=1
    LOWERED=2

class LatLon:
    lat=0
    lon=0
    def hasFix(self):
        return self.lat!=0 and self.lon!=0

class AnchoringState:
    state=AnchorState.RAISED
    anchorLatLon=LatLon()
    anchorDepthFt=0
    lastDepthFt=0
    lastGPSFixFromGX=LatLon()
    chainOutInFeet=0

    def distanceToAnchorFt(self, boatLatLon):
        return 123

    def getScope(self):
        if(self.anchorDepthFt==0):
            return 0
        return self.chainOutInFeet/self.anchorDepthFt

lastPublishTS=0
anchoringState=AnchoringState()

def on_can_message(mqtt_client, can_msg):
    if can_msg is None:
        return
    
    if can_msg.arbitration_id == 0x6C0:
        #print(len(can_msg.data))
        #print(binascii.hexlify(can_msg.data))
        (_, a, b, c)=struct.unpack('<HHHH', can_msg.data)
        #print(a,b,c)
        return

    if can_msg.arbitration_id != 0x6C1:
        return

    global lastPublishTS
    if(time.time() - lastPublishTS < 10):
        return
    lastPublishTS=time.time()

    (_, chainOutInFeet, unitOfMeasure)=struct.unpack('<HIH', can_msg.data)
    if unitOfMeasure==1:
        unitOfMeasure="meter"
    elif unitOfMeasure==2:
        unitOfMeasure="feet"
    #payloadObj={
        #"unitOfMeasure":unitOfMeasure,
        #"chainOutInFeet":chainOutInFeet,
        #"ts":can_msg.timestamp,
    #}
    #mqtt_client.publish('quickbus/chaincounter', payload=str(payloadObj), retain=False)
    mqtt_client.publish('quickbus/chainoutFeet', payload=chainOutInFeet, retain=True)
    #mqtt_client.publish('quickbus/chainoutMeters', payload=chainOutInFeet*0.3048, retain=False)

    global anchoringState
    print(f'anchoringState.lastGPSFixFromGX.lat={anchoringState.lastGPSFixFromGX.lat} anchoringState.lastGPSFixFromGX.lon={anchoringState.lastGPSFixFromGX.lon}')
    print(f'anchoringState.lastDepthFt={anchoringState.lastDepthFt}')
    if(not anchoringState.lastGPSFixFromGX.hasFix() or anchoringState.lastDepthFt==0):
        return

    if(chainOutInFeet > anchoringState.chainOutInFeet):
        anchoringState.chainOutInFeet=chainOutInFeet
        if(anchoringState.state==AnchorState.RAISED): #Transition to anchor down
            anchoringState.state=AnchorState.LOWERED
            anchoringState.anchorDepthFt=anchoringState.lastDepthFt
            anchoringState.anchorLatLon=anchoringState.lastGPSFixFromGX
            mqtt_client.publish('quickbus/anchorLat', payload=anchoringState.lastGPSFixFromGX.lat, retain=True)
            mqtt_client.publish('quickbus/anchorLon', payload=anchoringState.lastGPSFixFromGX.lon, retain=True)
    elif(chainOutInFeet < anchoringState.chainOutInFeet): #Shortening chain
        anchoringState.chainOutInFeet=chainOutInFeet
        if(anchoringState.state==AnchorState.LOWERED): #Transition
            if(chainOutInFeet<anchoringState.anchorDepthFt):
                anchoringState.state=AnchorState.RAISED
                anchoringState.lastDepthFt=0
                anchoringState.anchorDepthFt=0

    mqtt_client.publish('quickbus/scope', payload=anchoringState.getScope(), retain=True)

def convertGXJsonToNumber(jsonPayloadBytes):
    jsobObj=json.loads(jsonPayloadBytes.decode("utf-8"))
    return jsobObj['value']

def on_mqtt_message_received(client, userdata, message):
    logging.debug(f'userdata={userdata}')
    logging.debug(f'message={message}')
    print(message.topic+" "+str(message.payload))
    global anchoringState
    if(message.topic.endswith('/Latitude')):
        anchoringState.lastGPSFixFromGX.lat=convertGXJsonToNumber(message.payload)
    elif(message.topic.endswith('/Longitude')):
        anchoringState.lastGPSFixFromGX.lon=convertGXJsonToNumber(message.payload)
    elif(message.topic.endswith('/depthInCM')):
        anchoringState.lastDepthFt=float(message.payload.decode("utf-8"))/30.48 #Convert cm to Ft
    else:
        logging.warn("Unexpected MQT topic")

def on_connect(client, userdata, flags, reason_code):
    if reason_code:
        print(f"Failed to connect: {reason_code}.")
        return
    client.subscribe('N/+/gps/0/Position/+')
    client.subscribe('n2k/depth/0/depthInCM')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='',
                    description='',
                    epilog='')
    parser.add_argument('-c', '--caninterface',  help='The CANBus interface to use locally Default: vcan0')
    parser.add_argument('-n', '--netinterface',  default=None, help='Name of the network interface to search the gateway on')
    parser.add_argument('-g', '--gatewayname',  default='A0001', help='Name of the ecanebyte gateway. default: A0001')
    parser.add_argument('-i', '--gatewayip',  help='IP address of the ecanebyte gateway')
    parser.add_argument('-p', '--gatewayport',  help='Port on the ecanebyte gateway')
    parser.add_argument('-m', '--mqttbroker', default='localhost', help='MQTT broker hostname')
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
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message=on_mqtt_message_received
    mqtt_client.will_set('quickbus/status', payload='offline', qos=True, retain=True);
    mqtt_client.connect(args.mqttbroker, 1883)
    
    logging.info(f'Connected to MQTT broker {args.mqttbroker}')
    mqtt_client.publish('quickbus/status', payload='online', qos=True, retain=True);
    mqtt_client.loop_start()

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
        from ebyteecan import ebyteecan
        gatewayIpAndPort=None
        if(args.gatewayip):
            gatewayIpAndPort=ebyteecan.GatewayIpAndPort(args.gatewayip, int(args.gatewayport))
        else:
            (gatewayIp, macAddress)=ebyteecan.discoverGatewayByName(args.gatewayname, args.netinterface)
            if gatewayIp is None:
                logging.error('Unable to resolve IP of gateway named %s', deviceName)
                exit(1)
            logging.info(f'Gateway ip is {gatewayIp}, mac {binascii.hexlify(macAddress,":")}')
            gatewayIpAndPort=ebyteecan.GatewayIpAndPort(args.gatewayip, args.gatewayport)

        sockettogateway=ebyteecan.GatewayTCPSocket()
        sockettogateway.connect(gatewayIpAndPort)
        while True:
            canMsg=sockettogateway.recv()
            on_can_message(mqtt_client, canMsg)

    else:
        logging.error('You must specify either -c or -p')
        exit(1)
