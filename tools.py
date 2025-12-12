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


    File:          tools.py
    

    Purpose:       This module contains generic
                   functions mainly to acces
                   hardware resources of the
                   current operating system.
                   
    
    Remarks:       - Most of the functions
                     require root access.
                     Therefore scripts
                     which use functions
                     of this module have
                     to be run as root / 
                     sudoer.
    

    Author:        P. Leibundgut <leiu@zhaw.ch>
    

    Date:          10/2016


'''

import sys

import netifaces as ni
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE


def get_ip_address_by_if_name( interface_name ):
  return ni.ifaddresses( interface_name )[ AF_INET ][ 0 ][ 'addr' ]


def get_hw_address_by_if_name( interface_name ):
  return ni.ifaddresses( interface_name )[ AF_LINK ][ 0 ][ 'addr' ]

