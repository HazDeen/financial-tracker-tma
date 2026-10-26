#!/usr/bin/env python3
"""Replace only the finance site, validate, back up and reload the existing Caddy config."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def replace_finance_site(source, replacement):
    matches = list(re.finditer(r'(?m)^[ \t]*finance\.hazdeen\.xyz[ \t]*\{', source))
    if len(matches) != 1:
        raise ValueError('Expected exactly one standalone finance.hazdeen.xyz block; no configuration changed.')
    start = matches[0].start()
    opening = matches[0].end() - 1
    depth, quoted, comment, escaped = 0, False, False, False
    for index in range(opening, len(source)):
        char = source[index]
        if comment:
            if char == '\n':
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '#':
            comment = True
        elif char == '"':
            quoted = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return source[:start] + replacement.strip() + source[index + 1:]
    raise ValueError('Unclosed finance site block; no configuration changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('/etc/caddy/Caddyfile'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = args.config.resolve()
    original = config.read_text()
    updated = replace_finance_site(original, (ROOT / 'deploy/finance.Caddyfile').read_text())
    if args.dry_run:
        print(updated)
        return
    if updated == original:
        print('Finance routing already matches the project configuration.')
        return
    if os.geteuid() != 0:
        raise SystemExit('Run this command with sudo to update Caddy.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=config.parent, prefix='.finance-caddy-', delete=False) as stream:
            stream.write(updated)
            temporary = Path(stream.name)
        temporary.chmod(config.stat().st_mode & 0o777)
        subprocess.run(['caddy', 'validate', '--config', str(temporary), '--adapter', 'caddyfile'], check=True)
        backup_dir = Path('/var/backups/smart-finance')
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = backup_dir / ('Caddyfile-' + stamp)
        shutil.copy2(config, backup)
        os.replace(temporary, config)
        temporary = None
        try:
            subprocess.run(['systemctl', 'reload', 'caddy'], check=True)
        except subprocess.CalledProcessError:
            shutil.copy2(backup, config)
            subprocess.run(['systemctl', 'reload', 'caddy'], check=False)
            raise SystemExit('Reload failed. Previous configuration restored: ' + str(backup))
        print('Finance routing updated. Backup: ' + str(backup))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
