#!/bin/bash

REPO_URL="https://github.com/Resch-Said/Hunters-Wake-On-Lan-Server.git"
INSTALL_DIR="/home/pi/Hunters-Wake-On-Lan-Server"
SERVICE_NAME="wol-server"

# Voraussetzungen installieren
sudo apt update
sudo apt install -y git python3-venv python3-pip iputils-ping

# Repository klonen oder updaten
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing repository..."
    cd "$INSTALL_DIR"
    # Versuche zu pullen, wenn es fehlschlägt wegen lokaler Änderungen, dann reset
    if ! git pull; then
        echo "Merge-Konflikt erkannt. Setze lokale Änderungen zurück..."
        git reset --hard
        git clean -fd
        git pull
    fi
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env Datei erstellen
if [ ! -f .env ]; then
    echo "Erstelle .env Datei..."
    read -p "Gib deinen Telegram Bot Token ein: " TELEGRAM_TOKEN
    read -p "Gib die erlaubten Telegram User IDs ein (kommagetrennt): " ALLOWED_USERS
    
    echo "TELEGRAM_TOKEN=$TELEGRAM_TOKEN" > .env
    echo "ALLOWED_USERS=$ALLOWED_USERS" >> .env
    chmod 600 .env
fi

# Erstelle leere computers.json wenn sie nicht existiert
if [ ! -f computers.json ]; then
    echo "{}" > computers.json
    chmod 600 computers.json
fi

# Systemd Service aktualisieren
echo "Erstelle Systemd Service..."
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Telegram Wake-on-LAN Bot
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$INSTALL_DIR/venv/bin/python3 server.py
WorkingDirectory=$INSTALL_DIR
User=pi
Restart=always
RestartSec=10
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Status anzeigen
echo -e "\n\033[1mInstallation abgeschlossen! Service-Status:\033[0m"
sudo systemctl status $SERVICE_NAME --no-pager | head -n 10

# Anzeige der Konfiguration am Ende
echo -e "\n\033[1mWichtige Informationen:\033[0m"
echo -e "🤖 Bot ist eingerichtet! Suche deinen Bot auf Telegram und sende /start"
echo -e "👤 Erlaubte User IDs: $ALLOWED_USERS"
echo -e "\n💡 Nutze /add [name] [mac] [ip] um Computer hinzuzufügen"
echo -e "   Beispiel: /add pc1 00:11:22:33:44:55 192.168.1.100"

exit 0