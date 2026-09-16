import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const extensions = [];
let locale = "zh-CN";
const api = new EventTarget();
const requests = [];
let saved = false;
let nextError = "";
api.fetchApi = async (url, options = {}) => {
  requests.push({ url, ...options });
  if (nextError) return { ok: false, status: 500, json: async () => ({ error: { message: nextError } }) };
  if (options.method === "POST") saved = true;
  if (options.method === "DELETE") saved = false;
  return { ok: true, json: async () => ({ saved }) };
};
const app = {
  graph: { _nodes: [], setDirtyCanvas() {} },
  ui: { settings: { getSettingValue: () => locale, settingsLookup: { "Comfy.Locale": { onChange() {} } } } },
  registerExtension(extension) { extensions.push(extension); },
};
globalThis.__mengBaoKeyTestApp = app;
globalThis.__mengBaoKeyTestApi = api;
let confirmClear = true;
globalThis.window = { confirm: () => confirmClear };
globalThis.document = {
  createElement() {
    return {
      style: {}, listeners: {}, children: [], value: "",
      setAttribute(name, value) { this[name] = value; },
      append(...children) { this.children.push(...children); },
      addEventListener(name, callback) { this.listeners[name] = callback; },
    };
  },
};
const localizationSource = readFileSync(new URL("../web/js/node_localization.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__mengBaoKeyTestApp;");
globalThis.__mengBaoKeyTestLocalization = await import(`data:text/javascript;base64,${Buffer.from(localizationSource).toString("base64")}`);
const source = readFileSync(new URL("../web/js/global_api_key.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__mengBaoKeyTestApp;")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__mengBaoKeyTestApi;")
  .replace('import { applyNodeLocalization, normalizeLanguage } from "./node_localization.js";',
    "const { applyNodeLocalization, normalizeLanguage } = globalThis.__mengBaoKeyTestLocalization;");
await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const extension = extensions.find(({ name }) => name === "MengBaoAI.global_api_key");
assert.ok(extension);
await extension.setup();
class Node {
  constructor() {
    this.type = "MengBaoGlobalAPIKey";
    this.widgets = [{ name: "api_key", value: "", options: {} }];
    this.outputs = [{ name: "status" }];
    this.size = [300, 100];
  }
  addDOMWidget(name, type, element, options) {
    const widget = { name, type, element, options };
    this.widgets.push(widget);
    return widget;
  }
  computeSize() { return [300, 160]; }
  setSize(size) { this.size = size; }
  setDirtyCanvas() {}
}
await extension.beforeRegisterNodeDef(Node, { name: "MengBaoGlobalAPIKey" });
const node = new Node();
app.graph._nodes.push(node);
node.onNodeCreated();
await node._mengBaoGlobalKeyStatusPromise;
const controls = node._mengBaoGlobalKeyControls;
const root = controls.widget.element;
const margin = controls.widget.options.margin ?? 10;
const availableHeight = controls.widget.options.getMinHeight() - 2 * margin;
const padding = String(root.style.padding).split(" ").map(parseFloat);
const requiredHeight = parseFloat(controls.input.style.height)
  + parseFloat(controls.saveButton.style.height || controls.saveButton.style.minHeight)
  + parseFloat(controls.status.style.height)
  + 2 * parseFloat(root.style.gap) + 2 * padding[0];
assert.ok(availableHeight >= requiredHeight,
  `Status text is clipped: ${availableHeight}px available, ${requiredHeight}px required`);
assert.equal(controls.status.style.flexShrink, "0");
assert.equal(controls.saveButton.style.whiteSpace, "nowrap");
assert.equal(controls.saveButton.title, controls.saveButton.textContent);
assert.equal(node.title, "萌宝AI全局API Key管理");
assert.equal(node.widgets[0].hidden, true);
assert.equal(controls.input.type, "password");
assert.equal(controls.saveButton.textContent, "保存全局API Key");
assert.equal(controls.clearButton.textContent, "清除全局API Key");
assert.equal(controls.clearButton.disabled, true);
assert.equal(controls.saveButton.disabled, true);
assert.equal(controls.widget.options.serialize, false);
controls.input.value = "test-secret";
controls.input.listeners.input();
assert.equal(controls.saveButton.disabled, false);
assert.equal(node.widgets[0].value, "");
assert.equal(await node.widgets[0].serializeValue(), "");
const events = [];
api.addEventListener("mengbao-api-key-changed", ({ detail }) => events.push(detail));
const saving = controls.saveButton.listeners.click();
assert.equal(controls.input.disabled, true);
assert.equal(controls.saveButton.disabled, true);
assert.equal(controls.saveButton.textContent, "正在保存...");
node.onExecuted({ saved: [false] });
assert.equal(controls.saveButton.disabled, true);
await saving;
assert.equal(JSON.parse(requests.at(-1).body).api_key, "test-secret");
assert.equal(controls.input.value, "");
assert.match(controls.status.textContent, /已保存/);
assert.equal(controls.clearButton.disabled, false);
assert.deepEqual(events.at(-1), { saved: true });
assert.ok(!controls.status.textContent.includes("test-secret"));
confirmClear = false;
const requestCount = requests.length;
await controls.clearButton.listeners.click();
assert.equal(requests.length, requestCount);
confirmClear = true;
await controls.clearButton.listeners.click();
assert.equal(requests.at(-1).method, "DELETE");
assert.match(controls.status.textContent, /已清除/);
assert.equal(controls.clearButton.disabled, true);
assert.deepEqual(events.at(-1), { saved: false });
locale = "en";
globalThis.__mengBaoKeyTestLocalization.applyNodeLocalization(node, "en");
assert.equal(node.title, "MengBao AI · Global API Key Manager");
assert.equal(controls.input["aria-label"], "API Key");
assert.equal(controls.saveButton.textContent, "Save Global API Key");
controls.input.value = "another-test-secret";
controls.input.listeners.input();
nextError = "Disk write failed";
await controls.saveButton.listeners.click();
assert.equal(controls.status.textContent, "Disk write failed");
assert.equal(controls.status.title, "Disk write failed");
assert.equal(controls.status.style.overflow, "hidden");
assert.equal(controls.input.value, "another-test-secret");
assert.equal(controls.input.disabled, false);
assert.equal(controls.saveButton.disabled, false);
node.onConfigure({ widgets_values: ["workflow-secret-must-not-be-restored"] });
await node._mengBaoGlobalKeyStatusPromise;
assert.equal(controls.input.value, "");
assert.equal(node.widgets[0].value, "");
assert.equal(node.widgets.length, 2);
nextError = "";
node.onExecuted({ saved: [true] });
assert.match(controls.status.textContent, /saved/);
node.onExecuted({ saved: [false] });
assert.match(controls.status.textContent, /not set/);
console.log("Global API key frontend tests passed.");
