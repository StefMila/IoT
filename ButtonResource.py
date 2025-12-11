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


    File:          ButtonResource.py
    

    Purpose:       Derived class from the
                   sensor class that
                   implements the concrete
                   behaviour of a GrovePi
                   button.

                   Class is based on
                   the abstract sensor
                   class.
                   
    
    Remarks:       - The GrovePi module has
                     to be installed to 
                     interact with the GrovePi
                     hardware.

                   - This class holds the value
                     of a button (true/false)
                     and publishes it to a
                     MQTT topic if it changes
                     its state.


    Author:        P. Leibundgut <leiu@zhaw.ch>
    
    
    Date:          10/2016

'''

import log
import mqttconfig

from Sensor import Sensor
from grove_pi_interface import InteractorMember, \
                               DIGITAL_READ, \
                               flush_queue


# logging setup
logger = log.setup_custom_logger( "mqtt_thing_button_resource" )

class ButtonResource( Sensor ):
  
  def __init__( self, connector, lock, \
                mqtt_client, running, \
                pub_topic, \
                polling_interval, \
                sampling_resolution ):
    
    super( ButtonResource, self ).__init__( connector, lock, \
                                            mqtt_client, running, \
                                            pub_topic, \
                                            polling_interval, \
                                            sampling_resolution )

    self.grovepi_interactor_member = InteractorMember( connector, \
                                                       'INPUT', \
                                                       DIGITAL_READ )
    
    self.value = False

  
  def read_sensor( self ):
    new_value = bool( False )

    self.grovepi_interactor_member.tx_queue.put( ( self.grovepi_interactor_member, ) )
    new_value = bool( self.grovepi_interactor_member.rx_queue.get() )
    self.grovepi_interactor_member.rx_queue.task_done()
    
    # flush the rx queue if more than one value was present
    flush_queue( self.grovepi_interactor_member.rx_queue )

    if not self.is_equal( self.value, new_value ):
      self.value = new_value
      self.lock.acquire()
      self.mqtt_client.publish( self.pub_topic, str( self.value ), \
                                mqttconfig.QUALITY_OF_SERVICE, False )
      self.lock.release()
      logger.debug( "---button value just toggled in a ButtonResource instance" )


  def is_equal( self, a, b ):
    return a == b

