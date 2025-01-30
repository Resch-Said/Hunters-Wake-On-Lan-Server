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

def get_public_ipv6():
    """Ermittelt die öffentliche IPv6-Adresse"""
    try:
        import urllib.request
        return urllib.request.urlopen('https://api6.ipify.org').read().decode('utf8')
    except:
        return "::1"  # Fallback auf localhost

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
    print(f"\n\033[1mServer-Konfiguration:\033[0m")
    print(f"API Key: {API_KEY}")
    print(f"Target MAC: {TARGET_MAC}")
    
    public_ipv6 = get_public_ipv6()
    print(f"Server startet auf http://[::]:{PORT}")
    print(f"Öffentliche IPv6: [{public_ipv6}]")
    
    print(f"\n\033[1mBeispiel-Befehle zum Aufwecken:\033[0m")
    print("\nLinux/Mac:")
    print(f"curl -X POST 'http://[{public_ipv6}]:5000/wake?key={API_KEY}'")
    print("\nWindows PowerShell:")
    print(f"Invoke-WebRequest -Uri \"http://[{public_ipv6}]:5000/wake?key={API_KEY}\" -Method Post")
    
    app.run(host='::', port=PORT)