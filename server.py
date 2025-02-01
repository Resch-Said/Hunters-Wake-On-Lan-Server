from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
from wakeonlan import send_magic_packet
from dotenv import load_dotenv
import os
import json
import logging
import re
import asyncio
import platform
import subprocess
from telegram.request import HTTPXRequest
from telegram.error import TimedOut, NetworkError

# Logging konfigurieren
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def ensure_env_defaults(env_path='.env'):
    """Stellt sicher, dass alle Standardwerte in der .env-Datei vorhanden sind"""
    defaults = {
        'CONNECT_TIMEOUT': '30.0',
        'READ_TIMEOUT': '30.0',
        'WRITE_TIMEOUT': '30.0',
        'POOL_TIMEOUT': '30.0',
        'MAX_TRIES': '30',
        'CHECK_INTERVAL': '10',
        'COMPUTERS_FILE': 'computers.json'
    }
    
    # Existierende Werte laden
    existing_values = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    existing_values[key] = value

    # Fehlende Werte hinzufügen
    needs_update = False
    for key, value in defaults.items():
        if key not in existing_values:
            existing_values[key] = value
            needs_update = True
            logger.info(f"Füge Standardwert hinzu: {key}={value}")

    # Datei aktualisieren, wenn Änderungen vorgenommen wurden
    if needs_update:
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in existing_values.items():
                f.write(f"{key}={value}\n")
        logger.info("Standardwerte wurden zur .env-Datei hinzugefügt")

# Standardwerte sicherstellen
ensure_env_defaults()

# Umgebungsvariablen laden
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ALLOWED_USERS = [int(id) for id in os.getenv('ALLOWED_USERS', '').split(',') if id]
COMPUTERS_FILE = os.getenv('COMPUTERS_FILE', 'computers.json')
MAX_TRIES = int(os.getenv('MAX_TRIES', '30'))  # Anzahl der Versuche für Computer-Status-Check
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))  # Wartezeit zwischen Status-Checks in Sekunden
# Timeout-Einstellungen
CONNECT_TIMEOUT = float(os.getenv('CONNECT_TIMEOUT', '30.0'))  # Verbindungs-Timeout in Sekunden
READ_TIMEOUT = float(os.getenv('READ_TIMEOUT', '30.0'))  # Lese-Timeout in Sekunden
WRITE_TIMEOUT = float(os.getenv('WRITE_TIMEOUT', '30.0'))  # Schreib-Timeout in Sekunden
POOL_TIMEOUT = float(os.getenv('POOL_TIMEOUT', '30.0'))  # Pool-Timeout in Sekunden

# Debug-Ausgabe der Konfiguration
logger.debug(f"Geladene Konfiguration:")
logger.debug(f"Token verfügbar: {'Ja' if TELEGRAM_TOKEN else 'Nein'}")
logger.debug(f"Erlaubte Benutzer: {ALLOWED_USERS}")

def save_computers(computers, file_path=None):
    """Speichert die Computer"""
    if file_path is None:
        file_path = os.getenv('COMPUTERS_FILE', 'computers.json')
    with open(file_path, 'w') as f:
        json.dump(computers, f, indent=2)

def load_computers(file_path=None):
    """Lädt die gespeicherten Computer mit verbesserter Fehlerbehandlung"""
    if file_path is None:
        file_path = os.getenv('COMPUTERS_FILE', 'computers.json')
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Computers file {file_path} not found. Creating empty file.")
            save_computers({}, file_path)
            return {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.error("Invalid data format in computers file. Expected dictionary.")
                    return {}
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
                # Erstelle Backup der fehlerhaften Datei
                backup_file = f"{file_path}.backup"
                try:
                    os.rename(file_path, backup_file)
                    logger.info(f"Created backup of corrupted file as {backup_file}")
                except OSError as e:
                    logger.error(f"Failed to create backup file: {str(e)}")
                return {}
    except OSError as e:
        logger.error(f"Error accessing file {file_path}: {str(e)}")
        return {}

def is_valid_mac(mac):
    """Überprüft ob eine MAC-Adresse gültig ist"""
    pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(pattern.match(mac))

def is_valid_ip(ip):
    """Überprüft ob eine IP-Adresse gültig ist"""
    pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    if not pattern.match(ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split('.'))

async def ping(ip):
    """Pingt eine IP-Adresse an"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except:
        return False

async def check_computer_status(context: ContextTypes.DEFAULT_TYPE, chat_id: int, name: str, ip: str):
    """Überprüft den Status eines Computers nach dem Aufwecken"""
    tries = 0
    max_tries = 30  # 5 Minuten (10 Sekunden * 30)
    
    while tries < max_tries:
        if await ping(ip):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Computer '{name}' ist jetzt online!"
            )
            return
        await asyncio.sleep(10)  # 10 Sekunden warten
        tries += 1
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⚠️ Computer '{name}' konnte nicht aufgeweckt werden!"
    )

async def check_permission(update: Update):
    """Prüft ob der Benutzer berechtigt ist"""
    if not update or not update.effective_user:
        return False
        
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        logger.warning(f"Unbefugter Zugriffsversuch von User ID: {user_id}")
        if update.message:
            await update.message.reply_text("❌ Sorry, du bist nicht berechtigt diesen Bot zu nutzen.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sendet eine Begrüßungsnachricht"""
    logger.debug("Start-Befehl empfangen")
    if not update or not update.message:
        logger.error("Update oder Message-Objekt ist None")
        return
        
    if not await check_permission(update):
        logger.warning("Berechtigungsprüfung fehlgeschlagen")
        return
    
    logger.debug("Sende Begrüßungsnachricht")
    await update.message.reply_text(
        "🖥️ Wake-on-LAN Bot\n\n"
        "Verfügbare Befehle:\n"
        "/wake [name] - Startet einen Computer\n"
        "/wakeall - Startet alle Computer\n"
        "/list - Zeigt alle Computer\n"
        "/add [name] [mac] [ip] - Fügt einen Computer hinzu\n"
        "/remove [name] - Entfernt einen Computer\n"
        "/status - Zeigt den Bot-Status"
    )

async def add_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fügt einen neuen Computer hinzu"""
    if not await check_permission(update): return
    
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("❌ Bitte nutze: /add [name] [mac] [ip]")
        return
    
    name, mac, ip = args
    if not is_valid_mac(mac):
        await update.message.reply_text("❌ Ungültige MAC-Adresse! Format: XX:XX:XX:XX:XX:XX")
        return
    
    if not is_valid_ip(ip):
        await update.message.reply_text("❌ Ungültige IP-Adresse! Format: XXX.XXX.XXX.XXX")
        return
    
    computers = load_computers()
    computers[name] = {"mac": mac, "ip": ip}
    save_computers(computers)
    
    await update.message.reply_text(f"✅ Computer '{name}' wurde hinzugefügt!")

async def remove_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entfernt einen Computer"""
    if not await check_permission(update): return
    
    if not context.args:
        await update.message.reply_text("❌ Bitte nutze: /remove [name]")
        return
    
    name = context.args[0]
    computers = load_computers()
    
    if name in computers:
        del computers[name]
        save_computers(computers)
        await update.message.reply_text(f"✅ Computer '{name}' wurde entfernt!")
    else:
        await update.message.reply_text(f"❌ Computer '{name}' nicht gefunden!")

async def list_computers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listet alle Computer auf"""
    if not await check_permission(update): return
    
    computers = load_computers()
    if not computers:
        await update.message.reply_text("Keine Computer gespeichert!")
        return
    
    message = "🖥️ Gespeicherte Computer:\n\n"
    for name, data in computers.items():
        message += f"• {name}: {data['mac']} (IP: {data['ip']})\n"
    
    await update.message.reply_text(message)

async def wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Weckt einen Computer auf"""
    if not await check_permission(update): return
    
    if not context.args:
        await update.message.reply_text("❌ Bitte nutze: /wake [name]")
        return
    
    name = context.args[0]
    computers = load_computers()
    
    if name not in computers:
        await update.message.reply_text(f"❌ Computer '{name}' nicht gefunden!")
        return
    
    try:
        send_magic_packet(computers[name]["mac"])
        await update.message.reply_text(f"📨 Wake-on-LAN Paket wurde an '{name}' gesendet!")
        
        # Starte Status-Überprüfung
        asyncio.create_task(check_computer_status(
            context,
            update.effective_chat.id,
            name,
            computers[name]["ip"]
        ))
        
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Senden: {str(e)}")

async def wakeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Weckt alle Computer auf"""
    if not await check_permission(update): return
    
    computers = load_computers()
    if not computers:
        await update.message.reply_text("❌ Keine Computer gespeichert!")
        return
    
    success = []
    failed = []
    
    for name, data in computers.items():
        try:
            send_magic_packet(data["mac"])
            success.append(name)
            # Starte Status-Überprüfung für jeden Computer
            asyncio.create_task(check_computer_status(
                context,
                update.effective_chat.id,
                name,
                data["ip"]
            ))
        except Exception as e:
            failed.append(name)
    
    # Erstelle Statusnachricht
    message = "📨 Wake-on-LAN Status:\n\n"
    if success:
        message += "✅ Erfolgreich gesendet an:\n"
        message += "\n".join(f"• {name}" for name in success)
        message += "\n\n"
    if failed:
        message += "❌ Fehler beim Senden an:\n"
        message += "\n".join(f"• {name}" for name in failed)
    
    await update.message.reply_text(message)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt den Status des Bots"""
    if not await check_permission(update): return
    
    user_id = update.effective_user.id
    computers = load_computers()
    
    await update.message.reply_text(
        f"🤖 Bot ist aktiv\n"
        f"👤 Deine User ID: {user_id}\n"
        f"💻 Anzahl Computer: {len(computers)}"
    )

def main():
    """Startet den Bot"""
    # Erstelle einen benutzerdefinierten Request-Handler mit angepassten Timeouts
    request = HTTPXRequest(
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=READ_TIMEOUT,
        write_timeout=WRITE_TIMEOUT,
        pool_timeout=POOL_TIMEOUT
    )
    
    # Initialisiere die Anwendung mit dem benutzerdefinierten Request-Handler
    application = Application.builder()\
        .token(TELEGRAM_TOKEN)\
        .request(request)\
        .build()

    # Füge Error Handler hinzu
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Exception while handling an update: {context.error}")
        
        if isinstance(context.error, TimedOut):
            logger.info("Timeout aufgetreten - Versuche es erneut...")
            return
        
        if isinstance(context.error, NetworkError):
            logger.info("Netzwerkfehler aufgetreten - Warte kurz und versuche es erneut...")
            await asyncio.sleep(1)  # Kurze Pause vor erneutem Versuch
            return

        # Für andere Fehler
        logger.error("Ein unerwarteter Fehler ist aufgetreten:", exc_info=context.error)

    application.add_error_handler(error_handler)
    
    # Füge Command Handler hinzu
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_computer))
    application.add_handler(CommandHandler("remove", remove_computer))
    application.add_handler(CommandHandler("list", list_computers))
    application.add_handler(CommandHandler("wake", wake))
    application.add_handler(CommandHandler("wakeall", wakeall))
    application.add_handler(CommandHandler("status", status))
    
    # Starte den Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()