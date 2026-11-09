#!/usr/bin/env python3
"""Prepare a user-local QQMusic copy with modern Electron bridge support."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys

SOURCE = Path('/usr/lib/qqmusic/app.asar')
ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'app'

PRELOAD = '''const {contextBridge, ipcRenderer} = require('electron');
// Expose only the message channel used by QQMusic's embedded pages.
const trusted = location.protocol === 'https:' &&
  (location.hostname === 'qq.com' || location.hostname.endsWith('.qq.com'));
if (trusted) {
  const bridge = Object.freeze({
    sendToHost(channel, payload) {
      if (channel === 'client-message' && typeof payload === 'string' && payload.length <= 1048576) {
        ipcRenderer.sendToHost(channel, payload);
      }
    }
  });
  if (process.contextIsolated) contextBridge.exposeInMainWorld('ipcRenderer', bridge);
  else window.ipcRenderer = bridge;
}
'''

def files(node, prefix=Path()):
    for name, item in node.get('files', {}).items():
        if name in ('.', '..') or '/' in name or '\\' in name:
            raise RuntimeError('Invalid ASAR entry')
        current = prefix / name
        if 'files' in item:
            yield from files(item, current)
        else:
            yield current, item

def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    version = {'source_sha256': digest, 'patch_version': 3}
    manifest = ROOT / 'manifest.json'
    if TARGET.is_dir() and manifest.exists() and json.loads(manifest.read_text()) == version:
        return
    stage = ROOT / f'app.tmp-{os.getpid()}'
    stage.mkdir()
    try:
        with SOURCE.open('rb') as archive:
            header = struct.unpack('<IIII', archive.read(16))
            tree = json.loads(archive.read(header[3]))
            offset = 8 + header[1]
            for relative, entry in files(tree):
                if entry.get('unpacked') or 'link' in entry:
                    raise RuntimeError('Unsupported ASAR entry')
                dest = stage / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                archive.seek(offset + int(entry['offset']))
                data = archive.read(entry['size'])
                if len(data) != entry['size']:
                    raise RuntimeError('Truncated ASAR')
                dest.write_bytes(data)
                if entry.get('executable'):
                    dest.chmod(0o755)
        (stage / 'preload.js').write_text(PRELOAD)
        old = ROOT / 'app.previous'
        if old.exists():
            shutil.rmtree(old)
        if TARGET.exists():
            TARGET.rename(old)
        stage.rename(TARGET)
        manifest.write_text(json.dumps(version, indent=2) + '\n')
        if old.exists():
            shutil.rmtree(old)
    finally:
        if stage.exists():
            shutil.rmtree(stage)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'QQMusic compatibility preparation failed: {exc}', file=sys.stderr)
        sys.exit(1)
