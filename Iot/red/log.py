#!/usr/bin/env python3

import logging


def setup_custom_logger( name ):

  logging.basicConfig( level = logging.INFO )
  logger = logging.getLogger( name )
  logger.setLevel( logging.DEBUG )
  
  return logger
