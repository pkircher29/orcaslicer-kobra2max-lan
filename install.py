"""Install the plugin files on Windows. Does not touch credentials or printer state."""
from pathlib import Path
import os
import shutil


def install(source, support, plugins):
    (support / 'exports').mkdir(parents=True, exist_ok=True)
    target = plugins / 'kobra2max_local'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('transport.py','kobra_touch2.elf'):
        shutil.copy2(source / name, support / name)
    shutil.copy2(source / 'kobra_lan.py', target / 'kobra_lan.py')
    return target


if __name__ == '__main__':
    print('Installed:', install(Path(__file__).resolve().parent, Path.home() / 'Orca-Kobra-LAN',
                                Path(os.environ['APPDATA']) / 'OrcaSlicer' / 'orca_plugins'))
