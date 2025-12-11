#!/usr/bin/env python3

import sys
import threading

# For compatibility if grovepi not present, define placeholders
try:
    import grovepi
except Exception:
    grovepi = None

from queue import Queue

DIGITAL_READ  = (lambda pin: 0)
ANALOG_READ   = (lambda pin: 0)

DIGITAL_WRITE = (lambda pin, val: None)
ANALOG_WRITE  = (lambda pin, val: None)

if grovepi is not None:
    DIGITAL_READ = grovepi.digitalRead
    ANALOG_READ = grovepi.analogRead
    DIGITAL_WRITE = grovepi.digitalWrite
    ANALOG_WRITE = grovepi.analogWrite

running = True

grovepi_tx_queue = Queue()


def flush_queue( q ):
    while not q.empty():
        q.get()
        q.task_done()


class GrovePiInteractor( threading.Thread ):

    def __init__( self ):
        threading.Thread.__init__( self )
        self.lock = threading.Lock()


    def run( self ):
        self.process_tx_queue()


    def process_tx_queue( self ):
        self.lock.acquire()
        running_local = running
        self.lock.release()

        while running_local:
            value = grovepi_tx_queue.get()
            if value is None:
                break

            self.work_queue_entry( value )
            grovepi_tx_queue.task_done()

            self.lock.acquire()
            running_local = running
            self.lock.release()


    @staticmethod
    def work_queue_entry( value ):
        member = value[ 0 ]

        if not member.pin_mode_set and grovepi is not None:
            grovepi.pinMode( member.connector, member.direction )
            member.pin_mode_set = True

        if member.direction == 'OUTPUT':
            output_val = value[ 1 ]
            try:
                member.grovepi_func( member.connector, int( output_val ) )
            except Exception:
                print( "Error in writing to sensor at pin " + str( member.connector ) )

        elif member.direction == 'INPUT':
            try:
                input_val = member.grovepi_func( member.connector )
            except Exception:
                input_val = 0

            member.rx_queue.put( input_val )


    def stop_interactor( self ):
        global running
        self.lock.acquire()
        running = False
        self.lock.release()
        grovepi_tx_queue.put( None )


class InteractorMember( object ):

    def __init__( self, connector, direction, grovepi_func ):

        self.connector = connector
        self.direction = direction

        if self.direction == 'INPUT':
            self.rx_queue = Queue()
        else:
            self.rx_queue = None

        self.tx_queue = grovepi_tx_queue
        self.grovepi_func = grovepi_func
        self.pin_mode_set = False
