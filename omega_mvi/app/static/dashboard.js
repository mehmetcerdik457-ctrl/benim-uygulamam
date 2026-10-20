"use strict";
const $=id=>document.getElementById(id);
const show=(id,value)=>{const node=$(id);if(node)node.textContent=value};
// UI-only preferences. No cookies, localStorage, account data, or external requests.
const messages={
  tr:{
    intro:"Türkçe güvenli müfettiş — doğrulanmamış üretim işlevleri kapalıdır.",
    languageButton:"English",themeButton:"Açık temayı kullan",preferencesLabel:"Görünüm tercihleri",healthTitle:"Canlı sağlık denetimi",
    refreshButton:"Yalnızca durumları yenile",inspectionTitle:"Sentetik denetim modülleri",
    sourceIndexTitle:"Gerçek public kod indeksi",
    sourceIndexChecking:"Yalnızca izinli public kaynaklar yeniden doğrulanıyor…",
    sourceIndexFailure:"Public kaynak indeksi DOĞRULANAMADI / KAPALI.",
    sourceIndexSummary:(n,c)=>"Gerçek public indeks: "+n+" izinli Python dosyası, "+c+" sembol. YALNIZCA PUBLIC • KABUL EDİLMEDİ • Yürütme KAPALI.",
    databaseTitle:"PostgreSQL salt-okunur görünüm",securityTitle:"Güvenlik sınırları",
    executionDisabled:"Yürütme: KAPALI",identityMissing:"Gerçek kullanıcı kimliği ve tek kullanımlık onay yok.",
    sourcesSynthetic:"Veri kaynakları: SİMÜLASYON",sourcesUnlinked:"GitHub, RAG ve yerel model gerçek hesaba bağlanmıyor.",
    mviTitle:"MVI bileşenleri",mviDatabase:"PostgreSQL kayıtları yalnızca geçici sentinelli CI veritabanında sınandı.",
    mviApproval:"İnsan onayı: varsayılan RET. Yerel model: deterministik sahte adaptör.",
    productionNotAccepted:"Üretime hazırlık: KABUL EDİLMEDİ",
    footerNotice:"Dış CDN, üçüncü taraf betik, kullanıcı verisi veya bağlantı anahtarı yüklenmez.",
    gatesTitle:"Üretim ekranları — henüz kullanılamıyor",
    gatesIntro:"Kimlik ve kaynak yetkisi doğrulanmadığından aşağıdaki ekranlar gerçek veri göstermez.",
    inventoryDemoTitle:"73 · Sentetik envanter örneği",
    inventoryDemoNotice:"Yalnızca sabit, çevrimdışı test deposu; gerçek hesap veya klasörler taranmaz.",
    inventoryFilterLabel:"Kaynak türüne göre filtrele",
    inventoryTypeRepo:"Depolar",inventoryTypeFolder:"Klasörler",
    inventoryTypeService:"Servisler",inventoryTypeData:"Veri kaynakları",
    inventoryWaiting:"Sentetik depo verisi bekleniyor.",
    inventoryNoData:"Bu tür için yetkili gerçek veri yok; sentetik öğe de bulunmuyor.",
    inventoryUnavailable:"Sentetik envanter doğrulanamadı; hiçbir kaynak gösterilmez.",
    inventoryDemoResult:(name,stars,forks)=>"SADECE SENTETİK: "+name+" | Yıldız: "+stars+" | Fork: "+forks,
    inventoryLabel:"73 · Dijital envanter: KAPALI",
    inventoryReason:"Yetkili depo, klasör, servis ve veri kaynağı kaydı bağlanmadı.",
    searchLabel:"74 · Kaynaklı arama: KAPALI",
    searchReason:"Gerçek belge ACL, kaynak doğrulama ve silme denetimi yok.",
    secretsLabel:"77 · Secret referansları: KAPALI",
    secretsReason:"İzinli referans ve rotasyon metaverisi sunan güvenli uç yok; gizli değerler gösterilmez.",
    prLabel:"78 · PR denetimi: KAPALI",
    prReason:"Gerçek SHA'ya bağlı test, inceleme ve politika kararları doğrulanmadı.",
    authLabel:"79 · Kimlik ve oturum: KAPALI",
    authReason:"Gerçek IdP, MFA, RBAC veya doğrulanmış kullanıcı oturumu bulunmuyor.",
    updating:"Güncelleniyor…",
    healthFailure:"Yerel API erişilemiyor; hiçbir işlem başlatılmaz.",
    healthSuccess:"Servis: ok | Mod: mock | Üretim: KAPALI",
    inspectionFailure:"Sentetik denetim kullanılamıyor; erişim genişletilmez.",
    inspectionSummary:n=>"4 sentetik modül: GitHub envanteri, maskeleme, kaynaklı arama ve PR inceleme. Kaynak sayısı: "+n+". Karar yetkisi: YOK.",
    dbSuccess:"Yalnızca geçici test veritabanı: toplu durum sayıları. Kullanıcı ve görev ayrıntısı gösterilmez.",
    dbFailure:"PostgreSQL görünümü KAPALI / ERİŞİLEMİYOR. Kimlik ve yetki olmadan gerçek görev okunmaz."
  },
  en:{
    intro:"Turkish-first safe inspector — unverified production functionality is disabled.",
    languageButton:"Türkçe",themeButton:"Use light theme",preferencesLabel:"Display preferences",healthTitle:"Local health check",
    refreshButton:"Refresh status only",inspectionTitle:"Synthetic inspection modules",
    sourceIndexTitle:"Real public source code index",
    sourceIndexChecking:"Rechecking allowlisted public sources only…",
    sourceIndexFailure:"Public source index UNVERIFIED / DISABLED.",
    sourceIndexSummary:(n,c)=>"Real public index: "+n+" allowlisted Python files, "+c+" symbols. PUBLIC ONLY • NOT ACCEPTED • Execution DISABLED.",
    databaseTitle:"PostgreSQL read-only view",securityTitle:"Security boundaries",
    executionDisabled:"Execution: DISABLED",identityMissing:"No verified user identity or single-use approval.",
    sourcesSynthetic:"Data sources: SIMULATED",sourcesUnlinked:"GitHub, retrieval, and local model are not connected to a real account.",
    mviTitle:"MVI components",mviDatabase:"PostgreSQL records were tested only in a disposable CI database.",
    mviApproval:"Human approval: default DENY. Local model: deterministic mock adapter.",
    productionNotAccepted:"Production readiness: NOT ACCEPTED",
    footerNotice:"No external CDN, third-party script, personal data, or credential is loaded.",
    gatesTitle:"Production features — unavailable",
    gatesIntro:"Without verified identity and source permissions, these screens do not display real data.",
    inventoryDemoTitle:"73 · Synthetic inventory sample",
    inventoryDemoNotice:"Fixed offline test repository only; no real accounts or folders are scanned.",
    inventoryFilterLabel:"Filter by source type",
    inventoryTypeRepo:"Repositories",inventoryTypeFolder:"Folders",
    inventoryTypeService:"Services",inventoryTypeData:"Data sources",
    inventoryWaiting:"Waiting for synthetic repository data.",
    inventoryNoData:"No authorized live data or synthetic entry for this source type.",
    inventoryUnavailable:"Synthetic inventory could not be validated; no source is displayed.",
    inventoryDemoResult:(name,stars,forks)=>"SYNTHETIC ONLY: "+name+" | Stars: "+stars+" | Forks: "+forks,
    inventoryLabel:"73 · Digital inventory: DISABLED",
    inventoryReason:"No authorized repository, folder, service, or data source integration.",
    searchLabel:"74 · Cited search: DISABLED",
    searchReason:"No real-document ACL, citation verification, or deletion controls.",
    secretsLabel:"77 · Secret references: DISABLED",
    secretsReason:"No secure reference and rotation-metadata endpoint; secret values are never displayed.",
    prLabel:"78 · PR audit: DISABLED",
    prReason:"Actual SHA-bound checks, reviews, and policy decisions are unverified.",
    authLabel:"79 · Identity and sessions: DISABLED",
    authReason:"No real IdP, MFA, RBAC, or authenticated owner session.",
    updating:"Updating…",
    healthFailure:"Local API unavailable; no operation will start.",
    healthSuccess:"Service: ok | Mode: mock | Production: DISABLED",
    inspectionFailure:"Synthetic inspection unavailable; no access will be granted.",
    inspectionSummary:n=>"4 synthetic modules: GitHub inventory, redaction, cited retrieval, and PR review. Source count: "+n+". Decision authority: NONE.",
    dbSuccess:"Disposable test database only: aggregate state counts. User and task details are not available.",
    dbFailure:"PostgreSQL view DISABLED / UNAVAILABLE. No real tasks are read without verified identity."
  }
};
let language="tr", theme="dark";
const tr=(key,...args)=>{const value=messages[language][key];return typeof value==="function"?value(...args):value;};
function translateStatic(){
  document.documentElement?.setAttribute?.("lang",language);
  for(const node of document.querySelectorAll?.("[data-i18n]")??[]){
    const key=node.getAttribute("data-i18n");
    if(Object.prototype.hasOwnProperty.call(messages[language],key))node.textContent=tr(key);
  }
  for(const node of document.querySelectorAll?.("[data-i18n-aria-label]")??[]){
    const key=node.getAttribute("data-i18n-aria-label");
    if(Object.prototype.hasOwnProperty.call(messages[language],key))node.setAttribute?.("aria-label",tr(key));
  }
  const langButton=$("lang-toggle");
  langButton?.setAttribute?.("aria-label",language==="tr"?"Switch language to English":"Türkçe diline geç");
}
function applyTheme(){
  document.documentElement?.setAttribute?.("data-theme",theme);
  const button=$("theme-toggle");
  if(button){
    button.textContent=tr("themeButton");
    button.setAttribute?.("aria-pressed",String(theme==="light"));
  }
}

async function json(path){
  const res=await fetch(path,{method:"GET",cache:"no-store",credentials:"omit",redirect:"error"});
  if(!res.ok)throw Error("local_demo_unavailable");
  return await res.json();
}
// Fixture-only inventory renderer. Real inventory requires server-verified owner ACL/RBAC.
let demoInventory=null;
function validateFixtureInventory(value){
  if(!value || typeof value!=="object" || Array.isArray(value))return null;
  const expected=["counts","description","name","repository","visibility"].sort().join(",");
  if(Object.keys(value).sort().join(",")!==expected ||
     value.repository!=="mehmetcerdik457-ctrl/benim-uygulamam" ||
     value.name!=="benim-uygulamam" || value.visibility!=="public" ||
     value.description!=="Synthetic offline repository fixture")return null;
  const counts=value.counts;
  if(!counts || typeof counts!=="object" || Array.isArray(counts) ||
     Object.keys(counts).sort().join(",")!=="forks,open_issues,stars,watchers" ||
     Object.values(counts).some(n=>!Number.isSafeInteger(n)||n<0))return null;
  return {repository:value.repository,stars:counts.stars,forks:counts.forks};
}
function renderInventory(){
  const output=$("inventory-items");
  if(!output)return;
  output.replaceChildren();
  const type=$("inventory-filter")?.value;
  if(!["repository","folder","service","data_source"].includes(type)){
    show("inventory-status",tr("inventoryUnavailable"));return;
  }
  if(!demoInventory){
    show("inventory-status",tr("inventoryUnavailable"));return;
  }
  if(type!=="repository"){
    show("inventory-status",tr("inventoryNoData"));return;
  }
  const li=document.createElement("li");
  li.textContent=tr("inventoryDemoResult",demoInventory.repository,demoInventory.stars,demoInventory.forks);
  output.appendChild(li);
  show("inventory-status",tr("inventoryDemoNotice"));
}

let activeRefresh=0;
async function health(runId){
  try {
    const x=await json("/api/health");
    if(runId!==activeRefresh)return;
    if(!x || x.production_ready!==false || x.mode!=="mock" ||
       x.service!=="omega-mvi-demo" || x.status!=="ok")throw Error("unexpected_mode");
    show("health",tr("healthSuccess"));
  } catch(_) {if(runId===activeRefresh)show("health",tr("healthFailure"));}
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
    show("inspection",tr("inspectionSummary",sources.length));
    show("sources",sources.map(s=>s.ref).join(" | "));
    demoInventory=validateFixtureInventory(x.repository);
    renderInventory();
  } catch(_) {if(runId===activeRefresh){show("inspection",tr("inspectionFailure"));show("sources","");demoInventory=null;renderInventory();}}
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
let publicSourceGeneration=0;
async function publicSources(){
  // An older slower response must never replace newer source bytes or failure.
  const generation=++publicSourceGeneration;
  show("source-index",tr("sourceIndexChecking"));
  show("source-index-detail","");
  try {
    const raw=await json("/api/demo/source-index");
    if(generation!==publicSourceGeneration)return;
    const index=validatePublicSourceIndex(raw);
    if(!index)throw Error("invalid_public_source_index");
    show("source-index",tr("sourceIndexSummary",index.files.length,index.symbol_count));
    show("source-index-detail",index.files.map(f=>f.path+
      " — SHA-256: "+f.sha256.slice(0,12)+"…").join(" | "));
  } catch(_) {
    if(generation!==publicSourceGeneration)return;
    show("source-index",tr("sourceIndexFailure"));
    show("source-index-detail","");
  }
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
    show("db-status",tr("dbSuccess"));
  }catch(_){
    if(runId!==activeRefresh)return;
    output.replaceChildren();
    show("db-status",tr("dbFailure"));
  }
}
async function refresh(){
  // Clear stale state immediately. Only the most recent refresh may write data.
  const runId=++activeRefresh;
  for(const id of ["health","inspection","db-status"])show(id,tr("updating"));
  show("sources","");$("states").replaceChildren();
  demoInventory=null;show("inventory-status",tr("inventoryWaiting"));
  $("inventory-items")?.replaceChildren?.();
  await Promise.all([health(runId),inspection(runId),publicSources(),db(runId)]);
}
$("refresh").addEventListener("click",refresh);
$("inventory-filter")?.addEventListener?.("change",renderInventory);
$("lang-toggle")?.addEventListener?.("click",()=>{
  language=language==="tr"?"en":"tr";
  translateStatic();applyTheme();refresh();
});
$("theme-toggle")?.addEventListener?.("click",()=>{theme=theme==="dark"?"light":"dark";applyTheme();});
translateStatic();applyTheme();refresh();
