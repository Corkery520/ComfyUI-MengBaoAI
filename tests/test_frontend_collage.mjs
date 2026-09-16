import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

let extension;
const locale = { value: "zh-CN" };
const app = {
  ui: { settings: { getSettingValue: () => locale.value } },
  graph: { setDirtyCanvas() {} },
  registerExtension(value) { extension = value; },
};
globalThis.__mengBaoCollageTestApp = app;
globalThis.document = {
  createElement() {
    return {
      style: {}, listeners: {}, children: [],
      append(...children) { this.children.push(...children); },
      addEventListener(name, callback) { this.listeners[name] = callback; },
    };
  },
};
const labels = readFileSync(new URL("../web/js/node_localization.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__mengBaoCollageTestApp;");
globalThis.__mengBaoCollageTestLocalization = await import(
  `data:text/javascript;base64,${Buffer.from(labels).toString("base64")}`,
);
const source = readFileSync(new URL("../web/js/smart_collage.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__mengBaoCollageTestApp;")
  .replace('import { applyNodeLocalization, normalizeLanguage } from "./node_localization.js";',
    "const { applyNodeLocalization, normalizeLanguage } = globalThis.__mengBaoCollageTestLocalization;");
await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

class Node {
  constructor() {
    this.type = "MengBaoSmartCollage";
    this.inputs = Array.from({ length: 20 }, (_, index) => ({ name: `image_${index + 1}`, type: "IMAGE", link: null }));
    this.outputs = [{ name: "image" }];
    this.widgets = [];
    this.size = [400, 200];
    this.removedLinks = [];
  }
  addInput(name, type) { this.inputs.push({ name, type, link: null }); }
  removeInput(index) {
    if (this.inputs[index].link != null) this.removedLinks.push(this.inputs[index].link);
    this.inputs.splice(index, 1);
  }
  addDOMWidget(name, type, element, options) {
    const widget = { name, type, element, options };
    this.widgets.push(widget);
    return widget;
  }
  computeSize() { return [400, this.inputs.length * 24 + 80]; }
  setSize(size) { this.size = size; }
  setDirtyCanvas() {}
}
await extension.beforeRegisterNodeDef(Node, { name: "MengBaoSmartCollage" });
assert.equal(extension.name, "MengBaoAI.smart_collage");
const node = new Node();
node.onNodeCreated();
assert.equal(node.inputs.length, 4);
assert.equal(node.widgets.length, 1);
const controls = node._mengBaoCollageControls;
assert.equal(controls.widget.options.serialize, false);
assert.equal(controls.widget.element.style.display, "flex");
assert.equal(controls.addButton.style.background, "#477ac1");
assert.match(controls.addButton.textContent, /添加图片 5 \(4\/20\)/);
assert.equal(controls.removeButton.disabled, true);
controls.removeButton.listeners.click();
assert.equal(node.inputs.length, 4);
const initialHeight = node.size[1];
controls.addButton.listeners.click();
assert.equal(node.inputs.length, 5);
assert.equal(node.inputs[4].label, "图片 5");
assert.ok(node.size[1] > initialHeight);
assert.equal(controls.removeButton.disabled, false);
for (let index = 5; index < 20; index++) controls.addButton.listeners.click();
assert.equal(node.inputs.length, 20);
assert.equal(node.inputs[19].label, "图片 20");
assert.equal(controls.addButton.disabled, true);
controls.addButton.listeners.click();
assert.equal(node.inputs.length, 20);
node.inputs[0].link = 100;
node.inputs[19].link = 120;
controls.removeButton.listeners.click();
assert.equal(node.inputs.length, 19);
assert.deepEqual(node.removedLinks, [120]);
assert.equal(node.inputs[0].link, 100);
assert.equal(controls.addButton.disabled, false);
assert.ok(node.size[0] >= 560);

globalThis.__mengBaoCollageTestLocalization.applyNodeLocalization(node, "en");
assert.match(controls.addButton.textContent, /^Add Image 20/);
assert.equal(node.inputs[18].label, "Image 19");
globalThis.__mengBaoCollageTestLocalization.applyNodeLocalization(node, "zh-TW");
assert.match(controls.removeButton.textContent, /^删除图片 19/);

const savedInputs = node.inputs.map((input) => ({ ...input }));
const restored = new Node();
restored.onNodeCreated();
restored.inputs = savedInputs.map((input) => ({ ...input }));
restored.onConfigure({ inputs: savedInputs });
assert.equal(restored.inputs.length, 19);
assert.equal(restored.inputs[0].link, 100);
assert.match(restored._mengBaoCollageControls.addButton.textContent, /20 \(19\/20\)/);
restored.onConfigure({ inputs: savedInputs });
assert.equal(restored.widgets.length, 1);

const legacy = new Node();
legacy.onNodeCreated();
legacy.onConfigure({ inputs: legacy.inputs });
assert.equal(legacy.inputs.length, 4);
while (restored.inputs.length > 4) restored._mengBaoCollageControls.removeButton.listeners.click();
assert.equal(restored._mengBaoCollageControls.removeButton.disabled, true);
assert.equal(restored.inputs[0].link, 100);
console.log("Smart collage frontend tests passed.");
