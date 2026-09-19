import hashlib
import http.server
import json
import mimetypes
import os
import pathlib
import socketserver
import zipfile
from urllib.parse import urlparse

EXPECTED_SHA256 = "518d82cceb2843bc4db75d46876f1adc57558b601264bf2e888c9b09232fcbb0"
BASE_DIR = pathlib.Path(__file__).resolve().parent
ZIP_PATH = BASE_DIR / "MEHMET_YARATILIS_PWA_v0.2.2.zip"
EXTRACT_DIR = pathlib.Path("/tmp/mehmet_v022")
ROOT = EXTRACT_DIR / "MEHMET_YARATILIS_PWA_v0.2.2" / "MEHMET_YARATILIS_PWA"

FORENSIC_HTML = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111827">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icons/icon-192.png">
<title>MEHMET v0.2.2 Adli Kabul</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:auto;padding:18px;background:#0b1020;color:#eef2ff}
button,a{display:inline-block;font-size:17px;padding:12px 16px;margin:6px;border-radius:10px;background:#25304f;color:#fff;text-decoration:none;border:0}
button:disabled{opacity:.45}.card{background:#151d32;padding:14px;border-radius:14px;margin:12px 0}
pre{white-space:pre-wrap;word-break:break-word}.ok{color:#6ee7a8}.warn{color:#ffd166}
</style></head><body>
<h1>MEHMET v0.2.2 · Adli Kabul</h1>
<p>Exact ürün dosyaları değiştirilmez. Bu sayfa aynı origin'deki yalnız kabul-görev kayıtlarını ve fiziksel test metriklerini raporlar.</p>
<a href="/">MEHMET PWA'YI AÇ</a>
<button id="scan">KAYITLARI TARA</button>
<button id="loop">🔊 TTS + HOPARLÖR LOOPBACK</button>
<button id="install" disabled>📲 MEHMET'İ KUR</button>
<button id="heard" disabled>🔊 SESİ DUYDUM</button>
<div class="card"><div id="status">Hazırlanıyor…</div><pre id="out">Hazır.</pre></div>
<script>
const out=document.querySelector('#out'), statusEl=document.querySelector('#status');
const installBtn=document.querySelector('#install'), heardBtn=document.querySelector('#heard');
const interesting=new Set(['pwa-install','pwa-install-prompt','camera','camera-capture','microphone','tts','memory-reopen-observed','service-worker','browser-tests']);
let installPrompt=null;
let lastTtsReport=null;

function show(x){out.textContent=JSON.stringify(x,null,2)}
async function post(obj){
  try{await fetch('/__forensic_report',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(obj)})}catch{}
  show(obj);
}
function openDB(){return new Promise((res,rej)=>{const r=indexedDB.open('mehmet_pwa_v1');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
function all(db,store){return new Promise((res,rej)=>{if(!db.objectStoreNames.contains(store))return res([]);const r=db.transaction(store).objectStore(store).getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
async function scan(){
 const report={kind:'storage-scan',ts:new Date().toISOString(),ua:navigator.userAgent,secureContext:window.isSecureContext,standaloneNow:matchMedia('(display-mode: standalone)').matches||navigator.standalone===true};
 try{
   const db=await openDB();
   const tasks=(await all(db,'tasks')).filter(x=>interesting.has(x.type)).map(x=>({type:x.type,status:x.status||null,detail:String(x.detail||'').slice(0,240),verification:String(x.verification||'').slice(0,240),ts:x.ts||null}));
   report.tasks=tasks.slice(-80);
   report.installEventPass=tasks.some(x=>x.type==='pwa-install'&&x.status==='PASS');
   report.installPromptAccepted=tasks.some(x=>x.type==='pwa-install-prompt'&&x.status==='PASS'&&/accepted/i.test(String(x.detail||'')));
   report.cameraPass=tasks.some(x=>x.type==='camera-capture'&&x.status==='PASS');
   report.microphonePass=tasks.some(x=>x.type==='microphone'&&x.status==='PASS'&&/tamamlandı/i.test(String(x.detail||'')));
   report.ttsPass=tasks.some(x=>x.type==='tts'&&x.status==='PASS');
   report.reopenPass=tasks.some(x=>x.type==='memory-reopen-observed'&&x.status==='PASS');
 }catch(e){report.error=String(e?.message||e)}
 await post(report);
 return report;
}
async function measure(an,ms){
 const arr=new Float32Array(an.fftSize);let max=0,sum=0,n=0,end=performance.now()+ms;
 while(performance.now()<end){an.getFloatTimeDomainData(arr);let s=0;for(const x of arr)s+=x*x;const rms=Math.sqrt(s/arr.length);max=Math.max(max,rms);sum+=rms;n++;await new Promise(r=>setTimeout(r,40))}
 return {maxRms:max,avgRms:n?sum/n:0,samples:n};
}
async function ttsLoopback(){
 const report={kind:'tts-loopback',ts:new Date().toISOString(),ua:navigator.userAgent,secureContext:window.isSecureContext};
 let stream,ctx;
 try{
   stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
   const C=window.AudioContext||window.webkitAudioContext;ctx=new C();await ctx.resume();
   const src=ctx.createMediaStreamSource(stream),an=ctx.createAnalyser();an.fftSize=2048;src.connect(an);
   report.baseline=await measure(an,700);
   if(!('speechSynthesis' in window))throw new Error('speechSynthesis unavailable');
   speechSynthesis.cancel();
   const u=new SpeechSynthesisUtterance('MEHMET fiziksel ses testi başarılı');u.lang='tr-TR';
   let started=false,ended=false;
   const finished=new Promise((res,rej)=>{u.onstart=()=>{started=true};u.onend=()=>{ended=true;res()};u.onerror=e=>rej(new Error(e.error||'tts'));setTimeout(()=>rej(new Error('TTS_TIMEOUT')),15000)});
   speechSynthesis.speak(u);
   await new Promise(r=>setTimeout(r,250));
   report.during=await measure(an,2600);
   await finished;
   report.enginePass=started&&ended;
   const floor=Math.max(0.002,report.baseline.maxRms*1.35);
   report.loopbackObserved=report.enginePass && report.during.maxRms>floor && report.during.avgRms>Math.max(0.0007,report.baseline.avgRms*1.15);
   report.status=report.loopbackObserved?'PHYSICAL_LOOPBACK_PASS':(report.enginePass?'ENGINE_PASS_LOOPBACK_UNCERTAIN':'FAIL');
   lastTtsReport=report;
   heardBtn.disabled=false;
 }catch(e){report.status='FAIL';report.error=String(e?.message||e)}
 finally{stream?.getTracks().forEach(t=>t.stop());try{await ctx?.close()}catch{}}
 await post(report);
}
window.addEventListener('beforeinstallprompt',e=>{
  e.preventDefault();installPrompt=e;installBtn.disabled=false;statusEl.textContent='Kurulum istemi hazır.';
  post({kind:'installability-event',ts:new Date().toISOString(),ua:navigator.userAgent,beforeInstallPrompt:true});
});
window.addEventListener('appinstalled',()=>{
  installPrompt=null;installBtn.disabled=true;statusEl.textContent='PWA kuruldu.';
  post({kind:'appinstalled',ts:new Date().toISOString(),ua:navigator.userAgent,appinstalled:true,standaloneNow:matchMedia('(display-mode: standalone)').matches});
  setTimeout(scan,500);
});
installBtn.onclick=async()=>{
  if(!installPrompt){statusEl.textContent='Kurulum istemi henüz gelmedi; Chrome menüsündeki Uygulamayı yükle seçeneğini kullan.';return}
  installPrompt.prompt();const c=await installPrompt.userChoice;
  await post({kind:'install-choice',ts:new Date().toISOString(),ua:navigator.userAgent,outcome:c.outcome});
  if(c.outcome!=='accepted')statusEl.textContent='Kurulum kabul edilmedi.';
};
heardBtn.onclick=async()=>{
  const r={...(lastTtsReport||{}),kind:'tts-heard-confirmation',ts:new Date().toISOString(),ua:navigator.userAgent,heardByUser:true,status:'PHYSICAL_AUDIBLE_PASS'};
  heardBtn.disabled=true;await post(r);
};
document.querySelector('#scan').onclick=scan;
document.querySelector('#loop').onclick=ttsLoopback;
(async()=>{
 try{if('serviceWorker'in navigator){await navigator.serviceWorker.register('/sw.js');await navigator.serviceWorker.ready}}
 catch(e){statusEl.textContent='Service worker hazırlığı: '+String(e?.message||e)}
 await scan();
})();
</script></body></html>"""

print("RUNTIME_BOOT_START", flush=True)
payload = ZIP_PATH.read_bytes()
actual = hashlib.sha256(payload).hexdigest()
print(f"ARTIFACT_SIZE={len(payload)}", flush=True)
print(f"ARTIFACT_SHA256={actual}", flush=True)
if actual != EXPECTED_SHA256:
    raise SystemExit(f"SHA256_MISMATCH expected={EXPECTED_SHA256} actual={actual}")

with zipfile.ZipFile(ZIP_PATH) as zf:
    bad = zf.testzip()
    if bad is not None:
        raise SystemExit(f"ZIP_INTEGRITY_FAIL={bad}")
    zf.extractall(EXTRACT_DIR)

if not ROOT.is_dir():
    raise SystemExit(f"ROOT_NOT_FOUND={ROOT}")

os.chdir(ROOT)
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

class Handler(http.server.SimpleHTTPRequestHandler):
    def _send_bytes(self, code, ctype, data):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/__forensic_acceptance":
            return self._send_bytes(200, "text/html; charset=utf-8", FORENSIC_HTML.encode("utf-8"))
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/__forensic_report":
            try:
                n = int(self.headers.get("content-length", "0"))
                obj = json.loads(self.rfile.read(n) or b"{}")
                print("FORENSIC_ACCEPTANCE_REPORT="+json.dumps(obj,ensure_ascii=False,separators=(",",":")), flush=True)
                return self._send_bytes(200, "application/json", b'{"ok":true}')
            except Exception as e:
                return self._send_bytes(400, "application/json", json.dumps({"ok":False,"error":str(e)}).encode())
        return super().do_POST()

    def end_headers(self):
        self.send_header("Permissions-Policy", "camera=(self), microphone=(self)")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("HTTP", self.address_string(), fmt % args, flush=True)

port = int(os.environ.get("PORT", "8080"))
socketserver.TCPServer.allow_reuse_address = True
print(f"SERVING_ROOT={ROOT}", flush=True)
print(f"SERVING_PORT={port}", flush=True)
with socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler) as server:
    server.serve_forever()
