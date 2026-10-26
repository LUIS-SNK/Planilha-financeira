import os
import subprocess
import unittest
from unittest.mock import patch
from scripts import build_macos

class MacDistributionTests(unittest.TestCase):
    def test_no_credentials_builds_but_does_not_distribute(self):
        with patch.dict(os.environ,{},clear=True), patch.object(build_macos.sys,'platform','darwin'), patch.object(build_macos,'build') as build, patch.object(build_macos,'output') as output:
            build_macos.main()
            build.assert_called_once_with()
            output.assert_called_once_with(False)
    def test_partial_credentials_block_distribution(self):
        with patch.dict(os.environ,{'APPLE_ID':'test@example.invalid'},clear=True), patch.object(build_macos.sys,'platform','darwin'), patch.object(build_macos,'build') as build:
            with self.assertRaisesRegex(RuntimeError,'Configuração Apple incompleta'): build_macos.main()
            build.assert_not_called()
    def test_subprocess_failure_does_not_expose_arguments(self):
        with patch.object(build_macos.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaises(RuntimeError) as raised: build_macos.run('security','-p','sensitive-placeholder')
            self.assertNotIn('sensitive-placeholder',str(raised.exception))
