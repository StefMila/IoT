#!/usr/bin/env python3

'''
                    ___           ___           ___     
        ___        /\__\         /\  \         /\  \    
       /\  \      /::|  |       /::\  \       /::\  \   
       \:\  \    /:|:|  |      /:/\:\  \     /:/\ \  \  
       /::\__\  /:/|:|  |__   /::\~\:\  \   _\:\~\ \  \ 
    __/:/\/__/ /:/ |:| /\__\ /:/\:\ \:\__\ /\ \:\ \ \__\
   /\/:/  /    \/__|:|/:/  / \:\~\:\ \/__/ \:\ \:\ \/__/
   \::/__/         |:/:/  /   \:\ \:\__\    \:\ \:\__\  
    \:\__\         |::/  /     \:\ \/__/     \:\/:/  /  
     \/__/         /:/  /       \:\__\        \::/  /   
                   \/__/         \/__/         \/__/    


    File:          RotaryAngleResource.py
    

    Purpose:       Derived class from the
                   sensor class that
                   implements the concrete
                   behaviour of a GrovePi
                   rotary angle sensor.

                   Class is based on
                   the abstract sensor
                   class.
                   
    
    Remarks:       - The GrovePi module has
                     to be installed to 
                     interact with the GrovePi
                     hardware.

                   - This class holds the value
                     of a rotary angle sensor 
                     ([0,1023]) and publishes 
                     it to a MQTT topic if 
                     it changes its state.


    Author:        P. Leibundgut <leiu@zhaw.ch>
    
    
    Date:          10/2016

'''

import log
import mqttconfig

from Sensor import Sensor
from grove_pi_interface import InteractorMember, \
                               ANALOG_READ, \
                               flush_queue

# logging setup
logger = log.setup_custom_logger( "mqtt_thing_rotary_angle_resource" )

class RotaryAngleResource( Sensor ):
  
  def __init__( self, connector, lock, \
                mqtt_client, running, \
                pub_topic, \
                polling_interval, \
                sampling_resolution ):
    
    super( RotaryAngleResource, self ).__init__( connector, lock, \
                                                 mqtt_client, running, \
                                                 pub_topic, \
                                                 polling_interval, \
                                                 sampling_resolution )
    
    self.grovepi_interactor_member = InteractorMember( connector, \
                                                       'INPUT', \
                                                       ANALOG_READ )
    
    self.value = int( 0 )

  
  def read_sensor( self ):
    new_value = int( 0 )

    self.grovepi_interactor_member.tx_queue.put( ( self.grovepi_interactor_member, ) )
    new_value = int( self.grovepi_interactor_member.rx_queue.get() )
    self.grovepi_interactor_member.rx_queue.task_done()

    # flush the rx queue if more than one value was present
    flush_queue( self.grovepi_interactor_member.rx_queue )

    if not self.is_equal( self.value, new_value ):
      self.value = new_value
      self.lock.acquire()
      self.mqtt_client.publish( self.pub_topic, str( self.value ), \
                                mqttconfig.QUALITY_OF_SERVICE, False )
      self.lock.release()
      logger.debug( "---rotary angle sensor value just published its new value: " \
                    + str( self.value ) )


  def is_equal( self, a, b ):
    return a == b

