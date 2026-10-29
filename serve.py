#!/usr/bin/env python3
"""Static server with HTTP Range support (needed for <video> seeking).

Usage:  python3 serve.py [port]      then open http://localhost:8779
"""
import os
import re
import sys
import http.server
import socketserver
import mimetypes

ROOT = os.path.dirname(os.path.abspath(__file__))


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        if not os.path.isfile(path):
            return super().do_GET()

        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range') or '')

        if not m:
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with open(path, 'rb') as f:
                self.copyfile(f, self.wfile)
            return

        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        length = max(0, end - start + 1)

        self.send_response(206)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(length))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        with open(path, 'rb') as f:
            f.seek(start)
            self.wfile.write(f.read(length))

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8779
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', port), H) as s:
        print('serving %s on http://localhost:%d' % (ROOT, port))
        s.serve_forever()
