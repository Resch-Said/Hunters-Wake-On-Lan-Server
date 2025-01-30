#!/bin/bash

REPO_URL="https://github.com/Resch-Said/Hunters-Wake-On-Lan-Server.git"
INSTALL_DIR="/home/pi/Hunters-Wake-On-Lan-Server"
SERVICE_NAME="wol-server"

# Voraussetzungen installieren
sudo apt update
sudo apt install -y git python3-venv python3-pip

# Repository klonen oder updaten
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing repository..."
    cd "$INSTALL_DIR"
    git pull
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
    read -p "Gib deinen API-Key ein: " API_KEY
    read -p "Gib die MAC-Adresse ein: " TARGET_MAC
    
    echo "API_KEY=$API_KEY" > .env
    echo "TARGET_MAC=$TARGET_MAC" >> .env
    chmod 600 .env
fi

# Systemd Service erstellen
echo "Erstelle Systemd Service..."
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Wake-on-LAN Server
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind [::]:5000 --worker-class gevent --workers 2 server:app
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
exit 0