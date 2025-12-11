#!/usr/bin/env python3

"""
mqttthing.py

Main program that creates resources using the project's Sensor/Actuator
architecture. This version creates two SHT35 sensors (red and purple) and
an LED actuator on the purple Pi. The GrovePi interactor is started if
required by actuators.

Usage: python3 mqttthing.py
"""

import signal
import threading
import log
import mqttconfig

from SHT35Resource import SHT35Resource
from LedResource import LedResource
from grove_pi_interface import GrovePiInteractor

# network and pins config (adapt to your hardware)
NETWORK_INTERFACE = "eth0"

# topics
LOCAL_IP = None

# logging setup
logger = log.setup_custom_logger("mqtt_thing_main")

# --- application globals ---
lock = threading.Lock()
resources = {}
mqtt_client = None

# create a single instance of GrovePi interactor (used by LedResource)
gpi = GrovePiInteractor()


def signal_handler(*args):
    logger.debug("Shutting down, tearing down resources...")
    # stop sensor threads and actuators
    for key, res in resources.items():
        try:
            if hasattr(res, 'running'):
                res.running = False
            if hasattr(res, 'tear_down'):
                res.tear_down()
        except Exception:
            pass

    # stop grovepi interactor
    try:
        gpi.stop_interactor()
    except Exception:
        pass

    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass


def main():
    global mqtt_client, LOCAL_IP

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=['red', 'purple'], required=True, help='Role of this Pi: red or purple')
    parser.add_argument('--simulate', action='store_true', help='Simulate sensors (no I2C)')
    parser.add_argument('--led-pin', type=int, default=4, help='GrovePi connector pin for LED (purple)')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    # default broker setup
    mqtt_client = mqttconfig.setup_mqtt_client("0.0.0.0")

    # start the GrovePi interactor thread (needed by LedResource when used)
    gpi.start()

    # create resources based on role
    if args.role == 'red':
        resources['sht_red'] = SHT35Resource(connector=0,
                                             lock=lock,
                                             mqtt_client=mqtt_client,
                                             running=True,
                                             pub_topic='sensors/zone/red/temperature',
                                             polling_interval=10.0,
                                             simulate=args.simulate,
                                             use_dht=True,
                                             dht_port=3,
                                             dht_type=1)  # WHITE sensor
    elif args.role == 'purple':
        resources['sht_purple'] = SHT35Resource(connector=0,
                                                lock=lock,
                                                mqtt_client=mqtt_client,
                                                running=True,
                                                pub_topic='sensors/zone/purple/temperature',
                                                polling_interval=10.0,
                                                simulate=args.simulate,
                                                use_dht=True,
                                                dht_port=3,
                                                dht_type=1)  # WHITE sensor

        # LED actuator on purple (rosso - temperatura)
        resources['led_purple'] = LedResource(connector=args.led_pin,
                                              mqtt_client=mqtt_client,
                                              sub_topic='actuators/zone/purple/led',
                                              nuances_resolution=2)

        # LED actuator on purple (verde - umidità) su D6
        resources['led_humidity'] = LedResource(connector=6,
                                                mqtt_client=mqtt_client,
                                                sub_topic='actuators/zone/purple/led_humidity',
                                                nuances_resolution=2)

    # start sensor threads
    for key, res in resources.items():
        if hasattr(res, 'start') and callable(res.start):
            try:
                res.start()
            except Exception:
                pass

    # main thread just waits until interrupted
    try:
        while True:
            signal.pause()
    except KeyboardInterrupt:
        signal_handler()


if __name__ == '__main__':
    main()
