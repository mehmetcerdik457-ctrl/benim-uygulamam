"""Exercise owner authentication and chat through an actual runtime HTTP server.
--live uses configured deployment secrets; prints only synthetic test outcomes.
"""
import base64
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
live = '--live' in sys.argv

def request(url, auth=None, payload=None):
    headers = {'Content-Type': 'application/json'}
    if auth:
        headers['Authorization'] = auth
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=65) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def basic(user, password):
    return 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()

class MockBackend(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.headers.get('X-MEH-Proxy-Token') == 'local-proxy-test'
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert body['message']
        data = json.dumps({'text':'MEHMET_OK','provider':'test','model':'local-mock','request_id':'local-test'}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
    def log_message(self,*args): pass

env = dict(os.environ)
mock = None
if not live:
    mock = ThreadingHTTPServer(('127.0.0.1',0),MockBackend)
    threading.Thread(target=mock.serve_forever,daemon=True).start()
    env.update(OWNER_BASIC_USER='mehmet-test',OWNER_BASIC_PASSWORD=secrets.token_urlsafe(24),AI_BACKEND_PROXY_TOKEN='local-proxy-test',AI_BACKEND_URL=f'http://127.0.0.1:{mock.server_port}')
assert env.get('OWNER_BASIC_USER') and env.get('OWNER_BASIC_PASSWORD'), 'OWNER_SETUP_REQUIRED'
with socket.socket() as s:
    s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
env['PORT']=str(port)
base=f'http://127.0.0.1:{port}'
auth=basic(env['OWNER_BASIC_USER'],env['OWNER_BASIC_PASSWORD'])
with tempfile.TemporaryFile() as log:
    proc=subprocess.Popen([sys.executable,str(ROOT/'runtime_v022_server.py')],env=env,stdout=log,stderr=log)
    try:
        for _ in range(100):
            try:
                status,raw=request(base+'/__health');break
            except OSError:
                if proc.poll() is not None:raise RuntimeError('RUNTIME_START_FAILED')
                time.sleep(.1)
        assert status==200 and json.loads(raw)['owner_auth_configured']
        for path in ['/api/owner/status','/api/chat','/__forensic_acceptance']:
            assert request(base+path,payload={'message':'test'} if path=='/api/chat' else None)[0]==401,path
        assert request(base+'/api/chat',basic('normal-test','wrong'),{'message':'test'})[0]==401
        assert request(base+'/__forensic_report',payload={'kind':'test'})[0]==401
        status,raw=request(base+'/api/owner/status',auth)
        assert status==200 and json.loads(raw)['authenticated']
        assert json.loads(raw)['owner']['AUTH_LEVEL']=='OWNER'
        assert request(base+'/app.js',auth)[0]==200
        assert request(base+'/sw.js',auth)[0]==200
        print('OWNER_AUTH_HTTP_TEST=PASS; NORMAL_USER_NEGATIVE_TEST=PASS',flush=True)
        status,raw=request(base+'/api/chat',auth,{'provider':'openai','message':'Bu bağlantı testidir. Yalnız MEHMET_OK yaz.','attachments':[]})
        reply=json.loads(raw)
        if status != 200 and '--diagnose' in sys.argv:
            print(json.dumps({'event':'OWNER_CHAT_ACCEPTANCE','mode':'real-provider','status':'BLOCKED','http_status':status,'upstream_status':reply.get('upstream_status'),'upstream_code':reply.get('upstream_code'),'request_id':reply.get('request_id')}),flush=True)
            sys.exit(0)
        assert status==200, f'CHAT_STATUS={status}; ERROR={reply.get("error")}'
        assert 'MEHMET_OK' in reply.get('text',''), 'UNEXPECTED_MODEL_RESPONSE'
        print(json.dumps({'event':'OWNER_CHAT_ACCEPTANCE','mode':'real-provider' if live else 'mock','status':'PASS','model':reply.get('model'),'request_id':reply.get('request_id')}),flush=True)
    finally:
        proc.terminate();proc.wait(timeout=10)
        if mock:mock.shutdown()
