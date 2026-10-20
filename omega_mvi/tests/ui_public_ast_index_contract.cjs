"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");

const fixture=JSON.parse(fs.readFileSync(process.env.OMEGA_PUBLIC_AST_FIXTURE,"utf8"));
const source=fs.readFileSync(path.join(__dirname,"..","app","static","dashboard.js"),"utf8");
const copy=()=>structuredClone(fixture);
const element=()=>({
  textContent:"",children:[],addEventListener(){},
  replaceChildren(){this.children=[]},
  appendChild(node){this.children.push(node)}
});
function context(payload=fixture){
  const els=new Map(["refresh","health","inspection","sources","source-index",
     "source-index-detail","db-status","states"].map(k=>[k,element()]));
  const requestLog=[];
  const ctx=vm.createContext({
    document:{
      getElementById(id){return els.get(id)||null},
      createElement(){return element()}
    },
    fetch:async(url,config)=>{
      requestLog.push({url,config});
      const result=url==="/api/demo/source-index"?payload:
        url==="/api/health"?{service:"omega-mvi-demo",status:"ok",mode:"mock",production_ready:false}:
        url==="/api/demo/inspection"?{mode:"synthetic_offline_only",production_ready:false,authority:"none",redaction_applied:true,sources:[]}:
        {mode:"disposable-synthetic-only",production_ready:false,task_details_available:false,aggregate:[]};
      return {ok:true,json:async()=>result};
    }
  });
  vm.runInContext(source,ctx,{timeout:1000});
  return {ctx,els,requestLog};
}
test("actual installed source AST index is accepted without altering bytes",()=>{
  const {ctx}=context();
  assert.strictEqual(ctx.validatePublicSourceIndex(fixture),fixture);
  assert.equal(fixture.files.length,5);
  assert.equal(fixture.symbol_count,fixture.files.reduce((sum,f)=>sum+f.symbols.length,0));
});
test("strict file manifest denies traversal, repeats and unknown files",()=>{
  for(const change of [
    x=>x.files[0].path="../private/.env",
    x=>x.files[0].path="omega_mvi/inspection/../../backend/server.py",
    x=>x.files[0].path=x.files[1].path,
    x=>x.files[0].path="omega_mvi/inspection/private_keys.py",
    x=>x.files[0].path="omega_mvi/inspection/<img src=x>",
    x=>x.files.pop(),
    x=>x.files[0].credential="fake-bearer",
    x=>x.files[0]=null,
    x=>x.files.push(x.files[0]),
  ]){
    const x=copy();change(x);
    assert.equal(context().ctx.validatePublicSourceIndex(x),null);
  }
});
test("hash, size, counts, file fields and source provenance fail closed",()=>{
  for(const change of [
    x=>x.files[0].sha256="f".repeat(63),
    x=>x.files[0].sha256="F".repeat(64),
    x=>x.files[0].byte_length=131073,
    x=>x.files[0].byte_length=-1,
    x=>x.files[0].byte_length="123",
    x=>x.files[0].dynamic_calls_unresolved=-1,
    x=>x.files[0].symbols[0].kind="admin",
    x=>x.files[0].symbols[0].line=0,
    x=>x.files[0].symbols[0].symbol="<svg>",
    x=>x.files[0].symbols[0].source="private",
    x=>x.files[0].imports.push("<script>"),
    x=>x.files[0].call_edges.push({from:"a",to:"b",secret:"x"}),
    x=>x.files[0].call_edges.push({from:"<script>",to:"exec"}),
    x=>x.files[0].symbols=[],
    x=>x.symbol_count+=1,
    x=>x.files_indexed=4,
    x=>x.extra="injected",
    x=>x.authenticated_owner=true,
    x=>x.production_ready=true,
    x=>x.acceptance="ACCEPTED",
    x=>x.read_only=false,
    x=>x.external_calls=true,
    x=>x.input="user supplied file",
    x=>x.mode="real-private-source-ast",
  ]){
    const x=copy();change(x);
    assert.equal(context().ctx.validatePublicSourceIndex(x),null);
  }
});
test("good public source index renders distinctly as NOT ACCEPTED",async()=>{
  const {ctx,els,requestLog}=context();
  await ctx.publicSources();
  assert.match(els.get("source-index").textContent,/KABUL EDİLMEDİ/);
  assert.match(els.get("source-index").textContent,/5 izinli Python dosyası/);
  assert.match(els.get("source-index-detail").textContent,/SHA-256/);
  assert.doesNotMatch(els.get("source-index-detail").textContent,/PRIVATE KEY/);
  assert.ok(requestLog.some(x=>x.url==="/api/demo/source-index"&&
    x.config.credentials==="omit"&&x.config.method==="GET"));
});
test("malicious index never appears in browser and clears stale details",async()=>{
  const x=copy();x.files[0].path="omega_mvi/inspection/<img src=x onerror=alert(1)>";
  const {ctx,els}=context(x);
  els.get("source-index-detail").textContent="OLD_TRUSTED_DATA";
  await ctx.publicSources();
  assert.match(els.get("source-index").textContent,/DOĞRULANAMADI/);
  assert.equal(els.get("source-index-detail").textContent,"");
  assert.ok(!source.includes("innerHTML"));
});
