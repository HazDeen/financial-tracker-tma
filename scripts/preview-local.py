#!/usr/bin/env python3
"""Local-only presentation of the built UI. Uses a separate seeded demo backend."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
import mimetypes

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'frontend/dist'
ORIGIN = 'http://127.0.0.1:4174'


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            return self.proxy()
        if path in ('/', '/mobile', '/desktop'):
            return self.file(ROOT / 'scripts/preview.html')
        if path == '/app':
            return self.file(DIST / 'index.html')
        candidate = (DIST / path.lstrip('/')).resolve()
        if DIST.resolve() in candidate.parents:
            return self.file(candidate)
        self.send_error(404)

    def do_POST(self): self.proxy()
    def do_PUT(self): self.proxy()
    def do_PATCH(self): self.proxy()
    def do_DELETE(self): self.proxy()

    def proxy(self):
        if not self.path.startswith('/api/'):
            return self.send_error(404)
        if self.headers.get('Origin') not in (None, ORIGIN):
            return self.send_error(403)
        size = int(self.headers.get('Content-Length', '0'))
        if size > 11 * 1024 * 1024:
            return self.send_error(413)
        data = self.rfile.read(size) if size else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in ('cookie', 'content-type', 'accept')}
        headers['Origin'] = 'http://127.0.0.1:8000'
        request = Request('http://127.0.0.1:8000' + self.path, data=data, method=self.command, headers=headers)
        try:
            response = urlopen(request, timeout=120)
        except HTTPError as error:
            response = error
        self.send_response(response.status)
        for name, value in response.headers.items():
            if name.lower() in ('content-type', 'set-cookie', 'cache-control'):
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.read())

    def file(self, path):
        if not path.is_file(): return self.send_error(404)
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(path.read_bytes())


if __name__ == '__main__':
    print('Local previews: http://127.0.0.1:4174/mobile and /desktop', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 4174), Preview).serve_forever()
