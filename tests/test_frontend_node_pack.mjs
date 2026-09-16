import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const localizationUrl = new URL("../web/js/node_localization.js", import.meta.url);
const source = readFileSync(fileURLToPath(localizationUrl), "utf8");
let registeredExtension;
const locale = { value: "en" };

globalThis.__mengBaoPackTestApp = {
  graph: { _nodes: [], setDirtyCanvas() {} },
  ui: {
    settings: {
      getSettingValue(name) {
        return name === "Comfy.Locale" ? locale.value : undefined;
      },
      settingsLookup: { "Comfy.Locale": { onChange() {} } },
    },
  },
  registerExtension(extension) {
    registeredExtension = extension;
  },
};

const testable = source.replace(
  'import { app } from "../../../scripts/app.js";',
  "const app = globalThis.__mengBaoPackTestApp;"
);
const moduleUrl = `data:text/javascript;base64,${Buffer.from(testable).toString("base64")}`;
const localization = await import(moduleUrl);

function makeNode(type) {
  return {
    type,
    widgets: [
      { name: "grid", label: "grid", options: {} },
      { name: "custom_rows", label: "custom_rows", options: {} },
    ],
    inputs: [{ name: "image" }],
    outputs: [
      { name: "tiles" },
      { name: "rows" },
      { name: "columns" },
      { name: "tile_count" },
    ],
    setDirtyCanvas() {},
  };
}

assert.equal(localization.normalizeLanguage("zh-CN"), "zh");
assert.equal(localization.normalizeLanguage("fr"), "en");

const node = makeNode("ImageGridSplit");
localization.applyNodeLocalization(node, "en");
assert.equal(node.title, "MengBao AI · Image Split");
assert.equal(node.widgets[0].label, "Grid");
assert.equal(node.widgets[0].options.getOptionLabel("custom"), "Custom");
assert.equal(node.inputs[0].label, "Image");
assert.equal(node.outputs[3].label, "Tile Count");

localization.applyNodeLocalization(node, "zh-CN");
assert.equal(node.title, "萌宝AI·图片拆分");
assert.equal(node.widgets[0].options.getOptionLabel("custom"), "自定义");
assert.equal(node.outputs[3].label, "图片块数量");
assert.equal(registeredExtension.name, "MengBaoAI.node_localization");

const loadSource = readFileSync(
  fileURLToPath(new URL("../web/js/load_image.js", import.meta.url)),
  "utf8"
);
assert.match(loadSource, /document\.addEventListener\(\s*["']paste["']/);
assert.match(loadSource, /isEditableTarget\(event\.target\)/);
assert.match(loadSource, /pasteTargetNode\(\)/);
assert.match(loadSource, /Ctrl\+V/);

const promptSource = readFileSync(
  fileURLToPath(new URL("../web/js/prompt_organizer.js", import.meta.url)),
  "utf8"
);
assert.match(promptSource, /state\.pasteTarget === ["']image["']/);
assert.match(promptSource, /files\.find\(isJsonFile\)/);
assert.match(promptSource, /isEditableTarget\(event\.target\)/);
assert.match(promptSource, /Comfy\.Locale/);
assert.match(promptSource, /Ctrl\+V/);
assert.match(promptSource, /\\u840c\\u5b9dAI\\u00b7/);
assert.doesNotMatch(promptSource, /manager:\s*["']WANG/);

console.log("Frontend node pack tests passed.");
