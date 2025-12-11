#!/usr/bin/env python3
"""
SHT35Resource.py

Sensor subclass to read SHT35 temperature and humidity and publish via MQTT when value changes.
If `smbus2` is not available or I2C is not configured, it can run in simulation mode.
"""
import time
import threading
import json
import logging
import math
from datetime import datetime

import mqttconfig
from Sensor import Sensor

try:
    from smbus2 import SMBus
    HAS_SMBUS = True
except Exception:
    SMBus = None
    HAS_SMBUS = False

try:
    import grovepi
    HAS_GROVEPI = True
except Exception:
    grovepi = None
    HAS_GROVEPI = False

logger = logging.getLogger("mqtt_thing_sht35_resource")


class SHT35Resource(Sensor):
    def __init__(self, connector, lock, mqtt_client, running, pub_topic,
                 polling_interval=5.0, simulate=False, bus_num=1, i2c_addr=0x44,
                 use_dht=False, dht_port=None, dht_type=1):
        """
        Args:
            connector: I2C bus or connector number
            lock: threading lock
            mqtt_client: MQTT client
            running: running flag
            pub_topic: topic to publish temperature (humidity topic auto-generated)
            polling_interval: polling interval in seconds
            simulate: if True, simulate sensor values
            bus_num: I2C bus number (default 1)
            i2c_addr: I2C address (default 0x44 for SHT35)
            use_dht: if True, use grovepi.dht() for DHT sensor; if False, use SHT35 via smbus2
            dht_port: GrovePi connector port (if use_dht=True)
            dht_type: DHT type: 0=BLUE, 1=WHITE (default)
        """
        super(SHT35Resource, self).__init__(connector, lock, mqtt_client, running,
                                            pub_topic, polling_interval, sampling_resolution=0)
        self.simulate = simulate
        self.bus_num = bus_num
        self.i2c_addr = i2c_addr
        self.use_dht = use_dht
        self.dht_port = dht_port
        self.dht_type = dht_type
        self.value = None
        self.humidity = None
        # Generiamo il topic per umidità
        self.humidity_topic = pub_topic.replace('/temperature', '/humidity')

    def read_sensor(self):
        new_value = None
        new_humidity = None
        
        if self.use_dht and HAS_GROVEPI and self.dht_port is not None:
            # Usa sensore DHT via GrovePi
            try:
                res = grovepi.dht(self.dht_port, self.dht_type)
                if isinstance(res, (list, tuple)) and len(res) >= 2:
                    temp, hum = res[0], res[1]
                    if not math.isnan(temp) and not math.isnan(hum):
                        new_value = round(temp, 2)
                        new_humidity = round(hum, 2)
                    else:
                        logger.debug("DHT reading returned NaN")
                else:
                    logger.debug("DHT reading unexpected format: %s", res)
            except IOError:
                logger.debug("DHT IOError - will use simulated values")
            except Exception as e:
                logger.debug("DHT read failed: %s", e)
        elif self.simulate or not HAS_SMBUS:
            # Simulated values
            import random
            new_value = round(20.0 + random.uniform(-3.0, 3.0), 2)
            new_humidity = round(50.0 + random.uniform(-10.0, 10.0), 2)
        else:
            # SHT35 via smbus2
            try:
                with SMBus(self.bus_num) as bus:
                    # single shot high repeatability: command 0x2C 0x06
                    bus.write_i2c_block_data(self.i2c_addr, 0x2C, [0x06])
                    time.sleep(0.015)
                    data = bus.read_i2c_block_data(self.i2c_addr, 0x00, 6)
                    # Temperature: bytes 0-1
                    t_raw = data[0] << 8 | data[1]
                    temp_c = -45.0 + 175.0 * (t_raw / 65535.0)
                    new_value = round(temp_c, 2)
                    # Humidity: bytes 3-4
                    h_raw = data[3] << 8 | data[4]
                    humidity_pct = 100.0 * (h_raw / 65535.0)
                    new_humidity = round(humidity_pct, 2)
            except Exception as e:
                logger.debug("SHT35 read failed: %s, will use simulated values", e)
                # fallback to simulated
                import random
                new_value = round(20.0 + random.uniform(-3.0, 3.0), 2)
                new_humidity = round(50.0 + random.uniform(-10.0, 10.0), 2)

        # Pubblica temperatura se cambiata
        if self.value is None or not self.is_equal(self.value, new_value):
            self.value = new_value
            zone = self.pub_topic.split('/')[-2] if '/' in self.pub_topic else 'unknown'
            payload = json.dumps({"zone": zone,
                                  "temperature": self.value,
                                  "timestamp": datetime.utcnow().isoformat() + 'Z'})
            self.lock.acquire()
            try:
                self.mqtt_client.publish(self.pub_topic, payload, mqttconfig.QUALITY_OF_SERVICE, False)
            finally:
                self.lock.release()
            logger.debug("Published SHT35 temperature %s to %s", self.value, self.pub_topic)

        # Pubblica umidità se cambiata
        if self.humidity is None or not self.is_equal(self.humidity, new_humidity):
            self.humidity = new_humidity
            zone = self.pub_topic.split('/')[-2] if '/' in self.pub_topic else 'unknown'
            payload = json.dumps({"zone": zone,
                                  "humidity": self.humidity,
                                  "timestamp": datetime.utcnow().isoformat() + 'Z'})
            self.lock.acquire()
            try:
                self.mqtt_client.publish(self.humidity_topic, payload, mqttconfig.QUALITY_OF_SERVICE, False)
            finally:
                self.lock.release()
            logger.debug("Published SHT35 humidity %s to %s", self.humidity, self.humidity_topic)

    def is_equal(self, a, b):
        return a == b
