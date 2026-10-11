"use strict";
const $=id=>document.getElementById(id);
const show=(id,value)=>{const node=$(id);if(node)node.textContent=value};
async function json(path){
  const res=await fetch(path,{method:"GET",cache:"no-store",credentials:"omit",redirect:"error"});
  if(!res.ok)throw Error("local_demo_unavailable");
  return await res.json();
}
let activeRefresh=0;
async function health(runId){
  try {
    const x=await json("/api/health");
    if(runId!==activeRefresh)return;
    if(!x || x.production_ready!==false || x.mode!=="mock" ||
       x.service!=="omega-mvi-demo" || x.status!=="ok")throw Error("unexpected_mode");
    show("health","Servis: "+String(x.status)+" | Mod: "+x.mode+" | Üretim: KAPALI");
  } catch(_) {if(runId===activeRefresh)show("health","Yerel API erişilemiyor; hiçbir işlem başlatılmaz.");}
}
async function inspection(runId){
  try {
    const x=await json("/api/demo/inspection");
    if(runId!==activeRefresh)return;
    if(!x || x.production_ready!==false || x.authority!=="none" || x.mode!=="synthetic_offline_only" ||
       x.redaction_applied!==true || !Array.isArray(x.sources))throw Error("untrusted_result");
    // This route is explicitly synthetic-only. A prefix does not prove a citation.
    // Production provenance will require a separate authenticated endpoint/schema.
    const allowedRefs=new Set([
      "synthetic://omega-fixtures/owner-controls.md#access",
      "synthetic://omega-fixtures/provenance.md#citations",
      "synthetic://omega-fixtures/privacy.md#secrets"
    ]);
    if(x.sources.length>5 || x.sources.some(s=>!s || typeof s!=="object" ||
       !allowedRefs.has(s.ref) || !Number.isSafeInteger(s.score) || s.score<1) ||
       new Set(x.sources.map(s=>s.ref)).size!==x.sources.length)throw Error("unsafe_reference");
    const sources=x.sources;
    show("inspection","4 sentetik modül: GitHub envanteri, maskeleme, kaynaklı arama ve PR inceleme. "+
      "Kaynak sayısı: "+sources.length+". Karar yetkisi: YOK.");
    show("sources",sources.map(s=>s.ref).join(" | "));
  } catch(_) {if(runId===activeRefresh){show("inspection","Sentetik denetim kullanılamıyor; erişim genişletilmez.");show("sources","");}}
}
async function db(runId){
  const output=$("states");
  try{
    const x=await json("/api/demo/task-status");
    if(runId!==activeRefresh)return;
    if(!x || x.mode!=="disposable-synthetic-only" || x.production_ready!==false ||
       x.task_details_available!==false || !Array.isArray(x.aggregate))throw Error("unexpected_data");
    const allowed=new Set(["CREATED","PLANNED","APPROVAL_PENDING","RUNNING","VERIFYING","SUCCEEDED","FAILED","CANCELLED"]);
    const seen=new Set();
    if(x.aggregate.length>8 || x.aggregate.some(s=>{
      if(!s || !allowed.has(s.state) || seen.has(s.state) ||
         !Number.isSafeInteger(s.count) || s.count<0)return true;
      seen.add(s.state);return false;
    }))throw Error("unexpected_state");
    for(const entry of x.aggregate){
      const li=document.createElement("li");
      li.textContent=entry.state+": "+entry.count;
      output.appendChild(li);
    }
    show("db-status","Yalnızca geçici test veritabanı: toplu durum sayıları. Kullanıcı ve görev ayrıntısı gösterilmez.");
  }catch(_){
    if(runId!==activeRefresh)return;
    output.replaceChildren();
    show("db-status","PostgreSQL görünümü KAPALI / ERİŞİLEMİYOR. Kimlik ve yetki olmadan gerçek görev okunmaz.");
  }
}
async function refresh(){
  // Clear stale state immediately. Only the most recent refresh may write data.
  const runId=++activeRefresh;
  for(const id of ["health","inspection","db-status"])show(id,"Güncelleniyor…");
  show("sources","");$("states").replaceChildren();
  await Promise.all([health(runId),inspection(runId),db(runId)]);
}
$("refresh").addEventListener("click",refresh);
refresh();
