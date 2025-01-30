from flask import Flask, abort, request
from wakeonlan import send_magic_packet
from dotenv import load_dotenv
import socket
import os

# Lade Umgebungsvariablen
load_dotenv()

app = Flask(__name__)

# Konfiguration aus .env
API_KEY = os.getenv('API_KEY')
TARGET_MAC = os.getenv('TARGET_MAC')
PORT = 5000

if not API_KEY or not TARGET_MAC:
    print("Fehler: API_KEY oder TARGET_MAC nicht in .env Datei gefunden!")
    print("Bitte stelle sicher, dass die .env Datei existiert und folgende Einträge enthält:")
    print("API_KEY=dein_api_key")
    print("TARGET_MAC=deine_mac_adresse")
    exit(1)

def get_ipv6_address():
    """Ermittelt die globale IPv6-Adresse"""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
            s.connect(("2001:4860:4860::8888", 80))  # Google DNS
            return s.getsockname()[0]
    except:
        return None

@app.route('/wake', methods=['POST'])
def wake():
    """Wake-on-LAN Endpoint"""
    provided_key = request.args.get('key')
    
    if provided_key != API_KEY:
        abort(401)
    
    try:
        send_magic_packet(TARGET_MAC)
        return "Magic Packet gesendet!", 200
    except Exception as e:
        return f"Fehler: {str(e)}", 500

if __name__ == '__main__':
    print(f"API Key: {API_KEY}")
    print(f"Target MAC: {TARGET_MAC}")
    print(f"Server startet auf http://[::]:{PORT}")
    app.run(host='::', port=PORT)