#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, tarfile, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORK=pathlib.Path('/tmp/llama-inventory'); WORK.mkdir(parents=True,exist_ok=True)
URL='https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-ubuntu-x64.tar.gz'
SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
STATE={'status':'BOOTING','result':None,'error':None}; LOCK=threading.Lock()

def digest(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def run():
 try:
  p=WORK/'llama.tar.gz'
  req=urllib.request.Request(URL,headers={'User-Agent':'llama-rpc-inventory/1'})
  with urllib.request.urlopen(req,timeout=120) as r,p.open('wb') as o:
   while True:
    c=r.read(1024*1024)
    if not c: break
    o.write(c)
  if digest(p)!=SHA: raise RuntimeError('SHA_MISMATCH')
  with tarfile.open(p,'r:gz') as tf: names=tf.getnames()
  rpc=[n for n in names if 'rpc' in n.lower()]
  bins=[n for n in names if any(x in pathlib.Path(n).name for x in ('llama-server','llama-cli','rpc'))]
  result={'archive_sha256':SHA,'entry_count':len(names),'rpc_entries':rpc,'relevant_entries':bins,'has_rpc':bool(rpc)}
  with LOCK: STATE.update(status='PASS',result=result,error=None)
  print('INVENTORY_RESULT='+json.dumps(result,separators=(',',':')),flush=True)
 except Exception as e:
  with LOCK: STATE.update(status='FAIL',error=f'{type(e).__name__}:{e}')
  print('INVENTORY_ERROR='+STATE['error'],flush=True)

class H(BaseHTTPRequestHandler):
 def do_GET(self):
  with LOCK: b=json.dumps(STATE).encode()
  self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def log_message(self,*a): pass

def main():
 threading.Thread(target=run,daemon=True).start(); ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','10000'))),H).serve_forever()
if __name__=='__main__': main()
