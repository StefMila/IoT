# Progetto IoT Multi-RPi con MQTT, Sensori Temperatura/Umidità e Attuatori LED

## Panoramica del Sistema

Sistema distribuito su tre Raspberry Pi che implementa monitoraggio ambientale (temperatura/umidità) e controllo automatico di attuatori (LED) tramite protocollo MQTT.

### Architettura

- **Black RPi** (172.16.32.182): Server centrale
  - Broker MQTT (Mosquitto)
  - Database SQLite per storico misurazioni
  - Logica di controllo soglie
  - Pubblicazione comandi attuatori

- **Red RPi** (172.16.33.38): Client sensore
  - Sensore temperatura/umidità (DHT/SHT35 su pin D3)
  - Pubblicazione dati su MQTT

- **Purple RPi** (172.16.33.37): Client sensore + attuatori
  - Sensore temperatura/umidità (DHT/SHT35 su pin D3)
  - LED rosso (pin D5) - Riscaldamento (termostato)
  - LED verde (pin D6) - Deumidificatore
  - Sottoscrizione comandi LED via MQTT

---

## Componenti Hardware

### Purple RPi (Client con attuatori)
| Componente | Pin | Funzione |
|------------|-----|----------|
| Sensore DHT/SHT35 | D3 | Lettura temperatura + umidità |
| LED Rosso | D5 | Indicatore riscaldamento (termostato) |
| LED Verde | D6 | Indicatore deumidificatore |

### Red RPi (Client solo sensore)
| Componente | Pin | Funzione |
|------------|-----|----------|
| Sensore DHT/SHT35 | D3 | Lettura temperatura + umidità |

---

## Topic MQTT

### Sensori (pubblicati da red/purple → consumati da black)
```
sensors/zone/red/temperature
sensors/zone/red/humidity
sensors/zone/purple/temperature
sensors/zone/purple/humidity
```

**Payload JSON:**
```json
{
  "zone": "red|purple",
  "temperature": 23.5,  // opzionale
  "humidity": 45.2,     // opzionale
  "timestamp": "2025-12-12T17:30:00.000000Z"
}
```

### Attuatori (pubblicati da black → consumati da purple)
```
actuators/zone/purple/led           # LED rosso (termostato)
actuators/zone/purple/led_humidity  # LED verde (deumidificatore)
```

**Payload:** `"ON"` o `"OFF"` (stringa)

---

## Logica di Controllo

### Termostato (LED Rosso - D5)
- **Soglia predefinita:** 30°C
- **Comportamento:**
  - Se `temperatura < soglia` in qualsiasi zona → LED rosso **ON** (riscaldamento attivo)
  - Se `temperatura >= soglia` in tutte le zone → LED rosso **OFF**

### Deumidificatore (LED Verde - D6)
- **Soglia predefinita:** 60%
- **Comportamento:**
  - Se `umidità > soglia` in qualsiasi zona → LED verde **ON** (deumidificatore attivo)
  - Se `umidità <= soglia` in tutte le zone → LED verde **OFF**

---

## Database SQLite

**File:** `temperatures.db` (su black RPi)

### Tabella `readings`
```sql
CREATE TABLE readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone TEXT NOT NULL,
    temperature REAL,        -- NULL se il messaggio conteneva solo umidità
    humidity REAL,           -- NULL se il messaggio conteneva solo temperatura
    timestamp TEXT NOT NULL
);
```

**Note:**
- Ogni sensore pubblica temperatura e umidità su topic separati
- Il server inserisce due righe per ogni lettura sensore (una per temp, una per umidità)
- Le query filtrano i NULL per ottenere l'ultimo valore valido di ciascuna metrica

---

## Struttura File del Progetto

```
Iot/
├── black/
│   ├── server.py              # Server principale (broker + DB + logica)
│   ├── mqttconfig.py          # Configurazione MQTT
│   ├── requirements.txt       # Dipendenze Python
│   └── temperatures.db        # Database SQLite (generato al runtime)
│
├── purple/
│   ├── mqttthing.py          # Client principale (sensore + LED)
│   ├── SHT35Resource.py      # Classe sensore temp/umidità
│   ├── LedResource.py        # Classe attuatore LED
│   ├── Actuator.py           # Classe base attuatori
│   ├── Sensor.py             # Classe base sensori
│   ├── grove_pi_interface.py # Interfaccia GrovePi GPIO
│   ├── mqttconfig.py         # Configurazione MQTT
│   └── requirements.txt      # Dipendenze Python
│
├── red/
│   ├── mqttthing.py          # Client principale (solo sensore)
│   ├── SHT35Resource.py      # Classe sensore temp/umidità
│   ├── Sensor.py             # Classe base sensori
│   ├── grove_pi_interface.py # Interfaccia GrovePi GPIO
│   ├── mqttconfig.py         # Configurazione MQTT
│   └── requirements.txt      # Dipendenze Python
│
└── README.md                  # Documentazione utente
```

---

## Installazione e Configurazione

### Prerequisiti Comuni (tutti i RPi)
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv i2c-tools
sudo raspi-config  # Abilita I2C in Interfacing Options
```

### 1. Setup Black RPi (Server)

```bash
# 1.1 Installa e avvia Mosquitto
sudo apt install -y mosquitto mosquitto-clients sqlite3
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# 1.2 Verifica broker
mosquitto_sub -h localhost -t '#' -v

# 1.3 Configura ambiente Python
cd ~/IoT/black
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1.4 Avvia il server
python3 server.py --broker 172.16.32.182 --threshold 30.0 --humidity-threshold 60.0
```

**Parametri del server:**
- `--broker`: IP del broker MQTT (localhost o IP pubblico se accessibile da altri RPi)
- `--threshold`: Soglia temperatura in °C (default: 22.0)
- `--humidity-threshold`: Soglia umidità in % (default: 60.0)

### 2. Setup Red RPi (Client Sensore)

```bash
# 2.1 Configura ambiente Python
cd ~/IoT/red
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2.2 Verifica sensore I2C (opzionale, se usi SHT35)
sudo i2cdetect -y 1  # Dovresti vedere 0x44

# 2.3 Avvia client
sudo python3 mqttthing.py --role red

# Modalità simulazione (senza hardware):
sudo python3 mqttthing.py --role red --simulate
```

### 3. Setup Purple RPi (Client Sensore + LED)

```bash
# 3.1 Installa driver GPIO
sudo apt install -y python3-rpi.gpio

# 3.2 Configura ambiente Python
cd ~/IoT/purple
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3.3 Avvia client
sudo python3 mqttthing.py --role purple --led-pin 5

# Modalità simulazione (senza hardware):
sudo python3 mqttthing.py --role purple --led-pin 5 --simulate
```

**Note:**
- `sudo` è necessario per accesso GPIO/I2C
- `--led-pin 5` specifica il pin del LED rosso (D5)
- Il LED verde (D6) è hardcoded nel codice
- Il sensore è sempre su pin D3

---

## Test e Verifica

### Test Broker MQTT (da qualsiasi RPi)
```bash
# Sottoscrivi a tutti i topic
mosquitto_sub -h 172.16.32.182 -t '#' -v

# Sottoscrivi solo sensori
mosquitto_sub -h 172.16.32.182 -t 'sensors/zone/+/#' -v

# Sottoscrivi solo attuatori
mosquitto_sub -h 172.16.32.182 -t 'actuators/zone/purple/#' -v
```

### Test Manuale LED (da qualsiasi RPi)
```bash
# Accendi LED rosso su purple
mosquitto_pub -h 172.16.32.182 -t 'actuators/zone/purple/led' -m 'ON'

# Accendi LED verde su purple
mosquitto_pub -h 172.16.32.182 -t 'actuators/zone/purple/led_humidity' -m 'ON'

# Spegni LED
mosquitto_pub -h 172.16.32.182 -t 'actuators/zone/purple/led' -m 'OFF'
mosquitto_pub -h 172.16.32.182 -t 'actuators/zone/purple/led_humidity' -m 'OFF'
```

### Test Hardware LED Diretto (su purple)
```bash
# Verifica che il LED D5 si accenda
sudo python3 -c "
import grovepi, time
grovepi.pinMode(5, 1)
grovepi.digitalWrite(5, 1)
print('LED D5 acceso per 3 secondi')
time.sleep(3)
grovepi.digitalWrite(5, 0)
print('LED spento')
"
```

### Query Database (su black)
```bash
# Connetti al database
sqlite3 ~/IoT/black/temperatures.db

# Configura output leggibile
.mode column
.headers on
.nullvalue "NULL"

# Query ultimi 20 record
SELECT id, zone, temperature, humidity, timestamp 
FROM readings 
ORDER BY id DESC 
LIMIT 20;

# Statistiche per zona
SELECT 
    zone,
    COUNT(*) as total_readings,
    AVG(temperature) as avg_temp,
    AVG(humidity) as avg_humidity,
    MAX(temperature) as max_temp,
    MAX(humidity) as max_humidity
FROM readings 
WHERE temperature IS NOT NULL OR humidity IS NOT NULL
GROUP BY zone;
```

---

## Troubleshooting

### Problema: LED non si accendono

**Diagnosi:**
1. Verifica che il broker sia raggiungibile:
   ```bash
   ping 172.16.32.182
   ```

2. Verifica che mosquitto sia running:
   ```bash
   ssh pi@172.16.32.182
   sudo systemctl status mosquitto
   ```

3. Controlla che il client riceva i messaggi (nell'output di mqttthing.py):
   ```
   DEBUG:mqtt_thing_led_resource:Got message on topic: actuators/zone/purple/led
   ```

4. Test hardware LED (vedi sezione Test)

**Soluzioni comuni:**
- Aggiungi delay dopo `loop_start()` in mqttthing.py (già implementato: `time.sleep(2)`)
- Verifica che le sottoscrizioni siano presenti:
  ```python
  mqtt_client.subscribe('actuators/zone/purple/led')
  mqtt_client.message_callback_add('actuators/zone/purple/led', led_red.on_mqtt_message)
  ```
- Riavvia mosquitto: `sudo systemctl restart mosquitto`

### Problema: Sensore non pubblica dati

**Diagnosi:**
1. Verifica connessione I2C:
   ```bash
   sudo i2cdetect -y 1
   ```
   Dovresti vedere `44` se usi SHT35.

2. Controlla errori nell'output di mqttthing.py

**Soluzioni comuni:**
- Usa modalità simulazione: `--simulate`
- Verifica che I2C sia abilitato in `raspi-config`
- Per DHT, verifica cablaggio pin D3

### Problema: Database non si aggiorna

**Diagnosi:**
1. Verifica che il server stampi "Received ..." nell'output
2. Controlla permessi file database:
   ```bash
   ls -l ~/IoT/black/temperatures.db
   ```

**Soluzioni comuni:**
- Il database si crea automaticamente al primo messaggio
- Verifica che il server sia in esecuzione e connesso al broker

### Problema: AttributeError 'NoneType' object has no attribute 'recv'

**Causa:** Disconnessione MQTT o broker non raggiungibile.

**Soluzione:**
1. Riavvia mosquitto su black
2. Verifica connettività di rete
3. Aggiungi gestione reconnect in mqttthing.py (già presente)

---

## Avvio Automatico con systemd (Opzionale)

### Service per Black (Server)

File: `/etc/systemd/system/mqtt-server.service`
```ini
[Unit]
Description=MQTT IoT Server
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/IoT/black
ExecStart=/home/pi/IoT/black/venv/bin/python3 /home/pi/IoT/black/server.py --broker 172.16.32.182 --threshold 30.0 --humidity-threshold 60.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Attiva:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mqtt-server.service
sudo systemctl start mqtt-server.service
```

### Service per Purple (Client)

File: `/etc/systemd/system/mqtt-purple-client.service`
```ini
[Unit]
Description=MQTT IoT Purple Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/IoT/purple
ExecStart=/home/pi/IoT/purple/venv/bin/python3 /home/pi/IoT/purple/mqttthing.py --role purple --led-pin 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Attiva:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mqtt-purple-client.service
sudo systemctl start mqtt-purple-client.service
```

### Service per Red (Client)

File: `/etc/systemd/system/mqtt-red-client.service`
```ini
[Unit]
Description=MQTT IoT Red Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/IoT/red
ExecStart=/home/pi/IoT/red/venv/bin/python3 /home/pi/IoT/red/mqttthing.py --role red
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Attiva:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mqtt-red-client.service
sudo systemctl start mqtt-red-client.service
```

---

## Dipendenze Python

### requirements.txt (tutti i client)
```
paho-mqtt>=1.6.1
grovepi
smbus2
```

### Installazione dipendenze
```bash
pip install paho-mqtt grovepi smbus2
```

**Note:**
- `paho-mqtt`: Client MQTT Python
- `grovepi`: Libreria per GPIO GrovePi (LED, sensori DHT)
- `smbus2`: Comunicazione I2C per sensori SHT35

---

## Flusso di Dati

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│  Red RPi    │          │  Black RPi  │          │ Purple RPi  │
│             │          │  (Broker)   │          │             │
├─────────────┤          ├─────────────┤          ├─────────────┤
│ Sensore D3  │─publish─→│  Mosquitto  │          │ Sensore D3  │─publish─┐
│             │          │             │          │             │         │
│             │          │   SQLite    │          │  LED D5     │←─sub────┤
│             │          │             │          │  LED D6     │←─sub────┤
└─────────────┘          │   Server    │          └─────────────┘         │
                         │   Logic     │                                  │
                         └──────┬──────┘                                  │
                                │                                         │
                                └─────────publish LED commands────────────┘

Topic Flow:
1. sensors/zone/red/temperature     → Black
2. sensors/zone/red/humidity        → Black
3. sensors/zone/purple/temperature  → Black
4. sensors/zone/purple/humidity     → Black
5. Black evalua soglie
6. actuators/zone/purple/led        → Purple (LED rosso D5)
7. actuators/zone/purple/led_humidity → Purple (LED verde D6)
```

---

## Note Implementative

### SHT35Resource.py
- Supporta sia sensori DHT (via grovepi) che SHT35 (via I2C/smbus2)
- Parametro `use_dht=True` per usare DHT, `False` per SHT35
- Pubblica su due topic separati: `../temperature` e `../humidity`
- Gestisce fallback a valori simulati se hardware non disponibile

### LedResource.py
- Eredita da `Actuator`
- Sottoscrizione MQTT gestita manualmente in `mqttthing.py` (non in `__init__`)
- Converte payload stringa ('ON'/'OFF') in valori booleani
- Usa `grove_pi_interface.py` per comunicare con GPIO via thread separato

### Server.py
- Database thread-safe con lock per insert/query concorrenti
- Migrazione automatica schema DB (aggiunge colonna `humidity` se mancante)
- Valuta soglie dopo ogni messaggio ricevuto
- Pubblica comandi LED solo se lo stato cambia (evita spam MQTT)

---

## Estensioni Possibili

1. **Dashboard Web:**
   - Aggiungi Flask/FastAPI su black per visualizzare dati real-time
   - Grafici temperatura/umidità con Chart.js

2. **Notifiche:**
   - Invia email/Telegram quando soglie superate
   - Usa SMTP o API Telegram Bot

3. **Controllo Remoto:**
   - Aggiungi topic MQTT per modifica soglie dinamica
   - Web UI per controllo LED manuale

4. **Più Zone:**
   - Aggiungi altri RPi client con zone diverse
   - Logica server già supporta zone multiple

5. **Logging Avanzato:**
   - Rotazione log con `logging.handlers.RotatingFileHandler`
   - Aggregazione metriche giornaliere

---

## Riferimenti e Crediti

- **Protocollo MQTT:** [https://mqtt.org/](https://mqtt.org/)
- **Paho MQTT Python:** [https://github.com/eclipse/paho.mqtt.python](https://github.com/eclipse/paho.mqtt.python)
- **GrovePi:** [https://github.com/DexterInd/GrovePi](https://github.com/DexterInd/GrovePi)
- **SHT35 Datasheet:** [Sensirion SHT3x](https://www.sensirion.com/en/environmental-sensors/humidity-sensors/digital-humidity-sensors-for-various-applications/)

---

## Licenza

Progetto educativo per corso IoT - libero utilizzo per scopi didattici.

---

**Ultima revisione:** 12 Dicembre 2025
**Versione:** 1.0
