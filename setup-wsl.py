#!/usr/bin/env python3
"""Run interactively inside Ubuntu-24.04 WSL, not in Orca."""
import ipaddress
import os
from pathlib import Path
import subprocess


def main():
    addr = ipaddress.IPv4Address(input('Printer LAN IPv4: ').strip())
    if not any(addr in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
        raise SystemExit('Use a private LAN address.')
    pin = input('Verified SSH ED25519 fingerprint (SHA256:…): ').strip()
    host = str(addr)
    scan = subprocess.run(['/usr/bin/ssh-keyscan','-T','5','-t','ed25519',host],capture_output=True,check=True).stdout
    keys = [line for line in scan.splitlines() if line.startswith((host + ' ssh-ed25519 ').encode())]
    if len(keys) != 1:
        raise SystemExit('Could not retrieve a unique SSH host key.')
    key = keys[0] + b'\n'
    fingerprint = subprocess.run(['/usr/bin/ssh-keygen','-lf','-'],input=key,capture_output=True,check=True).stdout.decode().split()[1]
    if not pin.startswith('SHA256:') or pin != fingerprint:
        raise SystemExit('Host fingerprint mismatch. No password was sent.')
    os.umask(0o077)
    folder = Path.home() / '.config' / 'orca-kobra-lan'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (folder / 'address').exists() and (folder / 'address').read_text().strip() != host:
        raise SystemExit('This install supports one printer. Back up or move the old local config before changing hosts.')
    known = folder / 'known_hosts'
    if known.exists() and known.read_bytes() != key:
        raise SystemExit('Existing host pin differs. Verify identity and back up the old config before changing it.')
    if not known.exists(): known.write_bytes(key)
    identity = folder / 'id_ed25519'
    if not identity.exists():
        subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(identity)],check=True)
    opts = ['-F','/dev/null','-oStrictHostKeyChecking=yes','-oUserKnownHostsFile='+str(known),'-oIdentitiesOnly=yes']
    dest = 'root@'+host
    batch = ['/usr/bin/ssh',*opts,'-oBatchMode=yes','-i',str(identity),dest,'test -c /dev/fb0 && test -c /dev/input/event0']
    if subprocess.run(batch,capture_output=True).returncode:
        print('Enter the printer’s root password in the SSH prompt. It is not saved.')
        subprocess.run(['/usr/bin/ssh-copy-id',*opts,'-i',str(identity)+'.pub',dest],check=True)
        subprocess.run(batch,check=True)
    (folder / 'address').write_text(host+'\n')
    print('Pinned SSH, key login, and device nodes verified. No print started.')


if __name__ == '__main__':
    main()
