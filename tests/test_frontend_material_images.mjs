import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.handlers = {}; this.attributes = {};
    this.value = ""; this.textContent = ""; this.isConnected = true; this.disabled = false;
    this.classList = { toggle() {} };
  }
  append(...children) { this.children.push(...children); for (const child of children) child.parent = this; }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  set src(value) { this.setAttribute("src", value); }
  get src() { return this.getAttribute("src"); }
  addEventListener(name, handler) { (this.handlers[name] ||= []).push(handler); }
  removeEventListener(name, handler) { this.handlers[name] = (this.handlers[name] || []).filter((entry) => entry !== handler); }
  async fire(name, event = {}) { for (const handler of this.handlers[name] || []) await handler({ target: this, preventDefault() {}, ...event }); }
  click() { if (!this.disabled) return this.fire("click"); }
  getClientRects() { return this.hidden ? [] : [1]; }
  contains(target) { return this === target || this.children.some((child) => child.contains(target)); }
  showModal() { this.open = true; }
  close() { this.open = false; this.fire("close"); }
  remove() { this.isConnected = false; if (this.parent) this.parent.children = this.parent.children.filter((child) => child !== this); }
}
const body = new Element("body");
const documentHandlers = {};
globalThis.document = {
  body, head: new Element("head"), activeElement: null,
  createElement: (tag) => new Element(tag), getElementById: () => ({}),
  addEventListener(name, handler) { documentHandlers[name] = handler; },
  querySelector: () => body.children.find((element) => element.tagName === "DIALOG" && element.open) || null,
};
globalThis.window = { confirm: () => true, prompt: () => "新品" };
globalThis.createImageBitmap = async () => ({ width: 8, height: 4, close() {} });
let locale = "zh-CN", extension, nextId = 2, failUpload = false;
const firstId = "1".padStart(32, "0");
const items = new Map([[firstId, { id: firstId, name: "产品.png", category: "产品", favorite: false, width: 8, height: 4 }]]);
let categories = ["产品", "参考", "未分类"];
const requests = [];
globalThis.__materialApp = {
  graph: { _nodes: [], setDirtyCanvas() {} },
  ui: { settings: { getSettingValue: () => locale, settingsLookup: { "Comfy.Locale": { onChange() {} } } } },
  registerExtension(value) { extension = value; },
};
globalThis.__materialApi = { async fetchApi(path, options = {}) {
  requests.push({ path, options });
  let payload;
  if (path === "/upload/image") {
    if (failUpload) return Response.json({ error: { message: "Upload failed" } }, { status: 500 });
    payload = { name: options.body.get("image").name, subfolder: "mengbao", type: "input" };
  } else if (path.endsWith("/items")) payload = { items: [...items.values()], categories };
  else if (path.endsWith("/import")) {
    const id = String(nextId++).padStart(32, "0");
    payload = { id, name: options.body.get("image").name, category: options.body.get("category"), favorite: false, width: 8, height: 4 };
    items.set(id, payload);
  } else if (path.endsWith("/category")) {
    const data = JSON.parse(options.body);
    if (data.action === "add") categories.push(data.name);
    if (data.action === "rename") { categories = categories.map((entry) => entry === data.current ? data.name : entry); for (const item of items.values()) if (item.category === data.current) item.category = data.name; }
    if (data.action === "delete") { categories = categories.filter((entry) => entry !== data.name); for (const item of items.values()) if (item.category === data.name) item.category = "未分类"; }
    payload = { saved: true };
  } else {
    const id = path.split("/").at(-1);
    if (!items.has(id)) return Response.json({ error: { message: "Material does not exist" } }, { status: 404 });
    if (options.method === "DELETE") { items.delete(id); payload = { deleted: true }; }
    else { if (options.method === "POST") Object.assign(items.get(id), JSON.parse(options.body)); payload = items.get(id); }
  }
  return Response.json(payload);
} };
const asModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const read = (file) => readFileSync(new URL(`../web/js/${file}`, import.meta.url), "utf8");
const uploadUrl = asModule(read("material_uploads.js"));
const library = await import(asModule(read("material_library.js")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__materialApi;")
  .replace('"./material_uploads.js"', JSON.stringify(uploadUrl))));
globalThis.__materialLibrary = library;
const frontend = await import(asModule(read("material_images.js")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__materialApp;")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__materialApi;")
  .replace('"./material_uploads.js"', JSON.stringify(uploadUrl))
  .replace(/import \{ (.*?) \} from "\.\/material_library.js";/, "const { $1 } = globalThis.__materialLibrary;")));
const settle = async () => { for (let index = 0; index < 8; index++) await new Promise((resolve) => setTimeout(resolve, 0)); };
function node(type, value = "") {
  const result = { type, widgets: [{ name: type === "MengBaoLoadImage" ? "image" : "material_id", value }], outputs: [{ name: "image" }, { name: "mask" }], size: [360, 410],
    addDOMWidget(name, kind, element, options) { this.domOptions = options; body.append(element); }, setDirtyCanvas() {}, computeSize: () => [360, 410], setSize() {} };
  __materialApp.graph._nodes.push(result); frontend.setupNode(result); return result;
}
const loader = node("MengBaoLoadImage");
await loader._mengBaoMaterialRestorePromise;
assert.equal(loader.title, "萌宝AI·加载图片");
assert.equal(loader.widgets[0].type, "hidden");
assert.equal(loader.domOptions.serialize, false);
assert.equal(loader._mengBaoMaterialControls.clear.disabled, true);
const file = new File([new Uint8Array([1, 2, 3])], "upload.png", { type: "image/png" });
await loader._mengBaoMaterialControls.binding.receiveFiles([file]);
assert.equal(loader.widgets[0].value, "mengbao/upload.png");
assert.equal(loader._mengBaoMaterialState.width, 8);
assert.equal(requests.at(-1).options.body.get("subfolder"), "mengbao");
const oldValue = loader.widgets[0].value;
failUpload = true;
await loader._mengBaoMaterialControls.binding.receiveFiles([file]);
assert.equal(loader.widgets[0].value, oldValue);
assert.equal(loader._mengBaoMaterialControls.status.textContent, "Upload failed");
failUpload = false;
frontend.clearImage(loader);
assert.equal(loader.widgets[0].value, "");
assert.equal(loader._mengBaoMaterialControls.image.src, null);
assert.equal(loader._mengBaoMaterialState.width, 0);
await loader._mengBaoMaterialControls.image.fire("load");
assert.equal(loader._mengBaoMaterialState.width, 0);
await loader._mengBaoMaterialControls.load.click();
await settle();
const dialog = document.querySelector();
assert.equal(library.isMaterialDialogOpen(), true);
const grid = dialog.children[4];
assert.equal(grid.children.length, 1);
await grid.children[0].children[0].click();
await dialog.children[6].children[1].click();
assert.equal(loader.widgets[0].value, `mengbao-material:${firstId}`);
assert.equal(library.isMaterialDialogOpen(), false);
const libraryNode = node("MengBaoMaterialLibrary", firstId);
assert.equal(libraryNode.title, "萌宝AI·素材库");
await libraryNode._mengBaoMaterialRestorePromise;
assert.equal(libraryNode._mengBaoMaterialState.name, "产品.png");
await libraryNode._mengBaoMaterialControls.binding.receiveFiles([file, file]);
assert.equal(items.size, 3);
assert.equal(libraryNode.widgets[0].value, "3".padStart(32, "0"));
await extension.setup();
locale = "en"; __materialApp.ui.settings.settingsLookup["Comfy.Locale"].onChange(); await settle();
assert.equal(loader.title, "MengBao AI · Load Image");
assert.equal(libraryNode.outputs[1].label, "Mask");
locale = "fr"; frontend.renderNode(loader); assert.equal(loader._mengBaoMaterialControls.load.textContent, "Load Material");
locale = "zh-TW";
await libraryNode._mengBaoMaterialControls.load.click(); await settle();
const managing = document.querySelector();
assert.equal(managing.children[0].children[0].textContent, "萌宝AI·素材库");
const actions = managing.children[2];
await actions.children[2].click(); await settle();
assert.ok(categories.includes("新品"));
const filter = managing.children[1].children[1]; filter.value = ""; await filter.fire("change");
const managedGrid = managing.children[4];
await managedGrid.children[0].children[3].children[0].click(); await settle();
assert.equal(items.get(firstId).favorite, true);
const search = managing.children[1].children[0]; search.value = "missing"; await search.fire("input");
assert.equal(managedGrid.children[0].textContent, "暂无匹配素材");
assert.equal(managing.children[6].children[1].disabled, true);
search.value = ""; await search.fire("input");
locale = "en"; library.refreshMaterialDialogLocale();
assert.equal(managing.children[0].children[0].textContent, "MengBao Material Library");
const picker = actions.children[0];
await picker.click();
filter.value = "新品"; await filter.fire("change");
await actions.children[4].click(); await settle();
assert.equal(categories.includes("新品"), false);
managing.close();
for (const entry of __materialApp.graph._nodes) entry._mengBaoMaterialControls.binding.dispose();
assert.equal(requests.some(({ options }) => options.method === "DELETE"), false);
console.log("Material node, picker, persistence reference and localization tests passed.");
