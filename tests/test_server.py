import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
import sys
import asyncio

# Add the parent directory to the Python path to import server.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    is_valid_mac,
    is_valid_ip,
    load_computers,
    save_computers,
    check_permission,
    ensure_env_defaults
)

class TestWakeOnLANServer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.computers_file = os.path.join(self.test_dir, "test_computers.json")
        self.env_file = os.path.join(self.test_dir, ".env")
        
        # Set environment variable for testing
        os.environ["COMPUTERS_FILE"] = self.computers_file
        
    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.computers_file):
            os.remove(self.computers_file)
        if os.path.exists(self.env_file):
            os.remove(self.env_file)
        os.rmdir(self.test_dir)
        
    def test_valid_mac_address(self):
        """Test MAC address validation"""
        valid_macs = [
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "00-11-22-33-44-55"
        ]
        invalid_macs = [
            "00:11:22:33:44",  # Too short
            "00:11:22:33:44:55:66",  # Too long
            "00:11:22:33:44:GG",  # Invalid characters
            "0011.2233.4455"  # Wrong format
        ]
        
        for mac in valid_macs:
            self.assertTrue(is_valid_mac(mac), f"MAC address {mac} should be valid")
            
        for mac in invalid_macs:
            self.assertFalse(is_valid_mac(mac), f"MAC address {mac} should be invalid")
            
    def test_valid_ip_address(self):
        """Test IP address validation"""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255"
        ]
        invalid_ips = [
            "256.1.2.3",  # Invalid octet
            "1.2.3",  # Too few octets
            "1.2.3.4.5",  # Too many octets
            "192.168.1",  # Incomplete
            "abc.def.ghi.jkl"  # Invalid format
        ]
        
        for ip in valid_ips:
            self.assertTrue(is_valid_ip(ip), f"IP address {ip} should be valid")
            
        for ip in invalid_ips:
            self.assertFalse(is_valid_ip(ip), f"IP address {ip} should be invalid")
            
    def test_load_save_computers(self):
        """Test loading and saving computer data"""
        test_computers = {
            "test_pc": {
                "mac": "00:11:22:33:44:55",
                "ip": "192.168.1.100"
            }
        }
        
        # Test saving computers
        save_computers(test_computers, self.computers_file)
        self.assertTrue(os.path.exists(self.computers_file))
        
        # Test loading computers
        loaded_computers = load_computers(self.computers_file)
        self.assertEqual(loaded_computers, test_computers)
        
        # Test loading with non-existent file
        os.remove(self.computers_file)
        empty_computers = load_computers(self.computers_file)
        self.assertEqual(empty_computers, {})
        
    def test_ensure_env_defaults(self):
        """Test environment defaults are set correctly"""
        # Create empty .env file
        with open(self.env_file, 'w') as f:
            f.write("TELEGRAM_TOKEN=test_token\n")
            
        # Test ensuring defaults
        ensure_env_defaults(self.env_file)
        
        # Read the file and check if defaults were added
        with open(self.env_file, 'r') as f:
            content = f.read()
            
        expected_defaults = [
            'CONNECT_TIMEOUT=30.0',
            'READ_TIMEOUT=30.0',
            'WRITE_TIMEOUT=30.0',
            'POOL_TIMEOUT=30.0',
            'MAX_TRIES=30',
            'CHECK_INTERVAL=10',
            'COMPUTERS_FILE=computers.json'
        ]
        
        for default in expected_defaults:
            self.assertIn(default, content)
            
    @patch('server.Update')
    async def test_check_permission(self, mock_update):
        """Test permission checking"""
        # Set up mock user
        mock_user = MagicMock()
        mock_user.id = 12345
        mock_update.effective_user = mock_user
        
        # Test with allowed user
        os.environ['ALLOWED_USERS'] = '12345,67890'
        self.assertTrue(await check_permission(mock_update))
        
        # Test with unauthorized user
        mock_user.id = 99999
        self.assertFalse(await check_permission(mock_update))
        
        # Test with no user
        mock_update.effective_user = None
        self.assertFalse(await check_permission(mock_update))

def run_async_tests():
    """Helper function to run async tests"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        *(test() for test in [
            TestWakeOnLANServer('test_check_permission').test_check_permission
        ])
    ))

if __name__ == '__main__':
    # Run synchronous tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWakeOnLANServer)
    # Remove async test to run it separately
    suite._tests = [test for test in suite._tests if not test._testMethodName.startswith('test_check_permission')]
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Run async tests
    print("\nRunning async tests:")
    run_async_tests() 