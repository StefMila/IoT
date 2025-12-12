# MQTT Multi-RPi — Istruzioni complete (italiano)
Questo progetto implementa un sistema MQTT distribuito su tre Raspberry Pi con sensori di temperatura/umidità e LED RGB:
- `red` (172.16.33.38): client che legge temperatura e umidità (sensore DHT/SHT35 su D3) e pubblica su MQTT.
- `purple` (172.16.33.37): client che legge temperatura e umidità (sensore DHT/SHT35 su D3), si sottoscrive ai topic LED rosso (D5) e verde (D6).
- `black` (172.16.32.182): server che esegue Mosquitto (broker), salva i dati in SQLite e pubblica comandi LED in base alle soglie di temperatura e umidità.

`git clone https://github.com/StefMila/IoT.git`

Topic principali:
- Sensori: `sensors/zone/<zone>/temperature` e `sensors/zone/<zone>/humidity` (payload JSON con zone, valore, timestamp)
- Attuatori: `actuators/zone/purple/led` (LED rosso per temperatura) e `actuators/zone/purple/led_humidity` (LED verde per umidità)

Configurazione Hardware (purple):
- **D3**: Sensore DHT/SHT35 (temperatura + umidità)
- **D5**: LED rosso (acceso se temperatura > soglia)
- **D6**: LED verde (acceso se umidità > soglia)

Prerequisiti (a grandi linee):
- Raspbian / Raspberry Pi OS con accesso SSH ai dispositivi indicati.
- Python 3, `pip` e `virtualenv` su ogni Pi.
- Mosquitto installato e avviato sul `black` (172.16.32.182).
- Se usi sensori reali: I2C abilitato su `red` e `purple` e sensore SHT35 con indirizzo 0x44 (o adattare lo script).
- Se usi GPIO reale su `purple`: `RPi.GPIO` installato e collegamento LED corretto.

Struttura dei file principali:
- `mqttthing.py` — script principale per red e purple (con supporto DHT, LED, sensor)
- `SHT35Resource.py` — classe per lettura sensore temperatura/umidità (supporta sia DHT via grovepi che SHT35 via smbus2)
- `LedResource.py` — classe per pilotaggio LED via GPIO (grovepi)
- `Sensor.py`, `Actuator.py` — classi base
- `grove_pi_interface.py` — interfaccia GrovePi
- `server.py` — server centrale (broker, DB, logica LED)
- `requirements.txt` — dipendenze Python (paho-mqtt, grovepi, smbus2)

Installazione e comandi (passaggi dettagliati)

1) Preparare il server `black` (172.16.32.182)

- Accedi via SSH: `ssh pi@172.16.32.182`
- Installa Mosquitto e strumenti utili:
   ```bash
   sudo apt update
   sudo apt install -y mosquitto mosquitto-clients sqlite3
   sudo systemctl enable --now mosquitto

   oppure

   ssh pi@172.16.32.182
   sudo systemctl start mosquitto
   sudo systemctl enable mosquitto
   sudo systemctl status mosquitto

   ```

- Posizionati nella cartella del progetto (dove hai copiato gli script) e crea un virtualenv:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

- Avvia il server:
   ```bash
   python3 server.py --broker 172.16.32.182 --threshold 22.0 --humidity-threshold 60.0
   ```

Test sul server:
- Vedi i messaggi sensore (temperatura e umidità) in tempo reale:
   ```bash
   mosquitto_sub -h 172.16.32.182 -t 'sensors/zone/+/#' -v
   ```
- Vedi i comandi LED pubblicati:
   ```bash
   mosquitto_sub -h 172.16.32.182 -t 'actuators/zone/purple/led#' -v
   ```
- Controlla il DB (temperatura e umidità):
   ```bash
   sqlite3 temperatures.db "SELECT id,zone,temperature,humidity,timestamp FROM readings ORDER BY id DESC LIMIT 20;"
   ```

2) Preparare `red` (172.16.33.38)

- Abilita I2C se usi DHT/SHT35: `sudo raspi-config` → Interfacing Options → I2C → enable.
- Crea virtualenv e installa dipendenze:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r /path/to/repo/requirements.txt
   ```
- Avvia il client (con sensore DHT su D3):
   ```bash
   sudo python3 mqttthing.py --role red --simulate
   ```
   (Usa `--simulate` per test senza sensore, rimuovi per usare sensore reale)

3) Preparare `purple` (172.16.33.37)

- Abilita I2C e GPIO se usi DHT/SHT35 e LED reali: `sudo raspi-config` → Interfacing Options → I2C → enable e GPIO → enable.
- Se userai GPIO reale per i LED, installa i driver:
   ```bash
   sudo apt install -y python3-rpi.gpio grovepi
   ```
- Crea virtualenv e installa dipendenze:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r /path/to/repo/requirements.txt
   ```
- Avvia il client (sensore su D3, LED rosso su D5, LED verde su D6):
   ```bash
   sudo python3 mqttthing.py --role purple --led-pin 5 --simulate
   ```
   (Usa `--simulate` per test senza sensore/LED reali; rimuovi per hardware reale)

Comportamento atteso
- Quando `red` o `purple` inviano temperature > soglia (default 22°C), il server pubblicherà `ON` sul topic `actuators/zone/purple/led` (LED rosso acceso).
- Quando `red` o `purple` inviano umidità > soglia umidità (default 60%), il server pubblicherà `ON` sul topic `actuators/zone/purple/led_humidity` (LED verde acceso).
- Il client `purple`, se attivo, riceverà i comandi e accenderà/spegnerà i LED su D5 (rosso) e D6 (verde), o stamperà lo stato se in simulazione.

Opzionale: systemd (esempi)
- Esempio file `/etc/systemd/system/mqtt-server.service` (modificare percorsi e utente):
   ```ini
   [Unit]
   Description=MQTT Server script
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/path/to/repo
   ExecStart=/home/pi/path/to/repo/venv/bin/python /home/pi/path/to/repo/server.py --broker 172.16.32.182 --threshold 22.0 --humidity-threshold 60.0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
- Abilitare e avviare:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now mqtt-server.service
   ```

Pubblicare su GitHub (PowerShell o terminale locale)
- Usa lo script `publish_to_github.ps1` presente nella cartella per inizializzare il repo e pushare. Esempio (PowerShell):
   ```powershell
   .\publish_to_github.ps1 -RemoteUrl git@github.com:USERNAME/REPO.git -Branch main -Message "Initial commit"
   ```
- Nota: lo script non può usare le tue credenziali da remoto. Se la prima push fallisce per autenticazione, configura la tua chiave SSH o usa un PAT (per HTTPS).

Suggerimenti `.gitignore`:
- `venv/`
- `temperatures.db`
- `__pycache__/`
- `.vscode/`

Problemi comuni e soluzioni rapide
- Se non vedi messaggi MQTT: controlla che Mosquitto sia in ascolto e che firewall/NAT non blocchino la porta 1883.
- Se il sensore I2C non risponde: verifica `i2cdetect -y 1` e assicurati che il sensore sia su D3 (indirizzo I2C: 0x44 per SHT35).
- Se il LED non si accende: verifica i permessi GPIO (`sudo`), che il pin sia corretto (D5 rosso, D6 verde) e il cablaggio.

Vuoi che io provi a eseguire i comandi `git` qui per creare il commit e tentare il push verso un tuo repository? Posso provarci ma:
- Ho bisogno dell'URL remoto (SSH o HTTPS).
- Non ho le tue credenziali: il push potrebbe fallire per autenticazione. In quel caso ti fornirò esattamente i comandi da eseguire localmente oppure potrai usare lo script `publish_to_github.ps1` che ho aggiunto.

Se vuoi che proceda a tentare il push da questo ambiente, inviami l'URL remoto (es. `git@github.com:USERNAME/REPO.git`) e conferma che va bene provare (attenzione: se l'URL è corretto ma non hai autorizzazione il push fallirà). 

---

## Comandi di avvio completi (rapido cheat sheet)

**Server (black):**
```bash
ssh pi@172.16.32.182
cd /path/to/repo
source venv/bin/activate
python3 server.py --broker 172.16.32.182 --threshold 22.0 --humidity-threshold 60.0
```

**Red:**
```bash
ssh pi@172.16.33.38
cd /path/to/repo
source venv/bin/activate
sudo python3 mqttthing.py --role red --simulate
```

**Purple:**
```bash
ssh pi@172.16.33.37
cd /path/to/repo
source venv/bin/activate
sudo python3 mqttthing.py --role purple --led-pin 5 --simulate
```

Argomenti disponibili:
- `--simulate`: testa senza hardware (sensori e LED simulati)
- `--threshold NUM`: soglia temperatura (default 22.0)
- `--humidity-threshold NUM`: soglia umidità (default 60.0)
- `--led-pin PIN`: pin LED rosso (purple, default 5)
 
# MQTT Multi-RPi Temperature Control

This workspace contains example Python scripts to implement the system you described:

- `red_client.py` — Zone *red* sensor publisher (SHT35)
- `purple_client.py` — Zone *purple* sensor publisher and LED actuator subscriber
- `server.py` — Central server: subscribes to sensors, stores data in SQLite, and publishes LED ON/OFF when threshold is exceeded
- `requirements.txt` — Python dependencies


Architecture summary
- RPi Black (server) runs Mosquitto broker and `server.py` to store readings and decide LED state.
- RPi Red runs `red_client.py` and publishes temperature to `sensors/zone/red/temperature`.
- RPi Purple runs `purple_client.py`, publishes to `sensors/zone/purple/temperature` and subscribes to `actuators/zone/purple/led` to control LED.

RPi network addresses (your environment):
- Purple (Viola): `ssh pi@172.16.33.37`
- Red (Rosso): `ssh pi@172.16.33.38`
- Black (Server/Nero): `ssh pi@172.16.32.182`

Topics
- Sensors: `sensors/zone/<zone>/temperature` (JSON payload: zone, temperature, timestamp)
- Actuator: `actuators/zone/purple/led` (payload: `ON` or `OFF`)

Setup notes
1. Install Mosquitto broker on the server (RPi black):

   On Raspbian / Debian:
   ```powershell
   sudo apt update; sudo apt install -y mosquitto mosquitto-clients
   sudo systemctl enable --now mosquitto
   ```

2. Create a Python virtualenv on each Pi and install requirements:

   ```powershell
   python3 -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt
   ```

   On Raspberry Pi, activate the venv and install: `pip3 install -r requirements.txt`.

3. Run the server (on black):

   ```powershell
   # on the black/server RPi (172.16.32.182)
   ssh pi@172.16.32.182
   python3 -m venv venv
   . venv/bin/activate
   pip install -r requirements.txt
   python server.py --broker 172.16.32.182 --threshold 22.0
   ```

4. Run the red client (on red RPi):

   ```powershell
   # on the red RPi (172.16.33.38)
   ssh pi@172.16.33.38
   python3 -m venv venv
   . venv/bin/activate
   pip install -r /path/to/repo/requirements.txt
   python red_client.py --broker 172.16.32.182 --interval 10 --simulate
   ```

5. Run the purple client (on purple RPi):

   ```powershell
   # on the purple RPi (172.16.33.37)
   ssh pi@172.16.33.37
   python3 -m venv venv
   . venv/bin/activate
   pip install -r /path/to/repo/requirements.txt
   python purple_client.py --broker 172.16.32.182 --interval 10 --simulate --led-pin 17
   ```

Notes and caveats
- The SHT35 reading uses low-level I2C via `smbus2`. If the SHT35 library or hardware is not available, use `--simulate` to publish simulated temperatures.
- `purple_client.py` will use `RPi.GPIO` if available to toggle a GPIO pin; otherwise it prints the intended LED action.
- The server stores readings in `temperatures.db` (SQLite) in the same folder.
- This repository only provides Python scripts. You must install and run Mosquitto on the server RPi.

If you want, I can:
- Add automatic service files / systemd units to run the scripts as services.
- Switch storage to InfluxDB instead of SQLite and show Grafana examples.


