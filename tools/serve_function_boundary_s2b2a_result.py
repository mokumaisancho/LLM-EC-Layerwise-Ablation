#!/usr/bin/env python3
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / 'results' / 'function_boundary_s2b2a_qwen25_1p5b_runtime.json'

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = RESULT.read_bytes() if RESULT.exists() else json.dumps({'status':'MISSING_BUILD_RESULT'}).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args):
        pass

ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','10000'))),H).serve_forever()
