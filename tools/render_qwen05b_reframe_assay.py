#!/usr/bin/env python3
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
STATE={"status":"STOPPED","reason":"1.5B inference host restart loop stopped after evidence capture","issue":31}
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps(STATE,separators=(",",":")).encode()
        self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass
ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
