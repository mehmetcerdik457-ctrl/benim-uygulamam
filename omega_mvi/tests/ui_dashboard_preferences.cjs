"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,"..","app","static","dashboard.js"),"utf8");

function makeNode(attributes={}){
  const events={};
  return {
    attributes:{...attributes}, textContent:"", children:[],
    getAttribute(name){return this.attributes[name]??null;},
    setAttribute(name,value){this.attributes[name]=String(value);},
    addEventListener(event,callback){events[event]=callback;},
    click(){assert.ok(events.click,"click handler missing");return events.click();},
    replaceChildren(){this.children=[];},
    appendChild(element){this.children.push(element);}
  };
}
function fixture(){
  const ids=["refresh","health","inspection","sources","db-status","states","lang-toggle","theme-toggle"];
  const elements=new Map(ids.map(id=>[id,makeNode()]));
  const keys=[
    "intro","languageButton","themeButton","healthTitle","refreshButton","inspectionTitle",
    "databaseTitle","securityTitle","executionDisabled","identityMissing",
    "sourcesSynthetic","sourcesUnlinked","mviTitle","mviDatabase","mviApproval",
    "productionNotAccepted","footerNotice","gatesTitle","gatesIntro","inventoryLabel",
    "inventoryReason","searchLabel","searchReason","secretsLabel","secretsReason",
    "prLabel","prReason","authLabel","authReason"
  ];
  const labeled=keys.map(key=>makeNode({"data-i18n":key}));
  const group=makeNode({"data-i18n-aria-label":"preferencesLabel"});
  const root=makeNode();
  const calls=[];
  const body={
    mode:"synthetic_offline_only",authority:"none",production_ready:false,redaction_applied:true,
    sources:[{ref:"synthetic://omega-fixtures/provenance.md#citations",score:2}]
  };
  const payloads={
    "/api/health":{service:"omega-mvi-demo",status:"ok",mode:"mock",production_ready:false},
    "/api/demo/inspection":body,
    "/api/demo/task-status":{mode:"disposable-synthetic-only",
      task_details_available:false,production_ready:false,aggregate:[{state:"CREATED",count:1}]}
  };
  const context=vm.createContext({
    document:{
      documentElement:root,
      getElementById(id){return elements.get(id)||null;},
      querySelectorAll(selector){
        if(selector==="[data-i18n]")return labeled;
        if(selector==="[data-i18n-aria-label]")return [group];
        throw new Error("unexpected selector");
      },
      createElement(tag){assert.equal(tag,"li");return makeNode();}
    },
    fetch:async (url,options)=>{
      calls.push({url,options});
      assert.ok(Object.hasOwn(payloads,url),"unexpected API call: "+url);
      return {ok:true,json:async()=>payloads[url]};
    }
  });
  vm.runInContext(source,context,{timeout:1000});
  const textFor=key=>labeled.find(x=>x.getAttribute("data-i18n")===key).textContent;
  return {context,elements,root,group,calls,textFor};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test("English language changes the entire read-only disclosure and live status",async()=>{
  const f=fixture();
  await f.context.refresh();
  assert.equal(f.root.getAttribute("lang"),"tr");
  assert.match(f.textFor("secretsReason"),/gizli değerler/);
  assert.match(f.elements.get("health").textContent,/Üretim: KAPALI/);
  f.elements.get("lang-toggle").click();
  await flush();
  assert.equal(f.root.getAttribute("lang"),"en");
  assert.equal(f.textFor("languageButton"),"Türkçe");
  assert.match(f.textFor("searchReason"),/citation verification/);
  assert.match(f.textFor("secretsReason"),/secret values are never displayed/);
  assert.match(f.textFor("prReason"),/SHA-bound/);
  assert.match(f.textFor("authReason"),/No real IdP/);
  assert.equal(f.group.getAttribute("aria-label"),"Display preferences");
  assert.match(f.elements.get("health").textContent,/Production: DISABLED/);
  assert.match(f.elements.get("inspection").textContent,/synthetic modules/);
  assert.match(f.elements.get("db-status").textContent,/Disposable test database/);
  f.elements.get("lang-toggle").click();
  await flush();
  assert.equal(f.root.getAttribute("lang"),"tr");
  assert.match(f.textFor("authReason"),/Kimlik|IdP/);
});

test("theme is a stable accessible toggle and never persists preferences",async()=>{
  const f=fixture();
  assert.equal(f.root.getAttribute("data-theme"),"dark");
  assert.equal(f.elements.get("theme-toggle").getAttribute("aria-pressed"),"false");
  const label=f.elements.get("theme-toggle").textContent;
  f.elements.get("theme-toggle").click();
  assert.equal(f.root.getAttribute("data-theme"),"light");
  assert.equal(f.elements.get("theme-toggle").getAttribute("aria-pressed"),"true");
  assert.equal(f.elements.get("theme-toggle").textContent,label);
  f.elements.get("theme-toggle").click();
  assert.equal(f.root.getAttribute("data-theme"),"dark");
  assert.equal(f.elements.get("theme-toggle").getAttribute("aria-pressed"),"false");
});

test("UI requests only synthetic GET endpoints with no credentials",async()=>{
  const f=fixture();
  await f.context.refresh();
  f.elements.get("theme-toggle").click();
  f.elements.get("lang-toggle").click();
  await flush();
  assert.ok(f.calls.length>=6);
  for(const {url,options} of f.calls){
    assert.ok(["/api/health","/api/demo/inspection","/api/demo/task-status"].includes(url));
    assert.equal(options.method,"GET");
    assert.equal(options.credentials,"omit");
    assert.equal(options.cache,"no-store");
    assert.equal(options.redirect,"error");
  }
});
