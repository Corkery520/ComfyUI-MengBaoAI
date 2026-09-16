import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

let extension;
let locale = "zh-CN";
const listeners = {};
let fileInput;
const app = {
  graph: { _nodes: [], setDirtyCanvas() {} },
  canvas: { selected_nodes: {} },
  ui: { settings: { getSettingValue: () => locale, settingsLookup: {} } },
  registerExtension(value) { extension = value; },
};
globalThis.__mengBaoLoadImageTestApp = app;
globalThis.document = {
  addEventListener(name, callback) { listeners[name] = callback; },
  createElement(tag) {
    assert.equal(tag, "input");
    fileInput = { click() { this.clicked = true; } };
    return fileInput;
  },
};
globalThis.FileReader = class {
  readAsDataURL(file) { this.result = file.data; this.onload(); }
};
const source = readFileSync(new URL("../web/js/load_image.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__mengBaoLoadImageTestApp;");
await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

class Node {
  constructor() {
    this.type = "WANGLoadImageUploadPaste";
    this.widgets = [
      { name: "image_data", type: "customtext", value: "saved-image-data", element: { style: {} }, options: {} },
      { name: "filename", type: "text", value: "saved.png", options: {} },
    ];
    this.size = [300, 160];
  }
  addWidget(type, name, value, callback) {
    const widget = { type, name, value, callback, options: {} };
    this.widgets.push(widget);
    return widget;
  }
  addCustomWidget(widget) { this.widgets.push(widget); return widget; }
  computeSize() { return [300, 200]; }
  setSize(size) { this.size = size; }
}
await extension.beforeRegisterNodeDef(Node, { name: "WANGLoadImageUploadPaste" });
const node = new Node();
app.graph._nodes.push(node);
node.onNodeCreated();
for (const widget of node.widgets.slice(0, 2)) {
  // ComfyUI DOMWidgetImpl.isVisible() checks hidden, not only the widget type.
  assert.equal(widget.hidden, true, `${widget.name} must not render outside the node`);
  assert.equal(widget.type, "hidden");
  assert.equal(widget.serialize, true);
}
assert.equal(node.widgets[0].element.style.display, "none");
assert.equal(node.widgets[0].value, "saved-image-data");
assert.equal(node.widgets[1].value, "saved.png");
const hint = node.widgets.find(({ name }) => name === "mengbao_load_status");
assert.ok(hint, "The upload hint must have its own allocated widget space");
assert.equal(hint.serialize, false);
assert.ok(hint.computeSize(300)[1] >= 44);
assert.equal(node.widgets.indexOf(hint), node.widgets.length - 1);
const drawn = [];
const context = {
  save() {}, restore() {}, fillRect() {},
  measureText(text) { return { width: [...text].reduce((width, character) => width + (character.charCodeAt(0) < 128 ? 6 : 12), 0) }; },
  fillText(text, x, y) { drawn.push({ text, x, y }); },
};
hint.draw(context, node, 300, 160, 48);
assert.match(drawn.map(({ text }) => text).join(""), /Ctrl\+V/);
assert.ok(drawn.every(({ y }) => y >= 160 && y <= 208));
locale = "en";
drawn.length = 0;
hint.draw(context, node, 300, 160, 48);
assert.match(drawn.map(({ text }) => text).join(""), /Ctrl\+V/);
node.onConfigure({ widgets_values: ["saved-image-data", "saved.png"] });
assert.equal(node.widgets.length, 5, "Reload must not duplicate controls");
const event = { target: { tagName: "TEXTAREA" }, preventDefault() { throw new Error("Text paste was intercepted"); } };
await listeners.paste(event);
const file = { name: "chosen.png", type: "image/png", data: "data:image/png;base64,test-fixture" };
node.widgets.find(({ _mengBaoLoadAction }) => _mengBaoLoadAction === "upload").callback();
assert.equal(fileInput.clicked, true);
assert.match(fileInput.accept, /image\/png/);
fileInput.files = [file];
await fileInput.onchange();
assert.equal(node.widgets[0].value, file.data);
assert.equal(node.widgets[1].value, "chosen.png");
assert.equal(node.widgets[0].hidden, true);
assert.ok(node.size[0] >= 300);
app.canvas.selected_nodes = { first: node };
let intercepted = false;
await listeners.paste({
  target: { tagName: "CANVAS" }, clipboardData: { files: [{ ...file, name: "clipboard.png" }] },
  preventDefault() { intercepted = true; },
});
assert.equal(intercepted, true);
assert.equal(node.widgets[1].value, "clipboard.png");
const otherNode = new Node();
otherNode.onNodeCreated();
app.graph._nodes.push(otherNode);
app.canvas.selected_nodes.second = otherNode;
intercepted = false;
await listeners.paste({ target: { tagName: "CANVAS" }, clipboardData: { files: [file] }, preventDefault() { intercepted = true; } });
assert.equal(intercepted, false, "Multiple upload nodes must not guess a paste target");
otherNode.onMouseEnter();
await listeners.paste({ target: { tagName: "CANVAS" }, clipboardData: { files: [file] }, preventDefault() {} });
assert.equal(otherNode.widgets[1].value, "chosen.png");
assert.equal(node.widgets[1].value, "clipboard.png");
otherNode.onMouseLeave();
assert.equal(node.widgets.length, 5);
console.log("Legacy image loader visibility and layout tests passed.");
