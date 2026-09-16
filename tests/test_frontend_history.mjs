import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.handlers = {}; this.attributes = {};
    this.className = ""; this.value = ""; this.open = false; this.disabled = false;
    this.classList = { toggle: (name, on) => { this.attributes[`class-${name}`] = on; } };
  }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return this.text || ""; }
  append(...children) { for (const child of children) { child.remove(); child.parent = this; this.children.push(child); } }
  get parentElement() { return this.parent; }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, handler) { (this.handlers[name] ||= []).push(handler); }
  async fire(name) { for (const handler of this.handlers[name] || []) await handler({ target: this }); }
  click() { if (!this.disabled) return this.fire("click"); }
  showModal() { this.open = true; }
  close() { this.open = false; this.fire("close"); }
  focus() { this.focused = true; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((child) => child !== this); }
}
const body = new Element("body"), head = new Element("head");
const find = (root, match) => match(root) ? root : root.children.map((child) => find(child, match)).find(Boolean);
globalThis.document = { body, head, hidden: false, createElement: (tag) => new Element(tag),
  getElementById: (id) => find(body, (node) => node.id === id) || find(head, (node) => node.id === id) };
const intervals = new Set(), timeouts = new Set();
globalThis.setInterval = (callback) => { intervals.add(callback); return callback; };
globalThis.clearInterval = (callback) => intervals.delete(callback);
globalThis.setTimeout = (callback) => { timeouts.add(callback); return callback; };
globalThis.clearTimeout = (callback) => timeouts.delete(callback);
const settle = async () => { for (let index = 0; index < 12; index++) await Promise.resolve(); };
const record = { id: "1".padStart(32, "0"), model: "gpt-image-2", prompt: "<script>literal prompt</script>",
  created_at: "2026-09-16T10:00:00Z", params: { size: "auto" }, progress: 100, state: "success",
  image_count: 2, images: [{ index: 0, width: 24, height: 12 }, { index: 1, width: 12, height: 24 }], error: "" };
const requests = [], apiListeners = {};
let fail = false, locale = "zh-CN", extension, materialOptions, refreshMaterialCount = 0;
let promptOpenCount = 0;
globalThis.window = { MengBaoPromptOrganizerOpen() {
  promptOpenCount++;
  const panel = new Element("section"); panel.id = "wang-prompt-panel"; panel.draft = "user draft"; body.append(panel);
} };
globalThis.__historyApi = {
  addEventListener(name, handler) { apiListeners[name] = handler; },
  async fetchApi(path) {
    requests.push(path);
    if (fail) return Response.json({ error: { message: "HTTP 503: Service Unavailable" } }, { status: 503 });
    const query = new URL(path, "http://localhost").searchParams;
    return Response.json({ items: query.get("query") ? [] : [record], total: query.get("query") ? 0 : 1,
      counts: { success: 1, running: 0, partial: 0, failed: 0 } });
  },
};
globalThis.__historyApp = { graph: { add(node) { this.lastNode = node; }, setDirtyCanvas() {} },
  canvas: { ds: { scale: 1, offset: [0, 0] } },
  ui: { settings: { getSettingValue: () => locale, settingsLookup: { "Comfy.Locale": { onChange() {} } } } },
  registerExtension(value) { extension = value; } };
globalThis.__historyMaterials = { openMaterialLibrary(options) {
  materialOptions = options;
  const dialog = new Element("dialog"); body.append(dialog); dialog.showModal();
  dialog.addEventListener("close", () => dialog.remove());
  return dialog;
},
  refreshMaterialDialogLocale() { refreshMaterialCount++; } };
globalThis.LiteGraph = { createNode: () => ({ widgets: [{ name: "image", value: "" }], onConfigure() { this.restored = true; } }) };
const asModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const read = (file) => readFileSync(new URL(`../web/js/${file}`, import.meta.url), "utf8");
const history = await import(asModule(read("history.js")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__historyApi;")
  .replace('new URL("./history.css", import.meta.url).href', JSON.stringify(new URL("../web/js/history.css", import.meta.url).href))));
globalThis.__historyFrontend = history;
const launchers = await import(asModule(read("library_launchers.js")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__historyApp;")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__historyApi;")
  .replace(/import \{ (.*?) \} from "\.\/history.js";/, "const { $1 } = globalThis.__historyFrontend;")
  .replace(/import \{ (.*?) \} from "\.\/material_library.js";/, "const { $1 } = globalThis.__historyMaterials;")));
await extension.setup();
launchers.ensureLibraryLaunchers();
const historyButton = document.getElementById("mengbao-history-fab");
const materialsButton = document.getElementById("mengbao-materials-fab");
const dock = document.getElementById("mengbao-library-dock");
assert.equal(body.children.length, 1, "Setup must not duplicate the shared dock");
assert.equal(dock.children.length, 3);
assert.equal(historyButton.parentElement, dock);
assert.equal(materialsButton.parentElement, dock);
const promptButton = document.getElementById("mengbao-prompts-fab");
assert.equal(promptButton.title, "萌宝AI·提示词库");
await promptButton.click(); await promptButton.click();
assert.equal(promptOpenCount, 1, "Opening an existing prompt panel must preserve its draft");
assert.equal(historyButton.title, "萌宝AI·历史记录");
assert.match(materialsButton.title, /素材库/);
await materialsButton.click();
assert.equal(materialOptions.language(), "zh");
materialOptions.onSelect({ id: "chosen-material" });
assert.equal(__historyApp.graph.lastNode.widgets[0].value, "mengbao-material:chosen-material");
assert.equal(__historyApp.graph.lastNode.restored, true);
await historyButton.click(); await settle();
const dialog = body.children.find((node) => node.tagName === "DIALOG");
assert.equal(dialog.open, true);
assert.equal(dialog.children[0].children[0].textContent, "萌宝AI·历史记录");
assert.equal(history.openHistory({ language: launchers.currentLanguage }), dialog);
assert.equal(intervals.size, 1);
assert.equal(dock.parentElement, dialog, "Dock must remain interactive inside the native modal");
const grid = dialog.children[3];
assert.equal(grid.children.length, 1);
assert.equal(grid.children[0].children[1].children[2].textContent, record.prompt, "Prompts must render as text, never HTML");
await grid.children[0].children[0].click();
let details = body.children.filter((node) => node.tagName === "DIALOG").at(-1);
assert.equal(details.open, true);
const downloads = details.children[1].children[1];
assert.equal(downloads.children.length, 2);
assert.match(downloads.children[1].children[1].href, /\/1\?download=1$/);
assert.match(downloads.children[0].children[0].children[0].src, /thumbnail=1/);
details.close();
await dialog.children[2].children[4].click(); await settle();
assert.match(requests.at(-1), /state=failed/);
const search = dialog.children[1].children[0];
search.value = "missing"; await search.fire("input");
for (const timer of timeouts) { timeouts.delete(timer); await timer(); } await settle();
assert.match(requests.at(-1), /query=missing/);
assert.equal(grid.children[0].textContent, "暂无匹配记录");
const auto = dialog.children[1].children[2].children[0];
auto.checked = false; await auto.fire("change");
const countBefore = requests.length;
apiListeners.executed({ detail: { output: { mengbao_balance_refresh: [true] } } });
for (const timer of intervals) await timer(); await settle();
assert.equal(requests.length, countBefore, "Auto refresh disabled must suppress timers and execution refresh");
auto.checked = true; fail = true; await auto.fire("change"); await settle();
assert.equal(dialog.children[4].textContent, "HTTP 503: Service Unavailable");
fail = false;
locale = "en"; __historyApp.ui.settings.settingsLookup["Comfy.Locale"].onChange();
for (const timer of timeouts) { timeouts.delete(timer); await timer(); } await settle();
assert.equal(historyButton.title, "MengBao AI · History");
assert.equal(dialog.children[0].children[0].textContent, "MengBao AI · History");
assert.ok(refreshMaterialCount > 0);
locale = "fr"; assert.equal(launchers.currentLanguage(), "en");
locale = "zh-TW"; assert.equal(launchers.currentLanguage(), "zh");
assert.equal(history.historyLabels("zh").success, "已完成");
await materialsButton.click(); await settle();
assert.equal(dialog.open, false, "Switching libraries closes the previous modal");
assert.equal(intervals.size, 0);
assert.equal(dock.parentElement.tagName, "DIALOG");
await historyButton.click(); await settle();
assert.equal(intervals.size, 1);
await promptButton.click(); await settle();
assert.equal(promptOpenCount, 1);
await settle();
assert.equal(dock.parentElement, body);
assert.equal(document.getElementById("wang-prompt-panel").draft, "user draft");
assert.equal(intervals.size, 0);
assert.equal(timeouts.size, 0);
assert.equal(body.children.filter((node) => node.tagName === "DIALOG").length, 0);
const css = read("history.css");
assert.match(css, /grid-auto-rows:\s*max-content/);
assert.match(css, /\.mengbao-library-dock\s*\{/);
assert.match(css, /flex-direction:\s*row/);
const promptSource = read("prompt_organizer.js");
assert.match(promptSource, /getElementById\("mengbao-library-dock"\)/);
console.log("History persistence UI, filters, errors, downloads, locale, launchers and timer cleanup tests passed.");
