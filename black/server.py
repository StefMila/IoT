#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime
import threading

import paho.mqtt.client as mqtt

DB_FILE = "temperatures.db"
SENSOR_TOPIC = "sensors/zone/+/temperature"
LED_TOPIC = "actuators/zone/purple/led"


class TemperatureDB:
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
                temperature REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def insert(self, zone, temperature, timestamp):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO readings(zone, temperature, timestamp) VALUES (?, ?, ?)",
                        (zone, temperature, timestamp))
            self.conn.commit()

    def last_temperature(self, zone):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("SELECT temperature FROM readings WHERE zone = ? ORDER BY id DESC LIMIT 1", (zone,))
            row = cur.fetchone()
            return row[0] if row else None


class BrokerServer:
    def __init__(self, broker, threshold=22.0):
        self.broker = broker
        self.db = TemperatureDB()
        self.threshold = float(threshold)
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.last_led_state = None

    def on_connect(self, client, userdata, flags, rc):
        print("Server connected to broker, subscribing to sensor topics")
        client.subscribe(SENSOR_TOPIC)

    def on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode('utf-8')
            data = json.loads(payload)
            zone = data.get('zone')
            temp = float(data.get('temperature'))
            ts = data.get('timestamp') or datetime.utcnow().isoformat() + 'Z'
        except Exception as e:
            print(f"Failed to parse message {message.topic}: {e}")
            return

        print(f"Received {zone} {temp}C @ {ts}")
        self.db.insert(zone, temp, ts)
        self.evaluate_and_publish()

    def evaluate_and_publish(self):
        red = self.db.last_temperature('red')
        purple = self.db.last_temperature('purple')

        should_on = False
        for val in (red, purple):
            if val is not None and val > self.threshold:
                should_on = True
                break

        new_state = 'ON' if should_on else 'OFF'
        if new_state != self.last_led_state:
            self.client.publish(LED_TOPIC, new_state)
            print(f"Published LED command: {new_state}")
            self.last_led_state = new_state

    def start(self):
        self.client.connect(self.broker, 1883, 60)
        self.client.loop_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default='localhost', help="Broker IP to connect to (where Mosquitto runs)")
    parser.add_argument("--threshold", type=float, default=22.0, help="Temperature threshold (C)")
    args = parser.parse_args()

    server = BrokerServer(args.broker, args.threshold)
    try:
        server.start()
    except KeyboardInterrupt:
        print("Stopping server")
