import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

globalThis.window = {};
globalThis.document = { addEventListener() {} };
globalThis.__draftApp = { registerExtension() {} };
const source = readFileSync(new URL("../web/js/prompt_organizer.js", import.meta.url), "utf8")
  .replace('import { app } from "../../../scripts/app.js";', "const app = globalThis.__draftApp;")
  + "\nexport { onSave, state };";
const frontend = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(typeof window.MengBaoPromptOrganizerDraft, "function");
assert.equal(frontend.hasUnsavedPromptDraft(null), false);
assert.equal(frontend.hasUnsavedPromptDraft({ values: {}, previewImage: "" }), false);
assert.equal(frontend.hasUnsavedPromptDraft({ values: { prompt: "new text" } }), true);
const saved = { title: "saved", group: "default", prompt: "original", tags: ["test"], note: "", color: "#e25545", preview_image: "data:image/png;base64,image" };
const draft = { values: { title: "saved", group: "default", prompt: "original", tags: "test", note: "" }, color: saved.color, previewImage: saved.preview_image };
assert.equal(frontend.hasUnsavedPromptDraft(draft, saved), false);
assert.equal(frontend.hasUnsavedPromptDraft({ ...draft, values: { ...draft.values, prompt: "my changes" } }, saved), true);
assert.equal(frontend.hasUnsavedPromptDraft({ ...draft, previewImage: "new image" }, saved), true);

const saveButton = { disabled: false, textContent: "" };
const status = { textContent: "" };
document.querySelector = () => saveButton;
document.getElementById = (id) => id === "wang-prompt-status" ? status : null;
globalThis.FormData = class { entries() { return Object.entries({ title: "retryable draft", group: "default", prompt: "do not lose this text" }); } };
let finishRequest;
let requests = 0;
globalThis.fetch = () => { requests += 1; return new Promise((resolve) => { finishRequest = resolve; }); };
frontend.state.imageDraftOpen = true;
frontend.state.previewImage = saved.preview_image;
const event = { preventDefault() {}, currentTarget: { dataset: {} } };
const pending = frontend.onSave(event);
assert.equal(saveButton.disabled, true);
await frontend.onSave(event);
assert.equal(requests, 1, "Repeated clicks must not submit twice");
finishRequest({ ok: false, text: async () => "PermissionError: Access denied" });
await pending;
assert.equal(status.textContent, "PermissionError: Access denied");
assert.equal(saveButton.disabled, false);
assert.equal(frontend.state.imageDraftOpen, true);
assert.equal(frontend.state.previewImage, saved.preview_image);
console.log("Prompt draft bridge, content protection, save loading and failure tests passed.");
