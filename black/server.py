#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime
import threading

import paho.mqtt.client as mqtt

DB_FILE = "temperatures.db"
SENSOR_TEMP_TOPIC = "sensors/zone/+/temperature"
SENSOR_HUMIDITY_TOPIC = "sensors/zone/+/humidity"
LED_TEMP_TOPIC = "actuators/zone/purple/led"
LED_HUMIDITY_TOPIC = "actuators/zone/purple/led_humidity"


class EnvironmentDB:
    def __init__(self, filename=DB_FILE):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self._init_db()
        self.lock = threading.Lock()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                timestamp TEXT NOT NULL
            )
        """)
        # Backward-compatible migration if the table already exists without humidity
        cur.execute("PRAGMA table_info(readings)")
        columns = {row[1] for row in cur.fetchall()}
        if "humidity" not in columns:
            cur.execute("ALTER TABLE readings ADD COLUMN humidity REAL")
        self.conn.commit()

    def insert(self, zone, temperature, humidity, timestamp):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO readings(zone, temperature, humidity, timestamp) VALUES (?, ?, ?, ?)",
                (zone, temperature, humidity, timestamp),
            )
            self.conn.commit()

    def last_temperature(self, zone):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT temperature FROM readings WHERE zone = ? AND temperature IS NOT NULL ORDER BY id DESC LIMIT 1",
                (zone,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def last_humidity(self, zone):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT humidity FROM readings WHERE zone = ? AND humidity IS NOT NULL ORDER BY id DESC LIMIT 1",
                (zone,),
            )
            row = cur.fetchone()
            return row[0] if row else None


class BrokerServer:
    def __init__(self, broker, temp_threshold=22.0, humidity_threshold=60.0):
        self.broker = broker
        self.db = EnvironmentDB()
        self.temp_threshold = float(temp_threshold)
        self.humidity_threshold = float(humidity_threshold)
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.last_temp_led_state = None
        self.last_humidity_led_state = None

    def on_connect(self, client, userdata, flags, rc):
        print("Server connected to broker, subscribing to sensor topics")
        client.subscribe(SENSOR_TEMP_TOPIC)
        client.subscribe(SENSOR_HUMIDITY_TOPIC)

    def on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)
            zone = data.get("zone")
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            ts = data.get("timestamp") or datetime.utcnow().isoformat() + "Z"
            temperature = float(temperature) if temperature is not None else None
            humidity = float(humidity) if humidity is not None else None
        except Exception as e:
            print(f"Failed to parse message {message.topic}: {e}")
            return

        if zone is None:
            print(f"Ignoring message without zone: {payload}")
            return

        if temperature is None and humidity is None:
            print(f"Ignoring message without temperature or humidity: {payload}")
            return

        print(f"Received {zone} temp={temperature}C hum={humidity}% @ {ts}")
        self.db.insert(zone, temperature, humidity, ts)
        self.evaluate_and_publish()

    def evaluate_and_publish(self):
        """Check thresholds and publish LED commands"""
        # Temperature: LED ON if temp < threshold (heating needed)
        red_temp = self.db.last_temperature('red')
        purple_temp = self.db.last_temperature('purple')

        should_on_temp = False
        for val in (red_temp, purple_temp):
            if val is not None and val < self.temp_threshold:
                should_on_temp = True
                break

        new_state_temp = 'ON' if should_on_temp else 'OFF'
        if new_state_temp != self.last_temp_led_state:
            self.client.publish(LED_TEMP_TOPIC, new_state_temp)
            print(f"Published temperature LED command: {new_state_temp}")
            self.last_temp_led_state = new_state_temp

        # Humidity: LED ON if humidity > threshold (dehumidifier needed)
        red_hum = self.db.last_humidity('red')
        purple_hum = self.db.last_humidity('purple')

        should_on_hum = False
        for val in (red_hum, purple_hum):
            if val is not None and val > self.humidity_threshold:  # invertito: > invece di <
                should_on_hum = True
                break

        new_state_hum = 'ON' if should_on_hum else 'OFF'
        if new_state_hum != self.last_humidity_led_state:
            self.client.publish(LED_HUMIDITY_TOPIC, new_state_hum)
            print(f"Published humidity LED command: {new_state_hum}")
            self.last_humidity_led_state = new_state_hum

    def start(self):
        self.client.connect(self.broker, 1883, 60)
        self.client.loop_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="localhost", help="Broker IP to connect to (where Mosquitto runs)")
    parser.add_argument("--threshold", type=float, default=22.0, help="Temperature threshold (C)")
    parser.add_argument(
        "--humidity-threshold", type=float, default=60.0, help="Humidity threshold (%) for green LED"
    )
    args = parser.parse_args()

    server = BrokerServer(args.broker, args.threshold, args.humidity_threshold)
    try:
        server.start()
    except KeyboardInterrupt:
        print("Stopping server")


if __name__ == "__main__":
    main()