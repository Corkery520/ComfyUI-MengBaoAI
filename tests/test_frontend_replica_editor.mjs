import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Element extends EventTarget {
  constructor(tagName) {
    super();
    this.tagName = tagName;
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.classList = { toggle() {} };
    this.isConnected = true;
  }
  append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  querySelectorAll(selector) {
    const selectors = selector.split(",").map(value => value.trim());
    return this.children.flatMap(child => [
      ...(selectors.includes(child.tagName) || (selectors.includes("[data-requires-images]") && child.dataset.requiresImages) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
  showModal() { this.open = true; }
  close() { this.open = false; this.dispatchEvent(new Event("close")); }
  remove() { this.isConnected = false; if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
  click() { if (!this.disabled) this.dispatchEvent(new Event("click")); }
}

globalThis.document = { body: new Element("body"), createElement: tag => new Element(tag) };
let disconnects = 0;
globalThis.ResizeObserver = class { observe() {} disconnect() { disconnects += 1; } };
const listeners = new Set(), requests = [], changes = [];
let fetchResponse = async () => ({ ok: true, json: async () => ({ saved: true }) });
globalThis.replicaEditorApi = {
  addEventListener(_name, listener) { listeners.add(listener); },
  removeEventListener(_name, listener) { listeners.delete(listener); },
  async fetchApi(path, options) { requests.push({ path, body: JSON.parse(options.body) }); return fetchResponse(); },
};
const dataModule = source => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const modelUrl = dataModule(readFileSync(new URL("../web/js/replica_model.js", import.meta.url), "utf8"));
const uploadUrl = dataModule("export function bindUploadTarget(){throw new Error('Unexpected upload binding');} export function isEditableTarget(){return false;}");
const materialUrl = dataModule("export function materialFileUrl(){} export function openMaterialLibrary(){} export function refreshMaterialDialogLocale(){}");
const source = readFileSync(new URL("../web/js/replica_editor.js", import.meta.url), "utf8")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.replicaEditorApi;")
  .replace('"./material_uploads.js"', JSON.stringify(uploadUrl))
  .replace('"./material_library.js"', JSON.stringify(materialUrl))
  .replace('"./replica_model.js"', JSON.stringify(modelUrl));
const editor = await import(dataModule(source));
const settle = () => new Promise(resolve => setImmediate(resolve));
async function open() {
  return editor.openReplicaEditor({
    record: { id: "a".repeat(32), source: { id: "source", width: 80, height: 60 } },
    draft: { analysis_id: "a".repeat(32), analysis: { composition: "Layout", elements: [] }, replacements: {}, confirmed: false },
    draftId: "b".repeat(32), language: () => "en", limit: () => 14,
    onChange: draft => changes.push(draft),
  });
}
function control(dialog, label) { return dialog.querySelectorAll("button").find(button => button.textContent === label); }

// 保存完成前不关闭，重复点击不重复提交；确认成功才更新节点并清理弹窗。
let resolveSave;
fetchResponse = () => new Promise(resolve => { resolveSave = resolve; });
const confirmed = await open();
control(confirmed.dialog, "Confirm Settings").click();
await settle();
assert.equal(confirmed.dialog.open, true);
assert.equal(control(confirmed.dialog, "Confirm Settings").disabled, true);
control(confirmed.dialog, "Confirm Settings").click();
assert.equal(requests.length, 1);
assert.equal(changes.length, 0);
resolveSave({ ok: true, json: async () => ({ saved: true }) });
await settle();
assert.equal(confirmed.dialog.open, false);
assert.equal(confirmed.dialog.isConnected, false);
assert.equal(changes.at(-1).confirmed, true);
assert.equal(listeners.size, 0);
assert.equal(disconnects, 1);
assert.equal(requests.length, 1);

fetchResponse = async () => ({ ok: true, json: async () => ({ saved: true }) });
const saved = await open();
control(saved.dialog, "Save Draft").click();
await settle();
assert.equal(saved.dialog.open, true);
assert.equal(changes.at(-1).confirmed, false);
saved.dialog.close();

for (const failure of [
  async () => ({ ok: false, status: 400, json: async () => ({ error: { message: "Confirm the position of element: Bottle" } }) }),
  async () => { throw new Error("Failed to fetch"); },
]) {
  fetchResponse = failure;
  const failed = await open();
  const previousChanges = changes.length;
  control(failed.dialog, "Confirm Settings").click();
  await settle();
  assert.equal(failed.dialog.open, true);
  assert.equal(control(failed.dialog, "Confirm Settings").disabled, false);
  assert.equal(changes.length, previousChanges);
  assert.match(failed.dialog.querySelectorAll("div").find(div => div.className === "replica-status").textContent, /Confirm the position|Failed to fetch/);
  failed.dialog.close();
}
assert.equal(listeners.size, 0);
console.log("Replica editor: confirmed save closes once; pending, draft save, validation and network failure keep the dialog open.");
