import unittest
from pathlib import Path
from paths import data_directory

class DataPathsTests(unittest.TestCase):
    def test_macos_uses_application_support(self):
        self.assertEqual(data_directory('darwin','/Users/test',{}),Path('/Users/test/Library/Application Support/FinancasGeovana'))
    def test_windows_existing_location_is_preserved(self):
        self.assertEqual(data_directory('win32','/home/test',{'LOCALAPPDATA':'/data/local'}),Path('/data/local/FinancasGeovana'))
    def test_linux_existing_location_is_preserved(self):
        self.assertEqual(data_directory('linux','/home/test',{}),Path('/home/test/.local/share/FinancasGeovana'))
