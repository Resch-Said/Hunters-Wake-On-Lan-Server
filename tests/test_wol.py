import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import asyncio

# Add the parent directory to the Python path to import server.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestWakeOnLAN(unittest.TestCase):
    def setUp(self):
        """Setup für die Tests"""
        # Setze Test-Umgebungsvariablen
        os.environ['MAX_TRIES'] = '6'  # Reduziere für schnellere Tests
        os.environ['CHECK_INTERVAL'] = '1'  # 1 Sekunde Intervall für Tests
        
        # Importiere die Konstanten nach dem Setzen der Umgebungsvariablen
        from server import MAX_TRIES, CHECK_INTERVAL
        self.max_tries = MAX_TRIES
        self.check_interval = CHECK_INTERVAL

    @patch('server.send_magic_packet')
    @patch('server.ping')
    async def test_wake_computer_slow_boot(self, mock_ping, mock_send_magic_packet):
        """Test waking up a computer with slow boot time"""
        from server import wake
        
        # Simuliere einen langsam bootenden Computer:
        # - Erste 3 Pings: Computer ist offline
        # - Dann 2 Pings: Computer antwortet nicht zuverlässig (Bootphase)
        # - Danach: Computer ist online
        mock_ping.side_effect = [False, False, False, False, True, True]
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_message = AsyncMock()
        mock_update.message = mock_message
        mock_update.effective_chat = MagicMock()
        mock_update.effective_chat.id = 12345
        mock_bot = AsyncMock()
        mock_context.bot = mock_bot
        
        # Set up test environment
        mock_update.effective_user.id = 12345
        os.environ['ALLOWED_USERS'] = '12345'
        mock_context.args = ['test_pc']
        
        # Mock the computers file content
        with patch('server.load_computers') as mock_load:
            mock_load.return_value = {
                'test_pc': {
                    'mac': '00:11:22:33:44:55',
                    'ip': '192.168.1.100'
                }
            }
            
            # Test wake command
            await wake(mock_update, mock_context)
            
            # Warte auf die Status-Checks (5 Intervalle)
            await asyncio.sleep(self.check_interval * 5)
            
            # Überprüfe die Sequenz der Ereignisse
            assert mock_ping.call_count >= 5, "Sollte mehrmals pingen während des Bootvorgangs"
            assert mock_send_magic_packet.call_count >= 2, "Sollte mehrere Wake-Pakete senden"
            
            # Überprüfe die Benachrichtigungen
            status_messages = [call.args[1]['text'] for call in mock_bot.send_message.call_args_list]
            assert any("Wake-on-LAN Paket wurde an 'test_pc' gesendet" in msg for msg in status_messages), "Initiales Wake-Paket nicht gesendet"
            assert any("ist jetzt online" in msg for msg in status_messages), "Erfolgreiche Online-Meldung nicht gesendet"

    @patch('server.send_magic_packet')
    @patch('server.ping')
    async def test_wake_computer_never_wakes(self, mock_ping, mock_send_magic_packet):
        """Test eines Computers, der nicht aufwacht"""
        from server import wake
        
        # Computer bleibt offline
        mock_ping.return_value = False
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_message = AsyncMock()
        mock_update.message = mock_message
        mock_update.effective_chat = MagicMock()
        mock_update.effective_chat.id = 12345
        mock_bot = AsyncMock()
        mock_context.bot = mock_bot
        
        # Set up test environment
        mock_update.effective_user.id = 12345
        os.environ['ALLOWED_USERS'] = '12345'
        mock_context.args = ['test_pc']
        
        # Mock the computers file content
        with patch('server.load_computers') as mock_load:
            mock_load.return_value = {
                'test_pc': {
                    'mac': '00:11:22:33:44:55',
                    'ip': '192.168.1.100'
                }
            }
            
            # Test wake command
            await wake(mock_update, mock_context)
            
            # Warte auf alle Versuche
            await asyncio.sleep(self.check_interval * (self.max_tries + 1))
            
            # Überprüfe die Anzahl der Versuche
            assert mock_ping.call_count >= self.max_tries, f"Sollte mindestens {self.max_tries} Mal pingen"
            assert mock_send_magic_packet.call_count >= self.max_tries // 3, "Sollte mehrere Wake-Pakete senden"
            
            # Überprüfe die Fehlermeldung
            status_messages = [call.args[1]['text'] for call in mock_bot.send_message.call_args_list]
            assert any(f"nicht aufgeweckt werden nach {self.max_tries} Versuchen" in msg for msg in status_messages), "Fehlermeldung nicht gesendet"

    @patch('server.send_magic_packet')
    @patch('server.ping')
    async def test_wake_all_computers_different_boot_times(self, mock_ping, mock_send_magic_packet):
        """Test waking up multiple computers with different boot times"""
        from server import wakeall
        
        # Simuliere verschiedene Boot-Zeiten für verschiedene Computer
        ping_responses = {
            '192.168.1.100': [False, False, True, True],  # Schneller Boot
            '192.168.1.101': [False, False, False, False, True]  # Langsamer Boot
        }
        
        def mock_ping_side_effect(ip):
            if ip in ping_responses and ping_responses[ip]:
                return ping_responses[ip].pop(0)
            return False
        
        mock_ping.side_effect = mock_ping_side_effect
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_message = AsyncMock()
        mock_update.message = mock_message
        mock_update.effective_chat = MagicMock()
        mock_update.effective_chat.id = 12345
        mock_bot = AsyncMock()
        mock_context.bot = mock_bot
        
        # Set up test environment
        mock_update.effective_user.id = 12345
        os.environ['ALLOWED_USERS'] = '12345'
        
        # Mock the computers file content
        test_computers = {
            'pc1': {
                'mac': '00:11:22:33:44:55',
                'ip': '192.168.1.100'
            },
            'pc2': {
                'mac': 'AA:BB:CC:DD:EE:FF',
                'ip': '192.168.1.101'
            }
        }
        
        with patch('server.load_computers') as mock_load:
            mock_load.return_value = test_computers
            
            # Test wakeall command
            await wakeall(mock_update, mock_context)
            
            # Warte auf die Status-Checks
            await asyncio.sleep(self.check_interval * 5)
            
            # Überprüfe die Benachrichtigungen für beide Computer
            status_messages = [call.args[1]['text'] for call in mock_bot.send_message.call_args_list]
            assert any("pc1" in msg and "online" in msg for msg in status_messages), "PC1 Online-Status nicht gemeldet"
            assert any("pc2" in msg and "online" in msg for msg in status_messages), "PC2 Online-Status nicht gemeldet"

def run_async_tests():
    """Helper function to run async tests"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        *(test() for test in [
            TestWakeOnLAN('test_wake_computer_slow_boot').test_wake_computer_slow_boot,
            TestWakeOnLAN('test_wake_computer_never_wakes').test_wake_computer_never_wakes,
            TestWakeOnLAN('test_wake_all_computers_different_boot_times').test_wake_all_computers_different_boot_times
        ])
    ))

if __name__ == '__main__':
    print("Running async tests:")
    run_async_tests() 