"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const dashboard = fs.readFileSync(
  path.join(__dirname, "..", "app", "static", "dashboard.js"), "utf8");
const provenance = "synthetic://omega-fixtures/provenance.md#citations";

function mock(payload) {
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
      ? {mode:"mock", status:"ok", production_ready:false}
      : url === "/api/demo/task-status"
        ? {mode:"disposable-synthetic-only", production_ready:false,
           task_details_available:false, aggregate:[{state:"CREATED",count:1}]}
        : payload
  })});
  vm.runInContext(dashboard, context, {timeout: 1000});
  return {context, elements};
}
const valid = () => ({mode:"synthetic_offline_only", authority:"none",
  production_ready:false, redaction_applied:true,
  sources:[{ref:provenance, score:2}]});

async function rendered(payload) {
  const {context, elements} = mock(payload);
  await context.refresh();
  return {
    inspection:elements.get("inspection").textContent,
    source:elements.get("sources").textContent,
    health:elements.get("health").textContent
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
