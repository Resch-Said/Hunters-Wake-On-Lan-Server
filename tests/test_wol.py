import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import asyncio

# Add the parent directory to the Python path to import server.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestWakeOnLAN(unittest.TestCase):
    @patch('server.send_magic_packet')
    @patch('server.ping')
    async def test_wake_computer(self, mock_ping, mock_send_magic_packet):
        """Test waking up a computer"""
        from server import wake
        
        # Mock successful ping response
        mock_ping.return_value = True
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        
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
            
            # Verify magic packet was sent
            mock_send_magic_packet.assert_called_once_with('00:11:22:33:44:55')
            
            # Verify message was sent to user
            mock_update.message.reply_text.assert_called_with(
                "📨 Wake-on-LAN Paket wurde an 'test_pc' gesendet!"
            )
            
    @patch('server.send_magic_packet')
    @patch('server.ping')
    async def test_wake_all_computers(self, mock_ping, mock_send_magic_packet):
        """Test waking up all computers"""
        from server import wakeall
        
        # Mock successful ping response
        mock_ping.return_value = True
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        
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
            
            # Verify magic packets were sent to all computers
            self.assertEqual(mock_send_magic_packet.call_count, 2)
            mock_send_magic_packet.assert_any_call('00:11:22:33:44:55')
            mock_send_magic_packet.assert_any_call('AA:BB:CC:DD:EE:FF')
            
            # Verify success message was sent
            mock_update.message.reply_text.assert_called()
            
    @patch('server.send_magic_packet')
    async def test_wake_error_handling(self, mock_send_magic_packet):
        """Test error handling when waking computers"""
        from server import wake
        
        # Mock an error when sending magic packet
        mock_send_magic_packet.side_effect = Exception("Network error")
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        
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
            
            # Test wake command with error
            await wake(mock_update, mock_context)
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called_with(
                "❌ Fehler beim Senden: Network error"
            )

def run_async_tests():
    """Helper function to run async tests"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        *(test() for test in [
            TestWakeOnLAN('test_wake_computer').test_wake_computer,
            TestWakeOnLAN('test_wake_all_computers').test_wake_all_computers,
            TestWakeOnLAN('test_wake_error_handling').test_wake_error_handling
        ])
    ))

if __name__ == '__main__':
    print("Running async tests:")
    run_async_tests() 