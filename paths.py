"""Diretórios de dados por sistema, independentes do local do executável."""
import os
import sys
from pathlib import Path


def data_directory(platform=None, home=None, environ=None):
    platform=platform or sys.platform
    home=Path(home) if home is not None else Path.home()
    environ=os.environ if environ is None else environ
    if platform=='win32':
        return Path(environ.get('LOCALAPPDATA',home/'AppData'/'Local'))/'FinancasGeovana'
    if platform=='darwin':
        return home/'Library'/'Application Support'/'FinancasGeovana'
    return Path(environ.get('XDG_DATA_HOME',home/'.local'/'share'))/'FinancasGeovana'
