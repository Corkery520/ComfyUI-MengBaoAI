import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const listeners = {};
globalThis.document = {
  activeElement: null,
  addEventListener(name, callback) { listeners[name] = callback; },
  createElement() { return { click() { this.clicked = true; } }; },
};
const source = readFileSync(new URL("../web/js/material_uploads.js", import.meta.url), "utf8");
const uploads = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
function element() {
  return {
    isConnected: true, handlers: {},
    addEventListener(name, callback) { this.handlers[name] = callback; },
    removeEventListener(name) { delete this.handlers[name]; },
    getClientRects() { return [1]; }, contains(target) { return target === this; },
  };
}
const first = element();
const received = [];
const errors = [];
let enabled = true;
const binding = uploads.bindUploadTarget(first, {
  maxFiles: 1, available: () => enabled,
  upload: async (files) => received.push(files.map(({ name }) => name)),
  onError: (error) => errors.push(error.message),
});
const image = { type: "image/png", name: "image.png", size: 100 };
const event = (target, files) => ({ target, clipboardData: { files }, preventDefault() { this.prevented = true; } });
await binding.receiveFiles([image]);
assert.deepEqual(received, [["image.png"]]);
const paste = event({}, [image]);
await listeners.paste(paste);
assert.equal(paste.prevented, true);
assert.deepEqual(received[1], received[0]);
await listeners.paste(event({ tagName: "TEXTAREA" }, [image]));
assert.equal(received.length, 2);
enabled = false;
await binding.receiveFiles([image]);
await listeners.paste(event({}, [image]));
assert.equal(received.length, 2);
enabled = true;
await binding.receiveFiles([{ ...image, size: 33 * 1024 * 1024 }]);
assert.match(errors.at(-1), /32 MB/);
await binding.receiveFiles([image, image]);
assert.match(errors.at(-1), /at most 1/);
await binding.receiveFiles([{ ...image, type: "text/plain" }]);
assert.match(errors.at(-1), /Supported image/);
const second = element();
const other = [];
const secondBinding = uploads.bindUploadTarget(second, { maxFiles: 20, upload: async (files) => other.push(files), onError() {} });
await listeners.paste(event({}, [image]));
assert.equal(received.length, 2);
assert.equal(other.length, 0);
second.handlers.mouseenter();
await listeners.paste(event({}, [image]));
assert.equal(other.length, 1);
second.handlers.mouseleave();
document.activeElement = first;
await listeners.paste(event({}, [image]));
assert.equal(received.length, 3);
document.activeElement = null;
second.isConnected = false;
await listeners.paste(event({}, [image]));
assert.equal(received.length, 4);
const dropping = { dataTransfer: { files: [image] }, preventDefault() {} };
await first.handlers.drop(dropping);
assert.equal(received.length, 5);
const picker = binding.chooseFiles();
assert.equal(picker.clicked, true);
assert.equal(picker.multiple, false);
assert.match(picker.accept, /image\/png/);
picker.files = [image];
await picker.onchange();
assert.equal(received.length, 6);
globalThis.getComputedStyle = () => ({ visibility: "hidden" });
await binding.receiveFiles([image]);
await listeners.paste(event({}, [image]));
assert.equal(received.length, 6);
delete globalThis.getComputedStyle;
second.isConnected = true;
document.querySelector = () => ({ contains(target) { return target === second; } });
first.handlers.mouseenter();
await listeners.paste(event({}, [image]));
assert.equal(received.length, 6);
assert.equal(other.length, 2);
second.isConnected = false;
await listeners.paste(event({}, [image]));
assert.equal(received.length, 6);
document.querySelector = () => null;
binding.dispose();
secondBinding.dispose();
console.log("Material upload routing tests passed.");
