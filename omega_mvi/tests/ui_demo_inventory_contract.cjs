"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(path.join(__dirname,"..","app","static","dashboard.js"),"utf8");

const repository=()=>({
  repository:"mehmetcerdik457-ctrl/benim-uygulamam",
  name:"benim-uygulamam",visibility:"public",
  description:"Synthetic offline repository fixture",
  counts:{stars:0,forks:0,watchers:0,open_issues:0}
});
const inspection=()=>({
  mode:"synthetic_offline_only",authority:"none",production_ready:false,
  redaction_applied:true,repository:repository(),
  sources:[{ref:"synthetic://omega-fixtures/provenance.md#citations",score:2}]
});

function makeNode(value){
  const handlers={};
  return {value,textContent:"",attributes:{},children:[],
    getAttribute(key){return this.attributes[key]||null;},
    setAttribute(key,v){this.attributes[key]=String(v);},
    addEventListener(kind,cb){handlers[kind]=cb;},
    change(){assert.ok(handlers.change);handlers.change();},
    click(){assert.ok(handlers.click);handlers.click();},
    replaceChildren(){this.children=[];},
    appendChild(child){this.children.push(child);}
  };
}

function setup(){
  const ids=["refresh","lang-toggle","theme-toggle","health","inspection","sources",
    "states","db-status","inventory-status","inventory-items","inventory-filter"];
  const nodes=new Map(ids.map(id=>[id,makeNode(id==="inventory-filter"?"repository":undefined)]));
  const requests=[];
  const payloads={
    "/api/health":{service:"omega-mvi-demo",status:"ok",mode:"mock",production_ready:false},
    "/api/demo/inspection":inspection(),
    "/api/demo/source-index":{},
    "/api/demo/task-status":{mode:"disposable-synthetic-only",
      task_details_available:false,production_ready:false,aggregate:[]}
  };
  const context=vm.createContext({
    document:{
      documentElement:makeNode(),
      getElementById(id){return nodes.get(id)||null;},
      querySelectorAll(){return [];},
      createElement(tag){assert.equal(tag,"li");return makeNode();}
    },
    fetch:async(url,opts)=>{
      requests.push({url,opts});
      assert.ok(Object.hasOwn(payloads,url));
      return {ok:true,json:async()=>payloads[url]};
    }
  });
  vm.runInContext(source,context,{timeout:1000});
  return {context,nodes,requests,payloads,
    items(){return nodes.get("inventory-items").children.map(v=>v.textContent);},
    status(){return nodes.get("inventory-status").textContent;},
    select(kind){nodes.get("inventory-filter").value=kind;nodes.get("inventory-filter").change();}
  };
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test("renders only exact offline repository with filtered type and no real account request",async()=>{
  const e=setup();await e.context.refresh();
  assert.deepEqual(e.items(),["SADECE SENTETİK: mehmetcerdik457-ctrl/benim-uygulamam | Yıldız: 0 | Fork: 0"]);
  assert.match(e.status(),/Yalnızca sabit/);
  for(const kind of ["folder","service","data_source"]){
    e.select(kind);
    assert.deepEqual(e.items(),[]);
    assert.match(e.status(),/yetkili gerçek veri yok/);
  }
  e.select("repository");
  assert.equal(e.items().length,1);
  for(const {url,opts} of e.requests){
    assert.ok(["/api/health","/api/demo/inspection","/api/demo/source-index","/api/demo/task-status"].includes(url));
    assert.equal(opts.method,"GET");
    assert.equal(opts.credentials,"omit");
  }
});
test("rejects forged repository source metadata and never renders raw or secret fields",async()=>{
  const base=inspection();
  const mutators=[
    x=>x.repository.repository="other-user/private-data",
    x=>x.repository.name="<img src=x onerror=alert(1)>",
    x=>x.repository.visibility="private",
    x=>x.repository.description="Authorization: Bearer synthetic-malicious",
    x=>x.repository.counts.stars=-1,
    x=>x.repository.counts.forks="2",
    x=>x.repository.counts.token="synthetic-secret",
    x=>x.repository.private=true,
    x=>delete x.repository.counts,
    x=>x.repository=null
  ];
  for(const mutate of mutators){
    const e=setup();
    const x=structuredClone(base);mutate(x);
    e.payloads["/api/demo/inspection"]=x;
    await e.context.refresh();
    assert.deepEqual(e.items(),[]);
    assert.match(e.status(),/doğrulanamadı/);
    assert.ok(!e.status().includes("Bearer"));
    assert.match(e.nodes.get("inspection").textContent,/sentetik modül/);
  }
});
test("rejects unknown category even when synthetic repo is otherwise valid",async()=>{
  const e=setup();await e.context.refresh();
  e.select("secrets");assert.deepEqual(e.items(),[]);
  assert.match(e.status(),/doğrulanamadı/);
  e.select("repository");assert.equal(e.items().length,1);
});
test("English switch updates fixture indicator, and refresh invalidates stale inventory",async()=>{
  const e=setup();await e.context.refresh();
  e.nodes.get("lang-toggle").click();await tick();
  assert.match(e.items()[0],/^SYNTHETIC ONLY:/);
  e.select("folder");
  assert.match(e.status(),/No authorized live data/);
  e.select("repository");
  e.payloads["/api/demo/inspection"]={...inspection(),authority:"execute"};
  await e.context.refresh();
  assert.deepEqual(e.items(),[]);
  assert.match(e.nodes.get("inspection").textContent,/unavailable/);
  assert.match(e.status(),/could not be validated/);
});
