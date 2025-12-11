#!/usr/bin/env python3

import log
import mqttconfig

from Actuator import Actuator

from grove_pi_interface import InteractorMember, \
                               DIGITAL_WRITE

# logging setup
logger = log.setup_custom_logger( "mqtt_thing_led_resource" )


class LedResource( Actuator ):

  def __init__( self, connector, mqtt_client, \
                sub_topic, \
                nuances_resolution ):
    
    super( LedResource, self ).__init__( connector, mqtt_client, \
                                         sub_topic, nuances_resolution )
    
    self.grovepi_interactor_member = InteractorMember( connector, \
                                                       'OUTPUT', \
                                                       DIGITAL_WRITE )

    self.value = False

    self.grovepi_interactor_member.tx_queue.put( \
        ( self.grovepi_interactor_member, int( self.value ) ) )
 

  def on_mqtt_message( self, client, userdata, message ):
    payload = str( "" )
    logger.debug( "Got message on topic: " + str( message.topic ) )
    payload = self.decode_payload_ascii_str( message.payload )

    if self.input_valid( payload ):
      new_value = self.str_to_bool( payload )

      if not self.is_equal( new_value, self.value ):
        self.value = new_value
        self.set_actuator( self.value )


  def set_actuator( self, value ):
    self.grovepi_interactor_member.tx_queue.put( \
        ( self.grovepi_interactor_member, int( self.value ) ) )
      

  def input_valid( self, input ): 
    # accept True/False or ON/OFF (case-insensitive)
    if not isinstance( input, str ):
      return False
    up = input.strip().lower()
    return up in ["true", "false", "on", "off"]

  
  def is_equal( self, a, b ):
    return a == b
  

  def tear_down( self ): 
    logger.debug( "tearing things down ..." )
    self.set_actuator( int( 0 ) )


  def decode_payload_ascii_str( self, payload ):
    ascii_str = str( "" )

    if( isinstance( payload, bytes ) ):
      try:
        ascii_str = str( payload.decode( 'ascii' ) )
      except ValueError:
        logger.debug( "received payload does not contain anything convertible to bool" )
      except Exception:
        logger.debug( "Exception occurred while converting payload to bool" )
    else:
      try:
        # try to convert non-bytes to str
        ascii_str = str(payload)
      except Exception:
        logger.debug( "To decode message payload you have to use an array of bytes as input." )
      
    return ascii_str
  

  def str_to_bool( self, bool_as_str ):
    # Accept True/False/ON/OFF (case-insensitive)
    if not isinstance(bool_as_str, str):
        return False
    s = bool_as_str.strip().lower()
    return s == "true" or s == "on"
