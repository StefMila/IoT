#!/usr/bin/env python3

import threading
import mqttconfig


class Actuator( threading.Thread ):

  def __init__( self, connector, \
                mqtt_client, \
                sub_topic, \
                nuances_resolution = int( 2 ) ):

    self.connector = connector
    self.mqtt_client = mqtt_client
    self.sub_topic = sub_topic
    self.nuances_resolution = nuances_resolution
    self.grovepi_interactor_member = None

    # subscribe will be done by caller after mqtt client created

  # Function has to be overridden in derived class.
  def on_mqtt_message( self, client, userdata, message ):
    pass  


  # Function has to be overridden in derived class.
  def set_actuator( self, value ):
    pass

  
  # Function has to be overridden in derived class.
  def input_valid( self, input ):
    pass
	
  
  # Function has to be overridden in derived class.
  def is_equal( self, a, b ):
    pass


  # Function has to be overridden in derived class.
  def tear_down( self ):
    pass
