#!/usr/bin/env python3

import sys
import log
import paho.mqtt.client as mqtt

# Default broker IP set to black/server RPi
BROKER_IP            = "172.16.32.182"
BROKER_PORT          = int( 1883 )
CONNECTION_KEEPALIVE = int(   60 ) # unit is seconds
QUALITY_OF_SERVICE   = int(    0 )

# Every publisher/subscriber requires a mqtt client instance.
def setup_mqtt_client( local_ip ):

  mqtt_client = mqtt.Client()
  mqtt_client.on_connect = on_mqtt_connect
  mqtt_client.on_publish = on_mqtt_publish
  mqtt_client.on_disconnect = on_mqtt_disconnect

  try:
    mqtt_client.connect( BROKER_IP,
                         BROKER_PORT,
                         CONNECTION_KEEPALIVE,
                         local_ip )
  except Exception:
    print( "could not establish connection to broker with ip : " + BROKER_IP )
    sys.exit( 1 )
    
  mqtt_client.loop_start()

  return mqtt_client


# functions where the instance of the mqtt client points on
def on_mqtt_publish( client, userdata, mid ):
  print( "MQTT client successfully published a message to broker " + BROKER_IP )


def on_mqtt_connect( client, userdata, flags, rc ):
  print( "connected to broker with result code: " + str( rc ) )


def on_mqtt_disconnect( client, userdata, rc ):
  if rc != 0:
    print( "Unexpected disconnection." )
  else:
    print( "MQTT client disconnected without errors." )
