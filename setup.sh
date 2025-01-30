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

# API-Key aus .env Datei lesen
STORED_API_KEY=$(grep API_KEY .env | cut -d'=' -f2)

# IP und API-Key Information anzeigen
echo -e "\n\033[1mWichtige Informationen:\033[0m"
echo -e "\033[1mAPI-Key:\033[0m $STORED_API_KEY"
IPV6=$(curl -s -6 https://api6.ipify.org 2>/dev/null || echo "Nicht verfügbar")
echo -e "\033[1mÖffentliche IPv6:\033[0m $IPV6"
echo -e "\033[1mÖffentliche IPv4:\033[0m $(curl -s -4 https://api.ipify.org 2>/dev/null || echo "Nicht verfügbar")"
echo -e "\nDu kannst den Wake-on-LAN Befehl mit einem der folgenden Befehle ausführen:"
echo "Linux/Mac:"
echo "curl -X POST 'http://[$IPV6]:5000/wake?key=$STORED_API_KEY'"
echo -e "\nWindows PowerShell:"
echo "Invoke-WebRequest -Uri \"http://[$IPV6]:5000/wake?key=$STORED_API_KEY\" -Method Post"

exit 0