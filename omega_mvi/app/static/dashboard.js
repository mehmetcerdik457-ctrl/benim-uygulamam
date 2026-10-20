"use strict";
const $=id=>document.getElementById(id);
const show=(id,value)=>{const node=$(id);if(node)node.textContent=value};
async function json(path){
  const res=await fetch(path,{method:"GET",cache:"no-store",credentials:"omit",redirect:"error"});
  if(!res.ok)throw Error("local_demo_unavailable");
  return await res.json();
}
async function health(){
  try {
    const x=await json("/api/health");
    if(x.production_ready!==false || x.mode!=="mock")throw Error("unexpected_mode");
    show("health","Servis: "+String(x.status)+" | Mod: "+x.mode+" | Üretim: KAPALI");
  } catch(_) {show("health","Yerel API erişilemiyor; hiçbir işlem başlatılmaz.");}
}
async function inspection(){
  try {
    const x=await json("/api/demo/inspection");
    if(x.production_ready!==false || x.authority!=="none" || x.mode!=="synthetic_offline_only" ||
       x.redaction_applied!==true || !Array.isArray(x.sources))throw Error("untrusted_result");
    const sources=x.sources.slice(0,5);
    if(sources.some(s=>typeof s.ref!=="string" || !s.ref.startsWith("synthetic://")))throw Error("unsafe_reference");
    show("inspection","4 sentetik modül: GitHub envanteri, maskeleme, kaynaklı arama ve PR inceleme. "+
      "Kaynak sayısı: "+sources.length+". Karar yetkisi: YOK.");
    show("sources",sources.map(s=>s.ref).join(" | "));
  } catch(_) {show("inspection","Sentetik denetim kullanılamıyor; erişim genişletilmez.");show("sources","");}
}
// The server alone indexes fixed public files. UI validation is presentation
// defense-in-depth, NOT a cryptographic attestation or permission authority.
const PUBLIC_SOURCE_PATHS=Object.freeze([
  "omega_mvi/inspection/pipeline.py",
  "omega_mvi/inspection/github_inventory/__init__.py",
  "omega_mvi/inspection/pr_review/engine.py",
  "omega_mvi/inspection/redaction/__init__.py",
  "omega_mvi/inspection/retrieval/__init__.py"
]);
function exactObjectKeys(value,keys){
  return value!==null && typeof value==="object" && !Array.isArray(value) &&
    Object.keys(value).length===keys.length &&
    keys.every(key=>Object.prototype.hasOwnProperty.call(value,key));
}
function safeInteger(value,max,min=0){
  return Number.isSafeInteger(value) && value>=min && value<=max;
}
function validatePublicSourceIndex(x){
  if(!exactObjectKeys(x,["mode","input","files","files_indexed",
      "symbol_count","read_only","external_calls","authenticated_owner",
      "production_ready","acceptance"]))return null;
  if(x.mode!=="real-public-source-ast" ||
     x.input!=="fixed local installed public modules" ||
     x.production_ready!==false || x.external_calls!==false ||
     x.read_only!==true || x.authenticated_owner!==false ||
     x.acceptance!=="NOT_ACCEPTED" || x.files_indexed!==5 ||
     !safeInteger(x.symbol_count,10000) ||
     !Array.isArray(x.files) || x.files.length!==5)return null;
  const seen=new Set();
  let sum=0;
  const name=/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/;
  const callable=/^(?:<module>|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)$/;
  for(const file of x.files){
    if(!exactObjectKeys(file,["path","sha256","byte_length","symbols",
       "imports","call_edges","dynamic_calls_unresolved"]) ||
       !PUBLIC_SOURCE_PATHS.includes(file.path) || seen.has(file.path) ||
       typeof file.sha256!=="string" || !/^[a-f0-9]{64}$/.test(file.sha256) ||
       !safeInteger(file.byte_length,131072,1) ||
       !safeInteger(file.dynamic_calls_unresolved,100000) ||
       !Array.isArray(file.symbols) || !file.symbols.length || file.symbols.length>2000 ||
       !Array.isArray(file.imports) || file.imports.length>2000 ||
       !Array.isArray(file.call_edges) || file.call_edges.length>10000)return null;
    seen.add(file.path);
    for(const symbol of file.symbols){
      if(!exactObjectKeys(symbol,["symbol","kind","line"]) ||
         typeof symbol.symbol!=="string" || !name.test(symbol.symbol) ||
         !["class","function","async_function"].includes(symbol.kind) ||
         !safeInteger(symbol.line,100000,1))return null;
    }
    if(file.imports.some(item=>typeof item!=="string" ||
       !/^[.A-Za-z0-9_]{1,256}$/.test(item)))return null;
    for(const call of file.call_edges){
      if(!exactObjectKeys(call,["from","to"]) ||
         typeof call.from!=="string" || !callable.test(call.from) ||
         typeof call.to!=="string" || !callable.test(call.to))return null;
    }
    sum+=file.symbols.length;
  }
  if(seen.size!==PUBLIC_SOURCE_PATHS.length ||
     !PUBLIC_SOURCE_PATHS.every(path=>seen.has(path)) ||
     sum!==x.symbol_count)return null;
  return x;
}
async function publicSources(){
  try {
    const raw=await json("/api/demo/source-index");
    const index=validatePublicSourceIndex(raw);
    if(!index)throw Error("invalid_public_source_index");
    show("source-index","Gerçek public kod indeksi: "+index.files.length+
      " izinli Python dosyası, "+index.symbol_count+
      " sembol. YALNIZCA PUBLIC • KABUL EDİLMEDİ • Yürütme KAPALI.");
    show("source-index-detail",index.files.map(f=>f.path+
      " — SHA-256: "+f.sha256.slice(0,12)+"…").join(" | "));
  } catch(_) {
    show("source-index","Public kaynak indeksi DOĞRULANAMADI / KAPALI.");
    show("source-index-detail","");
  }
}

async function db(){
  const output=$("states");output.replaceChildren();
  try{
    const x=await json("/api/demo/task-status");
    if(x.mode!=="disposable-synthetic-only" || x.production_ready!==false ||
       x.task_details_available!==false || !Array.isArray(x.aggregate))throw Error("unexpected_data");
    const allowed=new Set(["CREATED","PLANNED","APPROVAL_PENDING","RUNNING","VERIFYING","SUCCEEDED","FAILED","CANCELLED"]);
    if(x.aggregate.length>8 || x.aggregate.some(s=>!allowed.has(s.state) ||
       !Number.isSafeInteger(s.count) || s.count<0))throw Error("unexpected_state");
    for(const entry of x.aggregate){
      const li=document.createElement("li");
      li.textContent=entry.state+": "+entry.count;
      output.appendChild(li);
    }
    show("db-status","Yalnızca geçici test veritabanı: toplu durum sayıları. Kullanıcı ve görev ayrıntısı gösterilmez.");
  }catch(_){
    show("db-status","PostgreSQL görünümü KAPALI / ERİŞİLEMİYOR. Kimlik ve yetki olmadan gerçek görev okunmaz.");
  }
}
async function refresh(){await Promise.all([health(),inspection(),publicSources(),db()]);}
$("refresh").addEventListener("click",refresh);
refresh();
