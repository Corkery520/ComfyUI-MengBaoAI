import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Element {
  constructor(tag) { this.tagName = tag; this.style = {}; this.children = []; this.handlers = {}; this.attributes = {}; this.value = ""; this.classList = { toggle() {} }; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  set src(value) { this.setAttribute("src", value); }
  get src() { return this.getAttribute("src"); }
  getContext() { return { drawImage() {} }; }
  toDataURL(type) { assert.equal(type, "image/png"); return "data:image/png;base64,pixel-only-thumbnail"; }
}
globalThis.document = { head: new Element("head"), getElementById: () => null, createElement: (tag) => new Element(tag) };
const drafts = [], requests = [], materials = [];
globalThis.window = { MengBaoPromptOrganizerDraft: (draft) => { drafts.push(draft); return true; } };
globalThis.createImageBitmap = async () => ({ width: 750, height: 10661, close() {} });
let extension, locale = "zh-CN", fail = false, failImport = false, finishImport;
globalThis.__outputMaterials = { async importMaterial(file) {
  materials.push(file);
  if (finishImport) await new Promise((resolve) => { finishImport = resolve; });
  if (failImport) throw new Error("Image file exceeds the 32 MB limit");
  return { id: "test-material", name: file.name };
} };
globalThis.__outputApp = { graph: { _nodes: [] }, ui: { settings: {
  getSettingValue: () => locale, settingsLookup: { "Comfy.Locale": { onChange() {} } },
} }, registerExtension(value) { extension = value; } };
globalThis.__outputApi = { async fetchApi(path) {
  requests.push(path);
  if (fail) return { ok: false, status: 404, text: async () => "FileNotFoundError: Image file is missing" };
  return { ok: true, blob: async () => new Blob(["PNG pixels"]) };
} };
const source = readFileSync(new URL("../web/js/image_output.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__outputApp;")
  .replace('import { api } from "../../../scripts/api.js";', "const api = globalThis.__outputApi;")
  .replace('import { importMaterial } from "./material_library.js";', "const { importMaterial } = globalThis.__outputMaterials;")
  .replace('new URL("./image_output.css", import.meta.url).href', JSON.stringify(new URL("../web/js/image_output.css", import.meta.url).href));
const frontend = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
class Node {
  constructor(type) { this.type = type; this.widgets = [{ name: "filename_prefix" }]; this.inputs = [{ name: "images" }, { name: "generation_prompt" }]; this.size = [360, 400]; }
  onExecuted(message) { this.nativeMessage = message; return "native-result"; }
  onDrawBackground() { this.nativePreviewDrawn = true; }
  addDOMWidget(name, type, root, options) { this.domOptions = options; this.root = root; }
  computeSize() { return [360, 400]; }
  setSize() {}
  setDirtyCanvas() {}
}
await extension.beforeRegisterNodeDef(Node, { name: "MengBaoSaveImage" });
const node = new Node("MengBaoSaveImage");
__outputApp.graph._nodes.push(node);
node.onNodeCreated();
assert.equal(node.title, "萌宝AI·保存图片");
assert.equal(node.inputs[1].label, "生图提示词");
assert.equal(node.domOptions.serialize, false);
assert.equal(node._mengBaoImageOutputControls.button.disabled, true);
const controls = node._mengBaoImageOutputControls;
assert.ok(controls.zone, "A preview placeholder must exist before generation");
assert.equal(controls.image.hidden, true);
assert.equal(controls.hint.textContent, "等待生成图片");
assert.equal(controls.materialButton.textContent, "加入素材库");
assert.equal(controls.materialButton.disabled, true);
assert.deepEqual(controls.actions.children, [controls.materialButton, controls.button]);
assert.ok(controls.root.children.indexOf(controls.zone) < controls.root.children.indexOf(controls.actions));
node.onDrawBackground();
assert.notEqual(node.nativePreviewDrawn, true, "Do not draw a second native preview beneath the buttons");
const images = [{ filename: "first.png", subfolder: "test", type: "output" }, { filename: "second.png", subfolder: "test", type: "temp" }];
const candidates = [{ node_id: "1", class_type: "WANGImageAPI", text: "first image prompt" }, { node_id: "2", class_type: "WANGImageAPI", text: "second image prompt" }];
const message = { images, mengbao_prompt_candidates: candidates };
assert.equal(node.onExecuted(message), "native-result");
assert.equal(node.nativeMessage, message);
assert.equal(controls.image.hidden, false);
assert.match(controls.image.src, /filename=first.png/);
assert.equal(controls.hint.hidden, true);
assert.equal(controls.pager.hidden, false);
controls.next.handlers.click();
assert.match(controls.image.src, /filename=second.png/);
assert.equal(node.imageIndex, 1);
controls.image.naturalWidth = 750; controls.image.naturalHeight = 10661;
controls.image.handlers.load();
assert.match(controls.status.textContent, /750 × 10661/);
await frontend.addImageMaterial(node);
assert.equal(materials[0].name, "second.png");
assert.equal(materials[0].type, "image/png");
assert.equal(await materials[0].text(), "PNG pixels", "Material import must receive original file bytes, not the prompt thumbnail");
assert.match(controls.status.textContent, /已加入素材库/);
assert.equal(node._mengBaoImageOutputControls.select.hidden, false);
assert.equal(node._mengBaoImageOutputControls.button.disabled, true);
node._mengBaoImageOutputControls.select.value = "1";
node._mengBaoImageOutputControls.select.handlers.change();
node.imageIndex = 1;
await frontend.addImagePrompt(node);
assert.equal(drafts[0].prompt, "second image prompt");
assert.equal(drafts[0].preview_image, "data:image/png;base64,pixel-only-thumbnail");
assert.equal(drafts[0].group, "default");
assert.match(requests.at(-1), /filename=second.png/);
assert.match(requests.at(-1), /type=temp/);
assert.equal(node._mengBaoImageOutputState.busy, false);
await extension.setup();
locale = "en"; __outputApp.ui.settings.settingsLookup["Comfy.Locale"].onChange();
await new Promise((resolve) => setTimeout(resolve, 5));
assert.equal(node.title, "MengBao AI · Save Image");
assert.equal(node._mengBaoImageOutputControls.select.value, "1");
assert.equal(node._mengBaoImageOutputControls.button.textContent, "Add to Prompt Library");
assert.equal(controls.materialButton.textContent, "Add to Material Library");
fail = true;
await frontend.addImagePrompt(node);
assert.equal(node._mengBaoImageOutputControls.status.textContent, "FileNotFoundError: Image file is missing");
assert.equal(node._mengBaoImageOutputControls.button.disabled, false);
await frontend.addImageMaterial(node);
assert.equal(controls.status.textContent, "FileNotFoundError: Image file is missing");
fail = false;
failImport = true;
await frontend.addImageMaterial(node);
assert.equal(controls.status.textContent, "Image file exceeds the 32 MB limit");
assert.equal(controls.materialButton.disabled, false);
failImport = false;
finishImport = true;
const importing = frontend.addImageMaterial(node);
for (let index = 0; index < 12; index++) await Promise.resolve();
assert.equal(controls.materialButton.disabled, true);
assert.equal(controls.button.disabled, true);
const materialCount = materials.length;
await frontend.addImageMaterial(node);
assert.equal(materials.length, materialCount, "Repeated clicks must not create duplicate requests while busy");
finishImport(); finishImport = null; await importing;
node.onExecuted({ images: [images[0]], mengbao_prompt_candidates: [] });
await frontend.addImagePrompt(node);
assert.equal(drafts.at(-1).prompt, "");
assert.equal(node._mengBaoImageOutputControls.select.hidden, true);
assert.equal(controls.pager.hidden, true);
locale = "fr"; frontend.renderImageOutput(node); assert.equal(node.title, "MengBao AI · Save Image");
locale = "zh-TW"; frontend.renderImageOutput(node); assert.equal(node.title, "萌宝AI·保存图片");
class PreviewNode extends Node {}
await extension.beforeRegisterNodeDef(PreviewNode, { name: "MengBaoPreviewImage" });
const preview = new PreviewNode("MengBaoPreviewImage");
preview.onNodeCreated();
assert.equal(preview.title, "萌宝AI·预览图片");
assert.equal(preview.onExecuted({ images: [images[1]], mengbao_prompt_candidates: [candidates[1]] }), "native-result");
await frontend.addImagePrompt(preview);
assert.equal(drafts.at(-1).prompt, "second image prompt");
assert.match(requests.at(-1), /type=temp/);
await frontend.addImageMaterial(preview);
assert.match(requests.at(-1), /type=temp/);
assert.equal(materials.at(-1).name, "second.png");
preview.onExecuted({ images: [] });
assert.equal(preview._mengBaoImageOutputControls.image.hidden, true);
assert.equal(preview._mengBaoImageOutputControls.image.src, null);
assert.equal(preview._mengBaoImageOutputControls.materialButton.disabled, true);
assert.equal(preview._mengBaoImageOutputControls.button.disabled, true);
assert.throws(() => frontend.imageOutputUrl({ filename: "bad.png", type: "input" }), /Image output reference is invalid/);
assert.match(frontend.imageOutputUrl({ filename: "a&b.png", subfolder: "folder name", type: "output" }), /filename=a%26b.png/);
const css = readFileSync(new URL("../web/js/image_output.css", import.meta.url), "utf8");
assert.match(css, /object-fit:\s*contain/);
assert.match(css, /\[hidden\]/);
preview.onExecuted({ images: [images[1]] });
preview._mengBaoImageOutputControls.image.handlers.error();
assert.equal(preview._mengBaoImageOutputControls.status.textContent, "Image preview could not be loaded");
__outputApi.apiURL = (path) => `/comfy${path}`;
preview.onExecuted({ images: [images[0]] });
assert.match(preview._mengBaoImageOutputControls.image.src, /^\/comfy\/view\?/);
await frontend.addImageMaterial(preview);
assert.match(requests.at(-1), /^\/view\?/, "fetchApi must apply the API base path only once");
const restored = new Node("MengBaoSaveImage"); restored.id = "cached";
__outputApp.nodeOutputs = { cached: message };
restored.onConfigure();
assert.match(restored._mengBaoImageOutputControls.image.src, /filename=first.png/);
assert.equal(restored._mengBaoImageOutputControls.select.hidden, false);
assert.equal(restored.domOptions.getMinHeight(), 424);
assert.equal(restored.domOptions.getMaxHeight(), 424);
const root = restored.root;
restored.onConfigure();
assert.equal(restored.root, root, "Workflow restore must not duplicate the placeholder and buttons");
locale = "en"; frontend.renderImageOutput(preview); assert.equal(preview.title, "MengBao AI · Preview Image");
console.log("Image output prompt capture, native hooks, thumbnails and locale tests passed.");
