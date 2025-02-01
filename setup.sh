#!/bin/bash

# Fehlerbehandlung aktivieren
set -e  # Skript beenden bei Fehlern
trap 'echo "Ein Fehler ist aufgetreten. Installation wird abgebrochen."; exit 1' ERR

# Farbige Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Aktuellen Benutzer ermitteln
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" = "root" ]; then
    echo -e "${RED}Das Skript sollte nicht als root ausgeführt werden!${NC}"
    echo -e "Bitte führe das Skript als normaler Benutzer aus (sudo wird bei Bedarf angefordert)."
    exit 1
fi

REPO_URL="https://github.com/Resch-Said/Hunters-Wake-On-Lan-Server.git"
INSTALL_DIR="/home/$CURRENT_USER/Hunters-Wake-On-Lan-Server"
SERVICE_NAME="wol-server"

# Funktion zum Entfernen des existierenden Services
cleanup_service() {
    echo -e "${YELLOW}Prüfe auf existierenden Service...${NC}"
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${YELLOW}Stoppe existierenden Service...${NC}"
        sudo systemctl stop $SERVICE_NAME
    fi
    
    if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
        echo -e "${YELLOW}Deaktiviere existierenden Service...${NC}"
        sudo systemctl disable $SERVICE_NAME
    fi
    
    if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo -e "${YELLOW}Entferne existierende Service-Datei...${NC}"
        sudo rm "/etc/systemd/system/$SERVICE_NAME.service"
        sudo systemctl daemon-reload
    fi
    
    echo -e "${GREEN}Service-Bereinigung abgeschlossen.${NC}"
}

# Funktion zur Überprüfung der Abhängigkeiten
check_dependencies() {
    echo -e "${YELLOW}Überprüfe Systemvoraussetzungen...${NC}"
    
    # Befehle, die direkt geprüft werden können
    COMMANDS=("git" "python3" "pip3" "ping")
    # Pakete, die über dpkg geprüft werden müssen
    PACKAGES=("python3-venv")
    
    MISSING_DEPS=()
    
    # Prüfe Befehle
    for cmd in "${COMMANDS[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            MISSING_DEPS+=($cmd)
        fi
    done
    
    # Prüfe Pakete
    for pkg in "${PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$pkg "; then
            MISSING_DEPS+=($pkg)
        fi
    done
    
    if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
        echo -e "${RED}Fehlende Abhängigkeiten: ${MISSING_DEPS[*]}${NC}"
        echo "Installiere fehlende Pakete..."
        sudo apt update
        sudo apt install -y git python3-venv python3-pip iputils-ping
    else
        echo -e "${GREEN}Alle Abhängigkeiten sind erfüllt.${NC}"
    fi
}

# Funktion zum Testen der Netzwerkfunktionalität
test_network() {
    echo -e "${YELLOW}Teste Netzwerkfunktionalität...${NC}"
    
    # Teste Internetverbindung
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        echo -e "${RED}Keine Internetverbindung verfügbar!${NC}"
        return 1
    fi
    
    # Teste lokales Netzwerk
    if ! ping -c 1 $(ip route | grep default | awk '{print $3}') &> /dev/null; then
        echo -e "${RED}Lokales Netzwerk nicht erreichbar!${NC}"
        return 1
    fi
    
    # Teste Wake-on-LAN Port (UDP 9)
    if ! nc -zu localhost 9 &> /dev/null; then
        echo -e "${YELLOW}Warnung: Wake-on-LAN Port (UDP 9) scheint blockiert zu sein.${NC}"
    fi
    
    echo -e "${GREEN}Netzwerktest erfolgreich.${NC}"
    return 0
}

# Hauptinstallation
main() {
    echo -e "${YELLOW}Starte Installation...${NC}"
    
    # Überprüfe Abhängigkeiten
    check_dependencies
    
    # Teste Netzwerk
    if ! test_network; then
        echo -e "${RED}Netzwerktest fehlgeschlagen. Installation wird abgebrochen.${NC}"
        exit 1
    fi
    
    # Entferne existierenden Service
    cleanup_service

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
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
Environment=VIRTUAL_ENV=$INSTALL_DIR/venv
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR
Environment=LC_ALL=C.UTF-8
Environment=LANG=C.UTF-8

ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/server.py
User=$CURRENT_USER
Group=$CURRENT_USER
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/$SERVICE_NAME.log
StandardError=append:/var/log/$SERVICE_NAME.error.log

[Install]
WantedBy=multi-user.target
EOF

    # Erstelle und setze Berechtigungen für Log-Dateien
    sudo touch /var/log/$SERVICE_NAME.log /var/log/$SERVICE_NAME.error.log
    sudo chown $CURRENT_USER:$CURRENT_USER /var/log/$SERVICE_NAME.log /var/log/$SERVICE_NAME.error.log
    sudo chmod 644 /var/log/$SERVICE_NAME.log /var/log/$SERVICE_NAME.error.log

    # Service aktivieren
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    sudo systemctl start $SERVICE_NAME

    # Warte kurz und prüfe den Status
    sleep 3
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${RED}Service konnte nicht gestartet werden. Überprüfe die Logs:${NC}"
        echo -e "${YELLOW}Service Log:${NC}"
        tail -n 20 /var/log/$SERVICE_NAME.log
        echo -e "\n${YELLOW}Error Log:${NC}"
        tail -n 20 /var/log/$SERVICE_NAME.error.log
        echo -e "\n${YELLOW}Systemd Status:${NC}"
        sudo systemctl status $SERVICE_NAME --no-pager
    else
        echo -e "${GREEN}Service erfolgreich gestartet!${NC}"
    fi

    # Status anzeigen
    echo -e "\n\033[1mInstallation abgeschlossen! Service-Status:\033[0m"
    sudo systemctl status $SERVICE_NAME --no-pager | head -n 10

    # Anzeige der Konfiguration am Ende
    echo -e "\n${GREEN}Installation erfolgreich abgeschlossen!${NC}"
    echo -e "\n\033[1mWichtige Informationen:\033[0m"
    echo -e "🤖 Bot ist eingerichtet! Suche deinen Bot auf Telegram und sende /start"
    echo -e "👤 Erlaubte User IDs: $ALLOWED_USERS"
    echo -e "\n💡 Nutze /add [name] [mac] [ip] um Computer hinzuzufügen"
    echo -e "   Beispiel: /add pc1 00:11:22:33:44:55 192.168.1.100"
}

# Führe Hauptfunktion aus
main

exit 0