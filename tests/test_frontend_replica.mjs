import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const moduleSource = readFileSync(new URL("../web/js/replica_model.js", import.meta.url), "utf8");
const modelUrl = `data:text/javascript;base64,${Buffer.from(moduleSource).toString("base64")}`;
const model = await import(modelUrl);
assert.equal(model.normalizeLanguage("zh-TW"), "zh");
assert.equal(model.normalizeLanguage("de"), "en");
assert.equal(model.labels("zh-CN").settingsTitle, "萌宝AI·图片复刻设置");
const record = { id: "a", source: { id: "source" }, analysis: { composition: "Original", elements: [
  { id: "p1", kind: "product", productGroup: "same", box: { x: .1, y: .1, w: .2, h: .2 } },
  { id: "p2", kind: "product", productGroup: "same" },
  { id: "t", kind: "text", parentId: "p1" },
] } };
const draft = model.draftFor(record);
draft.linkedGroups = ["same"];
model.changeReplacement(draft, draft.analysis.elements[0], { mode: "replace", images: ["product", "product"], description: "New product" });
assert.deepEqual(draft.replacements.p2, draft.replacements.p1);
assert.deepEqual(model.references(draft, "source"), ["source", "product"]);
assert.equal(model.inherited(draft, draft.analysis.elements[2]), true);
assert.equal(draft.confirmed, false);
draft.confirmed = true;
assert.equal(model.draftFor(record, draft).confirmed, true);
assert.equal(model.draftFor({ ...record, id: "changed" }, draft).confirmed, false);
assert.equal(model.validBox({ x: .8, y: .1, w: .3, h: .1 }), false);
assert.equal(model.validBox({ x: NaN, y: 0, w: 1, h: 1 }), false);
const removed = structuredClone(draft);
model.removeElement(removed, 'p1');
assert.deepEqual(removed.analysis.elements.map(element => element.id), ['p2']);
assert.equal(removed.replacements.t, undefined);
assert.equal(removed.confirmed, false);
const prompt = { "1": { class_type: "LoadImage", inputs: {} }, "2": { class_type: "MengBaoImageReverse", inputs: { image: ["1", 0] } }, "3": { class_type: "MengBaoImageReplicaSettings", inputs: { analysis: ["2", 0] } }, "4": { class_type: "WANGImageAPI", inputs: { replica_settings: ["3", 1] } } };
const queue = model.analysisQueue(2, prompt);
assert.deepEqual(Object.keys(queue.prompt), ["1", "2"]);
assert.deepEqual(queue.partial_execution_targets, ["2"]);
assert.equal(queue.prompt["4"], undefined);

let extension;
globalThis.replicaApp = { registerExtension(value) { extension = value; }, ui: { settings: { getSettingValue() { return "zh"; } } }, graph: { _nodes: [] } };
const editorUrl = `data:text/javascript;base64,${Buffer.from("export const fileUrl = id => '/file/' + id; export function invalidateReplicaEditor(){} export function openReplicaEditor(){} export function refreshReplicaEditorLocale(){} export function replicaRequest(){return Promise.resolve({});}").toString("base64")}`;
const source = readFileSync(new URL("../web/js/replica.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.replicaApp;")
  .replace('import { api } from "../../../scripts/api.js";', "const api = {};")
  .replace('"./replica_model.js"', JSON.stringify(modelUrl)).replace('"./replica_editor.js"', JSON.stringify(editorUrl));
const frontend = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(extension.name, "MengBaoAI.replica");
const fake = { type: "MengBaoImageReverse", _mengBaoReplicaState: { record: { ...record, model: "gem-3.8-flash", attempts: [{model:'gem-3.7-flash',error:'HTTP 503 Service Unavailable',success:false}] }, busy: false }, _mengBaoReplicaControls: { image: { getAttribute() {}, set src(value) {} }, empty: {}, button: {}, status: {} }, inputs: [{ name: "image" }], outputs: [{}, {}] };
frontend.renderNode(fake);
assert.equal(fake.title, "萌宝AI·图片反推");
assert.equal(fake.inputs[0].label, "原图");
assert.match(fake._mengBaoReplicaControls.status.textContent, /gem-3.8-flash/);
assert.match(fake._mengBaoReplicaControls.status.textContent, /HTTP 503 Service Unavailable/);
console.log("Replica frontend: locale, linked replacements, cache drafts, positions, isolated queue and node labels passed");
