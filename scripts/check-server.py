#!/usr/bin/env python3
"""Wait for the restarted API and report HTTP failures without JSON tracebacks."""
import argparse
import json
import subprocess
import sys
import time


class CheckError(Exception):
    pass


def fetch(url):
    result = subprocess.run(['curl', '--silent', '--show-error', '--connect-timeout', '3',
                             '--max-time', '5', '--write-out', '\n%{http_code}', url],
                            capture_output=True, text=True)
    if result.returncode:
        return 0, result.stderr.strip() or 'connection failed'
    body, code = result.stdout.rsplit('\n', 1)
    return int(code), body


def wait_for_json(url, predicate, timeout=60):
    deadline = time.monotonic() + timeout
    waiting = False
    while True:
        status, body = fetch(url)
        if status == 200:
            try:
                value = json.loads(body)
            except ValueError:
                raise CheckError(url + ': expected JSON but received a different response. Check API routing.')
            if not isinstance(value, dict) or not predicate(value):
                raise CheckError(url + ': JSON response does not match the expected API.')
            print(url + ': OK')
            return
        if status not in (0, 502, 503, 504):
            raise CheckError(f'{url}: HTTP {status}. Check backend logs.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            reason = f'HTTP {status}' if status else body
            raise CheckError(f'{url}: backend did not become ready within {timeout}s ({reason}). Run: pm2 logs smart-finance-api --lines 60 --nostream')
        if not waiting:
            print('Waiting for backend startup: ' + url, flush=True)
            waiting = True
        time.sleep(min(2, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://finance.hazdeen.xyz')
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    base = args.base_url.rstrip('/')
    try:
        wait_for_json(base + '/api', lambda data: data.get('status') == 'ok', args.timeout)
        wait_for_json(base + '/api/openapi.json', lambda data: '/api/v1/auth/login' in data.get('paths', {}), args.timeout)
    except CheckError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
