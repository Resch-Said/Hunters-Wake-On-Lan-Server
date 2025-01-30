# Hunters Wake-On-LAN Server

Ein einfacher Server zur Fernsteuerung von Computern über Wake-on-LAN.

## Funktionsweise

Der Server ermöglicht das Aufwecken von Computern im Netzwerk über das Wake-on-LAN Protokoll. Die Anwendung läuft als Webserver und bietet eine REST-API zum Senden von Wake-on-LAN Paketen.

## Voraussetzungen

- Python 3.x
- Flask (Python-Webframework)
- wakeonlan Paket (`pip install wakeonlan`)

## Installation

1. Repository klonen:
```bash
git clone https://github.com/Resch-Said/Hunters-Wake-On-Lan-Server.git
cd Hunters-Wake-On-Lan-Server
```

2. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

## Als Service auf dem Raspberry Pi einrichten

1. Service-Datei erstellen:
```bash
sudo nano /etc/systemd/system/wol-server.service
```

2. Folgenden Inhalt in die Service-Datei einfügen:
```ini
[Unit]
Description=Wake-on-LAN Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /pfad/zur/app.py
WorkingDirectory=/pfad/zum/projektverzeichnis
User=pi
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Service aktivieren und starten:
```bash
sudo systemctl enable wol-server
sudo systemctl start wol-server
```

4. Status überprüfen:
```bash
sudo systemctl status wol-server
```

## Verwendung

Der Server läuft standardmäßig auf Port 5000. Um einen Computer aufzuwecken, senden Sie eine POST-Anfrage an:

```
http://[server-ip]:5000/wake?key=dein_geheimer_schluessel
```

Mit folgendem JSON-Body:
```json
{
    "mac": "00:11:22:33:44:55"
}
```

### Beispiel mit CURL

```bash
curl -X POST "http://[deine-ipv6-adresse]:5000/wake?key=dein_geheimer_schluessel"
```

## Troubleshooting

- Stellen Sie sicher, dass Wake-on-LAN im BIOS des Zielcomputers aktiviert ist
- Überprüfen Sie, ob die MAC-Adresse korrekt ist
- Prüfen Sie die Firewall-Einstellungen
