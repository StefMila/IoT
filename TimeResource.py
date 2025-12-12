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


    File:          TimeResource.py
    

    Purpose:       Derived class from the
                   python internal thread class.
                   
                   This resource's pupose
                   is to get the operating
                   system's time and publish
                   it under a MQTT topic.
                   The querying time interval of
                   the resource is currently
                   set to 2 seconds.
                   
    
    Remarks:       - 


    Author:        P. Leibundgut <leiu@zhaw.ch>
    
    
    Date:          10/2016

'''

import threading
import datetime
import time

import log
import mqttconfig


ALIVE_CHECK_INTERVAL_IN_MILLIS = int( 100 )
ALIVE_CHECK_INTERVAL_IN_S = float( ALIVE_CHECK_INTERVAL_IN_MILLIS / 1000 )


# logging setup
logger = log.setup_custom_logger( "mqtt_thing_time_resource" )


class TimeResource( threading.Thread ):
    
  def __init__( self, lock, \
                mqtt_client, \
                running, \
                pub_topic, \
                pub_interval = float( 2.0 ) ):
    
    # must be called ...
    threading.Thread.__init__( self )
       
    self.lock = lock
    self.mqtt_client = mqtt_client
    self.running = running
    self.pub_topic = pub_topic
    self.pub_interval = pub_interval # unit is seconds ...


  def query_system_time( self ):
    keep_querying = bool( False )
    pub_interval_in_millis = int( self.pub_interval * 1000 )

    sleep_periods = int( pub_interval_in_millis // ALIVE_CHECK_INTERVAL_IN_MILLIS )
    
    self.lock.acquire()
    keep_querying = self.running
    self.lock.release()

    while keep_querying:
      
      payload = str( datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" ) )
      self.mqtt_client.publish( self.pub_topic, str( payload ), \
                                mqttconfig.QUALITY_OF_SERVICE, False )

      for _ in range( 0, sleep_periods ):
        time.sleep( ALIVE_CHECK_INTERVAL_IN_S )
        self.lock.acquire()
        keep_querying = self.running
        self.lock.release()
        if not keep_querying:
          break


  def run( self ):
    self.query_system_time()

