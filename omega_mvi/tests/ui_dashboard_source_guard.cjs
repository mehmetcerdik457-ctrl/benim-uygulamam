"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const dashboard = fs.readFileSync(
  path.join(__dirname, "..", "app", "static", "dashboard.js"), "utf8");
const provenance = "synthetic://omega-fixtures/provenance.md#citations";

function mock(payload, opts={}) {
  const elements = new Map();
  for (const id of ["refresh", "health", "inspection", "sources", "db-status", "states"]) {
    elements.set(id, {
      textContent: "", children: [],
      addEventListener() {},
      replaceChildren() { this.children = []; },
      appendChild(child) { this.children.push(child); }
    });
  }
  const document = {
    getElementById(id) { return elements.get(id) ?? null; },
    createElement() { return {textContent: ""}; }
  };
  const context = vm.createContext({document, fetch: async (url) => ({
    ok: true,
    json: async () => url === "/api/health"
      ? (opts.health ?? {service:"omega-mvi-demo", mode:"mock", status:"ok", production_ready:false})
      : url === "/api/demo/task-status"
        ? (opts.db ?? {mode:"disposable-synthetic-only", production_ready:false,
           task_details_available:false, aggregate:[{state:"CREATED",count:1}]})
        : payload
  })});
  vm.runInContext(dashboard, context, {timeout: 1000});
  return {context, elements};
}
const valid = () => ({mode:"synthetic_offline_only", authority:"none",
  production_ready:false, redaction_applied:true,
  sources:[{ref:provenance, score:2}]});

async function rendered(payload, opts={}) {
  const {context, elements} = mock(payload, opts);
  await context.refresh();
  return {
    inspection:elements.get("inspection").textContent,
    source:elements.get("sources").textContent,
    health:elements.get("health").textContent,
    dbStatus:elements.get("db-status").textContent,
    states:elements.get("states").children.map(x=>x.textContent)
  };
}

test("known fixture reference is explicitly synthetic", async () => {
  const result = await rendered(valid());
  assert.match(result.inspection, /sentetik modül/);
  assert.equal(result.source, provenance);
  assert.match(result.health, /Üretim: KAPALI/);
});

test("forged synthetic source is rejected rather than displayed", async () => {
  const data = valid();
  data.sources[0].ref = "synthetic://<img src=x onerror=alert(1)>";
  const result = await rendered(data);
  assert.match(result.inspection, /kullanılamıyor/);
  assert.equal(result.source, "");
});

test("unapproved URL, bad scores, repeated references, oversize and false authority deny", async () => {
  for (const mutate of [
    (d) => d.sources[0].ref = "https://outside.invalid/file",
    (d) => d.sources[0].score = "2",
    (d) => d.sources[0].score = -1,
    (d) => d.sources.push({...d.sources[0]}),
    (d) => d.sources = Array(6).fill({ref:provenance,score:1}),
    (d) => d.authority = "execute",
    (d) => d.production_ready = true
  ]) {
    const data = valid(); mutate(data);
    const result = await rendered(data);
    assert.match(result.inspection, /kullanılamıyor/);
    assert.equal(result.source, "");
  }
});

test("forged health status or service is never claimed as local health", async () => {
  for (const health of [
    {service:"outside-service", mode:"mock", status:"ok", production_ready:false},
    {service:"omega-mvi-demo", mode:"mock", status:"maintenance", production_ready:false},
    {service:"omega-mvi-demo", mode:"prod", status:"ok", production_ready:true}
  ]) {
    const result = await rendered(valid(), {health});
    assert.match(result.health, /API erişilemiyor/);
    assert.doesNotMatch(result.health, /Servis:/);
  }
});

test("duplicate aggregate states fail closed and cannot mislead queue", async () => {
  const db = {mode:"disposable-synthetic-only", production_ready:false,
    task_details_available:false, aggregate:[
      {state:"CREATED",count:2},{state:"CREATED",count:1000}]};
  const result = await rendered(valid(), {db});
  assert.match(result.dbStatus, /ERİŞİLEMİYOR/);
  assert.deepEqual(result.states, []);
});

test("stale out-of-order refresh response cannot replace newer visible data", async () => {
  const elements=new Map();
  for (const id of ["refresh","health","inspection","sources","db-status","states"]) {
    elements.set(id,{textContent:"", children:[],addEventListener(){},
      replaceChildren(){this.children=[]},appendChild(item){this.children.push(item)}});
  }
  const requests=[];
  const context=vm.createContext({
    document:{getElementById(id){return elements.get(id)},createElement(){return {textContent:""}}},
    fetch:(url)=>new Promise(resolve=>requests.push({url,resolve}))
  });
  vm.runInContext(dashboard,context,{timeout:1000}); // initial batch pending
  assert.equal(requests.length,4); // health, inspection, public AST, DB
  const newer=context.refresh();
  assert.equal(requests.length,8);
  const reply=(request,payload)=>request.resolve({ok:true,json:async()=>payload});
  const goodHealth={service:"omega-mvi-demo",mode:"mock",status:"ok",production_ready:false};
  const goodDb={mode:"disposable-synthetic-only",production_ready:false,
    task_details_available:false,aggregate:[{state:"CREATED",count:1}]};
  const goodInspection=valid();
  for(const r of requests.slice(4)){
    reply(r,r.url.includes("health")?goodHealth:r.url.includes("task-status")?goodDb:goodInspection);
  }
  await newer;
  assert.match(elements.get("health").textContent,/Üretim: KAPALI/);
  assert.equal(elements.get("sources").textContent,provenance);
  assert.deepEqual(elements.get("states").children.map(x=>x.textContent),["CREATED: 1"]);
  for(const r of requests.slice(0,4)){
    reply(r,r.url.includes("health")?{...goodHealth,status:"spoof"}:
      r.url.includes("task-status")?{...goodDb,aggregate:[{state:"FAILED",count:99}]}:
      {...goodInspection,sources:[{ref:"synthetic://forged",score:1}]});
  }
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(elements.get("health").textContent,/Üretim: KAPALI/);
  assert.equal(elements.get("sources").textContent,provenance);
  assert.deepEqual(elements.get("states").children.map(x=>x.textContent),["CREATED: 1"]);
});
