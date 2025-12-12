#!/usr/bin/env python3

import time
import threading 


class Sensor( threading.Thread ):

  def __init__( self, connector, lock, \
                mqtt_client, running, \
                pub_topic, \
                polling_interval = float( 1.0 ), \
                sampling_resolution = int( 2 ) ):
    
    # must be called ...
    threading.Thread.__init__( self )

    self.connector = connector
    self.lock = lock
    self.mqtt_client = mqtt_client
    self.running = running
    self.pub_topic = pub_topic
    self.polling_interval = polling_interval
    self.sampling_resolution = sampling_resolution
    self.grovepi_interactor_member = None


  def poll_sensor( self ):
    still_polling = False

    self.lock.acquire()
    still_polling = self.running
    self.lock.release()
    
    while still_polling:
      self.read_sensor()
      time.sleep( self.polling_interval )

      self.lock.acquire()
      still_polling = self.running
      self.lock.release()

  
  # gets invoked when thread starts ...
  def run( self ):
    self.poll_sensor()


  # Function has to be overridden in derived class.
  def read_sensor( self ):
    pass


  # Function has to be overridden in derived class.
  def is_equal( self, a, b ):
    pass
