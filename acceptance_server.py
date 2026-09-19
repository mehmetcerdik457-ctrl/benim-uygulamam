import json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

REPORTS = []

HTML = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>MEHMET v0.2.2 Fiziksel Cihaz Kabul</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:auto;padding:18px;background:#0b1020;color:#eef2ff}
button{font-size:18px;padding:14px 18px;margin:8px 4px;border:0;border-radius:12px}
.card{background:#151d32;padding:14px;border-radius:14px;margin:12px 0}video{width:100%;max-height:320px;background:#000;border-radius:12px}
pre{white-space:pre-wrap;word-break:break-word}
</style></head><body>
<h1>MEHMET v0.2.2 · Fiziksel Cihaz Kabul</h1>
<p>Bu yardımcı test ürün ZIP'ini değiştirmez. Yalnız telefonun gerçek kamera, mikrofon, TTS ve standalone durumunu ölçer.</p>
<div class="card"><b>Talimat:</b> BAŞLAT'a bastıktan sonra kamera/mikrofon izinlerini ver ve 3 saniye boyunca <b>“MEHMET TEST”</b> de.</div>
<button id="start">BAŞLAT FİZİKSEL TEST</button>
<button id="heard" disabled>🔊 SESİ DUYDUM</button>
<button id="standalone">📱 STANDALONE KONTROL</button>
<video id="v" autoplay playsinline muted></video>
<div class="card"><pre id="out">Hazır.</pre></div>
<script>
const out=document.querySelector('#out'),v=document.querySelector('#v'),heard=document.querySelector('#heard');
const report={session:crypto.randomUUID?.()||String(Date.now()),ts:new Date().toISOString(),ua:navigator.userAgent};
const show=()=>out.textContent=JSON.stringify(report,null,2);
const sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function send(){try{await fetch('/report',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(report)})}catch{}show()}
async function audioEnergy(stream,ms=2600){const C=window.AudioContext||window.webkitAudioContext;const ctx=new C();await ctx.resume();const src=ctx.createMediaStreamSource(stream),an=ctx.createAnalyser();an.fftSize=2048;src.connect(an);const arr=new Float32Array(an.fftSize);let max=0,sum=0,n=0,until=performance.now()+ms;while(performance.now()<until){an.getFloatTimeDomainData(arr);let s=0;for(const x of arr)s+=x*x;const rms=Math.sqrt(s/arr.length);max=Math.max(max,rms);sum+=rms;n++;await new Promise(r=>setTimeout(r,60))}await ctx.close();return{maxRms:max,avgRms:n?sum/n:0}}
start.onclick=async()=>{report.secureContext=window.isSecureContext;report.online=navigator.onLine;report.standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;report.camera={status:'PENDING'};report.microphone={status:'PENDING'};report.tts={status:'PENDING',heardByUser:false};show();let stream;
try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}});v.srcObject=stream;await v.play();await new Promise(r=>setTimeout(r,1200));const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',.88));const ab=await blob.arrayBuffer();report.camera={status:(v.videoWidth>0&&v.videoHeight>0&&blob.size>0)?'PASS':'FAIL',width:v.videoWidth,height:v.videoHeight,jpegBytes:blob.size,jpegSha256:await sha(ab)};const rec=new MediaRecorder(stream),chunks=[];rec.ondataavailable=e=>e.data.size&&chunks.push(e.data);rec.start();const energy=await audioEnergy(stream,2600);await new Promise(r=>setTimeout(r,400));const stopped=new Promise(r=>rec.onstop=r);rec.stop();await stopped;const audio=new Blob(chunks,{type:rec.mimeType||'audio/webm'});report.microphone={status:(audio.size>0&&energy.maxRms>0.0005)?'PASS':'PARTIAL',blobBytes:audio.size,mime:audio.type,maxRms:energy.maxRms,avgRms:energy.avgRms}}
catch(e){report.mediaError=String(e?.name||e)+': '+String(e?.message||'');report.camera={status:'FAIL'};report.microphone={status:'FAIL'}}
finally{stream?.getTracks().forEach(t=>t.stop());v.srcObject=null}
try{if(!('speechSynthesis'in window))throw new Error('speechSynthesis unavailable');speechSynthesis.cancel();const u=new SpeechSynthesisUtterance('MEHMET fiziksel ses testi başarılı');u.lang='tr-TR';await new Promise((res,rej)=>{let started=false;u.onstart=()=>{started=true;report.tts={status:'STARTED',heardByUser:false};show()};u.onend=()=>res(started);u.onerror=e=>rej(new Error(e.error||'tts'));speechSynthesis.speak(u);setTimeout(()=>rej(new Error('TTS_TIMEOUT')),15000)});report.tts={status:'ENGINE_PASS',heardByUser:false};heard.disabled=false}catch(e){report.tts={status:'FAIL',heardByUser:false,error:String(e.message||e)}}await send()};
heard.onclick=async()=>{report.tts={...(report.tts||{}),status:'PHYSICAL_AUDIBLE_PASS',heardByUser:true};await send();heard.disabled=true};
standalone.onclick=async()=>{report.standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;report.standaloneCheckedAt=new Date().toISOString();await send()};
show();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _h(self, code=200, ctype='text/html; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Permissions-Policy', 'camera=(self), microphone=(self)')
        self.end_headers()
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/':
            self._h(); self.wfile.write(HTML.encode())
        elif p=='/latest':
            self._h(200,'application/json'); self.wfile.write(json.dumps(REPORTS[-10:],ensure_ascii=False,indent=2).encode())
        elif p=='/health':
            self._h(200,'application/json'); self.wfile.write(b'{"status":"PASS"}')
        else:
            self._h(404,'text/plain'); self.wfile.write(b'not found')
    def do_POST(self):
        if urlparse(self.path).path!='/report':
            self._h(404,'text/plain'); return
        try:
            n=int(self.headers.get('content-length','0'))
            obj=json.loads(self.rfile.read(n) or b'{}')
            obj['serverTs']=time.time()
            REPORTS.append(obj); del REPORTS[:-50]
            print('PHYSICAL_ACCEPTANCE_REPORT='+json.dumps(obj,ensure_ascii=False,separators=(',',':')),flush=True)
            self._h(200,'application/json'); self.wfile.write(b'{"ok":true}')
        except Exception as e:
            self._h(400,'application/json'); self.wfile.write(json.dumps({'ok':False,'error':str(e)}).encode())
    def log_message(self,fmt,*args):
        print('HTTP '+fmt%args,flush=True)

port=int(os.environ.get('PORT','8080'))
print('PHYSICAL_ACCEPTANCE_SERVER_START port='+str(port),flush=True)
ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()
