import io
import os
from pathlib import Path
import runpy
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.modules['orca'] = SimpleNamespace(plugin=lambda c:c, base=object,
    pages=SimpleNamespace(PagesPluginCapabilityBase=object))
import kobra_lan as p
from install import install

raw = bytearray(480*272*4)
raw[479*4:480*4] = bytes([2,3,4,255])
bmp = p.bmp(raw)
assert struct.unpack_from('<ii',bmp,18)==(272,480)
assert bmp[54+479*816:57+479*816] == bytes([2,3,4])
for name in ('../x.gcode','x;reboot.gcode','job.gcode.part'):
    try: p.upload(name)
    except ValueError: pass
    else: raise AssertionError(name)

root = Path(__file__).resolve().parent
with TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    support = tmp/'support'
    target = install(root,support,tmp/'plugins')
    assert (target/'kobra_lan.py').read_bytes() == (root/'kobra_lan.py').read_bytes()
    assert (support/'kobra_touch2.elf').read_bytes().startswith(b'\x7fELF')
    assert (support/'exports').is_dir()
    sshdir = tmp/'.config/orca-kobra-lan'; sshdir.mkdir(parents=True)
    (sshdir/'address').write_text('192.168.100.123\n')
    for command,expected in [
        ('reboot',None), ('/tmp/chuck_orca_kobra_touch 1 2; reboot',None),
        ('set -e; /tmp/chuck_orca_kobra_touch; dd if=/dev/fb0 bs=1920 count=544 2>/dev/null',0),
    ]:
        fake_input = SimpleNamespace(buffer=io.BytesIO(('"'+command+'"\n').encode()))
        with patch.object(sys,'stdin',fake_input), patch.object(Path,'home',return_value=tmp), \
             patch.object(subprocess,'run',return_value=SimpleNamespace(returncode=0)) as ssh:
            try: runpy.run_path(str(root/'transport.py'))
            except SystemExit as exc:
                if expected is None: assert exc.code=='Command not allowed' and not ssh.called
                else:
                    assert exc.code==0
                    argv=ssh.call_args.args[0]
                    assert 'root@192.168.100.123' in argv
                    assert '-oStrictHostKeyChecking=yes' in argv and '-oBatchMode=yes' in argv
            else: raise AssertionError(command)
print('Install, screen orientation, filename validation, and pinned SSH command policy passed.')
