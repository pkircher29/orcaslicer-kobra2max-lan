"""Fixed WSL entry point for Orca's exact-command permission grant."""
import json
import re
import subprocess
import sys
import hashlib
import ipaddress
from pathlib import Path

HELPER = '/tmp/chuck_orca_kobra_touch'
D = r'[0-9a-f]{64}'
STAGE = r'/mnt/UDISK/\.orca-[0-9a-f]{32}\.part'
TARGET = r'/mnt/UDISK/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\.gcode'
line = sys.stdin.buffer.readline(2048)
command = json.loads(line)
if not isinstance(command, str):
    raise SystemExit('Invalid request')
h = re.escape(HELPER)
prefixes = [
    rf'test -x {h} && echo "{D}  {h}" \| sha256sum -c - >/dev/null',
    rf'set -euC; umask 077; cat > {h}; echo "{D}  {h}" \| sha256sum -c -; chmod 700 {h}',
    rf'set -e; {h}; dd if=/dev/fb0 bs=1920 count=544 2>/dev/null',
    rf'{h} [0-9]{{1,4}} [0-9]{{1,4}}',
    rf'set -euC; trap "rm -f (?P<stage>{STAGE})" EXIT; cat > (?P=stage); echo "(?P<sha>{D})  (?P=stage)" \| sha256sum -c -; ln (?P=stage) (?P<target>{TARGET}); echo "(?P=sha)  (?P=target)" \| sha256sum -c -',
]
if not any(re.fullmatch(p,command) for p in prefixes):
    raise SystemExit('Command not allowed')
root = Path.home() / '.config' / 'orca-kobra-lan'
address = ipaddress.IPv4Address((root / 'address').read_text().strip())
if not any(address in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
    raise SystemExit('Configure a private LAN IPv4 address')
payload = sys.stdin.buffer.read(64*1024*1024+1)
if len(payload)>64*1024*1024:
    raise SystemExit('Payload too large')
if command.startswith('set -euC; umask'):
    helper = Path(__file__).with_name('kobra_touch2.elf').read_bytes()
    if payload != helper or hashlib.sha256(helper).hexdigest() not in command:
        raise SystemExit('Unexpected touchscreen helper')
elif not command.startswith('set -euC; trap') and payload:
    raise SystemExit('Unexpected payload')
raise SystemExit(subprocess.run(['/usr/bin/ssh','-T','-F','/dev/null','-oBatchMode=yes',
    '-oStrictHostKeyChecking=yes','-oIdentitiesOnly=yes','-oConnectTimeout=5',
    '-oUserKnownHostsFile='+str(root/'known_hosts'),'-i',str(root/'id_ed25519'),
    'root@'+str(address),command],input=payload,timeout=40).returncode)
