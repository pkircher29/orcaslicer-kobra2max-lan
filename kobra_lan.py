# /// script
# requires-python = ">=3.9"
# dependencies = []
# [tool.orcaslicer.plugin]
# id = "kobra2max_local"
# name = "Kobra 2 Max LAN"
# description = "Upload Orca G-code and operate the Kobra touchscreen over pinned SSH."
# author = "Chuck"
# version = "0.2.0"
# ///
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import threading
import time
import uuid

import orca

ROOT = Path.home() / 'Orca-Kobra-LAN'
EXPORT = ROOT / 'exports'
WSL = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'wsl.exe')
HELPER = '/tmp/chuck_orca_kobra_touch'
PAGE = r'''<!doctype html><meta charset="utf-8"><style>
body{font:16px system-ui;margin:24px;color-scheme:light dark} input,button{font:inherit;margin:4px;padding:6px} img{display:block;margin-top:12px;cursor:crosshair;border:1px solid gray} #status{white-space:pre-wrap}</style>
<h2>Kobra 2 Max LAN</h2><p>Export G-code to <code id="folder"></code>, then browse for the file.</p>
<button id="browse">Browse exports…</button><label>G-code <select id="name" disabled><option value="">No file selected</option></select></label><button id="upload" disabled>Upload</button>
<p>On the live touchscreen: Print → Local → choose the uploaded file → Print.</p>
<label><input id="ready" type="checkbox">I checked that the bed is clear and the printer is ready. Enable one touchscreen tap.</label>
<div><button id="refresh">Refresh screen</button></div><img id="screen" width="272" height="480" hidden alt="Kobra touchscreen"><p id="status" role="status"></p>
<script>
const el=(id)=>document.getElementById(id); let token=null;
function send(m){el('status').textContent='Working…';window.orca.postMessage(m);}
el('refresh').onclick=()=>send({action:'screen'});
el('browse').onclick=()=>send({action:'browse'});
el('name').onchange=()=>{el('upload').disabled=!el('name').value;};
el('upload').onclick=()=>send({action:'upload',name:el('name').value});
el('screen').onclick=(e)=>{if(!el('ready').checked || !token)return;el('ready').checked=false; const t=token;token=null;
const r=e.currentTarget.getBoundingClientRect();send({action:'tap',x:Math.floor(272*(e.clientX-r.left)/r.width),y:Math.floor(480*(e.clientY-r.top)/r.height),token:t});};
window.orca.onMessage((m)=>{if(typeof m==='string')m=JSON.parse(m);el('status').textContent=m.status||'';if(m.folder)el('folder').textContent=m.folder;
if(Array.isArray(m.files)){const s=el('name'), previous=s.value;s.replaceChildren(new Option('Select a file…',''),...m.files.map(n=>new Option(n,n)));s.disabled=!m.files.length;s.value=m.files.includes(previous)?previous:(m.files.length===1?m.files[0]:'');s.onchange();}
if(m.image){el('screen').src=m.image;el('screen').hidden=false;token=m.token;} else {token=null;}});
send({action:'init'});</script>'''


def wsl_path(path):
    p = Path(path).resolve()
    return '/mnt/' + p.drive[0].lower() + p.as_posix()[2:]


def transport_argv():
    return [WSL, '-d', 'Ubuntu-24.04', '-e', '/usr/bin/python3', wsl_path(ROOT / 'transport.py')]


def ssh(command, payload=None):
    request, response = ROOT / 'ssh-request.bin', ROOT / 'ssh-response.bin'
    # Orca's audit hook needs named targets; subprocess.PIPE opens anonymous descriptors.
    request.write_bytes(json.dumps(command).encode('ascii') + b'\n' + (payload or b''))
    try:
        with request.open('rb') as src, response.open('wb') as dst:
            subprocess.run(transport_argv(),
                           stdin=src, stdout=dst, stderr=dst, timeout=45, check=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return response.read_bytes()
    finally:
        request.write_bytes(b'')
        response.write_bytes(b'')


GCODE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\.gcode')


def browse_exports():
    root = EXPORT.resolve()
    return sorted((p.name for p in root.iterdir()
                   if GCODE_NAME.fullmatch(p.name) and p.is_file()
                   and p.resolve().parent == root), key=str.casefold)


def upload(name):
    if not isinstance(name, str) or not GCODE_NAME.fullmatch(name):
        raise ValueError('Use a .gcode filename with letters, numbers, underscores, dots or hyphens.')
    source = (EXPORT / name).resolve()
    if source.parent != EXPORT.resolve() or not 0 < source.stat().st_size <= 64 * 1024 * 1024:
        raise ValueError('Select a file in the export folder, at most 64 MiB.')
    payload = source.read_bytes()
    if b'; printer_model = Anycubic Kobra 2 Max' not in payload.splitlines():
        raise ValueError('The export must use the Anycubic Kobra 2 Max profile.')
    digest = hashlib.sha256(payload).hexdigest()
    target = '/mnt/UDISK/' + name
    stage = '/mnt/UDISK/.orca-' + uuid.uuid4().hex + '.part'
    ssh(f'set -euC; trap "rm -f {stage}" EXIT; cat > {stage}; echo "{digest}  {stage}" | sha256sum -c -; ln {stage} {target}; echo "{digest}  {target}" | sha256sum -c -', payload)
    return f'Uploaded and verified {name}. No print started.'


def screen():
    image = (ROOT / 'kobra_touch2.elf').read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    command = f'test -x {HELPER} && echo "{digest}  {HELPER}" | sha256sum -c - >/dev/null'
    try:
        ssh(command)
    except subprocess.CalledProcessError:
        ssh(f'set -euC; umask 077; cat > {HELPER}; echo "{digest}  {HELPER}" | sha256sum -c -; chmod 700 {HELPER}', image)
    b = ssh(f'set -e; {HELPER}; dd if=/dev/fb0 bs=1920 count=544 2>/dev/null')
    geom = struct.unpack_from('<6i', b, 48)
    w,h,vw,vh,dx,dy = geom
    if (w,h,vw,vh,dx) != (480,272,480,544,0) or dy not in (0,272) or len(b) != 72 + 1920*544:
        raise ValueError('Unexpected touchscreen geometry. No tap sent.')
    pixels = b[72 + dy*1920:72 + (dy+h)*1920]
    return pixels


def bmp(frame):
    # Bottom-up Windows bitmap; rotate the native framebuffer counterclockwise.
    data = bytearray()
    for y in range(479,-1,-1):
        for x in range(272):
            i = (x*480 + 479-y)*4
            data += frame[i:i+3]
    return b'BM' + struct.pack('<IHHI',54+len(data),0,0,54) + struct.pack('<IiiHHIIiiII',40,272,480,1,24,0,len(data),0,0,0,0) + data


def tap(x, y, previous):
    if type(x) is not int or type(y) is not int or not (0 <= x < 272 and 0 <= y < 480):
        raise ValueError('Tap outside the touchscreen.')
    current = screen()
    # Ensure the local control under the pointer is still the one shown; heater numbers may change elsewhere.
    for sx in range(max(0,x-15),min(272,x+16)):
        a = (sx*480 + 479-min(479,y+15))*4
        z = (sx*480 + 480-max(0,y-15))*4
        if current[a:z] != previous[a:z]:
            raise ValueError('Screen changed near the tap. Refresh and confirm again.')
    ssh(f'{HELPER} {round(4095*(1-y/480))} {round(4095*(1-x/272))}')
    time.sleep(.7)
    return screen()


class KobraPage(orca.pages.PagesPluginCapabilityBase):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.snapshot = None

    def get_name(self): return 'Kobra 2 Max LAN'
    def get_icon(self): return ''
    def get_ui(self): return PAGE

    def on_message(self, msg):
        try:
            m = json.loads(msg) if isinstance(msg, str) else msg
        except ValueError:
            return
        if not isinstance(m, dict) or m.get('action') not in ('init','browse','screen','upload','tap'):
            return
        def work():
            with self.lock:
                try:
                    action = m['action']
                    if action == 'init':
                        self.post_message({'folder':str(EXPORT),'status':'Browse for an export or refresh the touchscreen.'})
                        return
                    if action == 'browse':
                        files = browse_exports()
                        self.post_message({'files':files,'status':'Choose a file, then click Upload.' if files else 'No compatible filenames in the export folder yet.'})
                        return
                    if action == 'upload':
                        text = upload(m.get('name'))
                    elif action == 'tap':
                        old, self.snapshot = self.snapshot, None
                        if not old or m.get('token') != old[0] or time.monotonic()-old[1] > 45:
                            raise ValueError('Refresh the screen before tapping.')
                        frame = tap(m.get('x'),m.get('y'),old[2])
                        text = 'Tap sent. Check the new screen before sending another.'
                    else:
                        text = 'Live touchscreen. No action sent.'
                    if action != 'tap':
                        frame = screen()
                    token = uuid.uuid4().hex
                    self.snapshot = (token,time.monotonic(),frame)
                    self.post_message({'status':text,'token':token,'image':'data:image/bmp;base64,'+base64.b64encode(bmp(frame)).decode('ascii')})
                except subprocess.CalledProcessError:
                    self.post_message({'status':'SSH operation failed (connection, helper, or file already exists). Refresh to see state; do not assume a tap was applied.'})
                except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
                    self.post_message({'status':str(exc)})
        threading.Thread(target=work,daemon=True).start()


@orca.plugin
class KobraLanPlugin(orca.base):
    def register_capabilities(self):
        orca.request_permissions(fs_read=[str(ROOT / '*')],
                                 fs_readwrite=[str(ROOT / n) for n in ('ssh-request.bin','ssh-response.bin')],
                                 process=[subprocess.list2cmdline(transport_argv())],threading=True)
        orca.register_capability(KobraPage)
