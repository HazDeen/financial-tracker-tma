#!/usr/bin/env python3
"""Package explicit release inputs only: never include credentials, databases, or signing keys."""
from pathlib import Path
import hashlib
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.4.0'
OUT = ROOT / 'output/releases' / VERSION
OUT.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'android' / f'RELEASE-{VERSION}.md', OUT / 'UPDATE.md')


def archive(name, paths):
    target = OUT / name
    with ZipFile(target, 'w', ZIP_DEFLATED) as bundle:
        for path in sorted(set(paths)):
            if path.is_file():
                assert path.name != '.env' and path.suffix not in {'.db', '.jks', '.pyc'}
                bundle.write(path, path.relative_to(ROOT))
        bundle.write(OUT / 'UPDATE.md', 'UPDATE.md')
    return target


frontend = list((ROOT / 'frontend/dist').rglob('*'))
archive('frontend-1.4.0.zip', frontend)
backend = [ROOT / 'backend/main.py', ROOT / 'backend/requirements.txt', ROOT / 'backend/alembic.ini']
backend += list((ROOT / 'backend/app').rglob('*.py'))
backend += list((ROOT / 'backend/alembic').rglob('*.py'))
backend += list((ROOT / 'backend/alembic').rglob('*.mako'))
source = list((ROOT / 'frontend/src').rglob('*'))
source += [p for p in (ROOT / 'frontend/public').rglob('*') if p.is_file() and p.suffix != '.apk']
source += [ROOT / 'frontend' / name for name in ['package.json', 'package-lock.json', 'index.html', 'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json']]
archive('site-update-1.4.0.zip', frontend + backend + source)
shutil.copy2(ROOT / 'output/android/moi-finansy-1.4.0.apk', OUT / 'moi-finansy-1.4.0.apk')
files = [OUT / name for name in ['frontend-1.4.0.zip','site-update-1.4.0.zip','moi-finansy-1.4.0.apk']]
(OUT / 'SHA256SUMS.txt').write_text(''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in files))
for path in files:
    print(path.name, path.stat().st_size, 'bytes')
