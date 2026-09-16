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

const collageNode = {
  type: "MengBaoSmartCollage",
  widgets: [],
  inputs: [{ name: "image_1" }, { name: "image_4" }],
  outputs: [{ name: "image" }],
  setDirtyCanvas() {},
};
localization.applyNodeLocalization(collageNode, "zh-CN");
assert.equal(collageNode.title, "萌宝AI智能拼图");
assert.equal(collageNode.inputs[0].label, "图片 1");
assert.equal(collageNode.outputs[0].label, "图像");

const constraintNode = {
  type: "MengBaoImageConstraint",
  widgets: [
    { name: "max_width", options: {} },
    { name: "crop_if_required", options: {} },
    { name: "max_file_size_mb", value: 10, options: {} },
  ],
  inputs: [{ name: "image" }],
  outputs: [{ name: "image" }],
  setDirtyCanvas() {},
};
localization.applyNodeLocalization(constraintNode, "en");
assert.equal(constraintNode.title, "MengBao AI · Image Constraint");
assert.equal(constraintNode.widgets[0].label, "Maximum Width");
assert.equal(constraintNode.widgets[1].options.getOptionLabel("yes"), "Yes");
assert.equal(constraintNode.inputs[0].label, "Image");
assert.equal(constraintNode.widgets[2].label, "Maximum File Size (MB)");
localization.applyNodeLocalization(constraintNode, "zh-CN");
assert.equal(constraintNode.widgets[2].label, "最大图片大小（MB）");
assert.equal(constraintNode.widgets[2].value, 10);
localization.applyNodeLocalization(constraintNode, "fr");
assert.equal(constraintNode.widgets[2].label, "Maximum File Size (MB)");

const ecommerceNode = {
  type: "MengBaoEcommerceSettings",
  widgets: [
    { name: "language", label: "language", value: "中文", options: {} },
    { name: "quantity", label: "quantity", value: 8, options: {} },
    { name: "usage", label: "usage", value: "详情页", options: {} },
    { name: "page_content", label: "page_content", value: "中等", options: {} },
    { name: "font_style", label: "font_style", value: "自动判断", options: {} },
    { name: "reverse_pages", label: "reverse_pages", value: "插入2张", options: {} },
    { name: "model_setting", label: "model_setting", value: "女性模特", options: {} },
    { name: "model_appearance_count", label: "model_appearance_count", value: "8", options: {} },
  ],
  inputs: [],
  outputs: [
    { name: "user_prompt" },
    { name: "aspect_ratio" },
    { name: "quantity" },
    { name: "settings_json" },
  ],
  setDirtyCanvas() {},
};
localization.configureEcommerceWidgets(ecommerceNode);
assert.deepEqual(
  ecommerceNode.widgets.find((widget) => widget.name === "reverse_pages").options.values,
  ["自动判断", "不插入", "插入1张", "插入2张"],
);
assert.equal(
  ecommerceNode.widgets.find((widget) => widget.name === "model_appearance_count").options.values.length,
  9,
);

ecommerceNode.widgets.find((widget) => widget.name === "quantity").value = 4;
ecommerceNode.widgets.find((widget) => widget.name === "quantity").callback();
assert.equal(
  ecommerceNode.widgets.find((widget) => widget.name === "reverse_pages").value,
  "插入1张",
);
assert.equal(
  ecommerceNode.widgets.find((widget) => widget.name === "model_appearance_count").value,
  "4",
);

ecommerceNode.widgets.find((widget) => widget.name === "model_setting").value = "不使用模特";
ecommerceNode.widgets.find((widget) => widget.name === "model_setting").callback();
assert.equal(
  ecommerceNode.widgets.find((widget) => widget.name === "model_appearance_count").value,
  "自动判断",
);

localization.applyNodeLocalization(ecommerceNode, "zh-CN");
assert.equal(ecommerceNode.title, "MengBao AI电商设置");
assert.equal(ecommerceNode.widgets[0].label, "语言");
assert.equal(ecommerceNode.widgets[1].options.getOptionLabel("详情页"), "详情页");
assert.equal(ecommerceNode.outputs[0].label, "用户提示词");

localization.applyNodeLocalization(ecommerceNode, "en");
assert.equal(ecommerceNode.title, "MengBao AI · E-commerce Settings");
assert.equal(ecommerceNode.widgets[0].label, "Language");
assert.equal(ecommerceNode.widgets[0].options.getOptionLabel("中文"), "Chinese");
assert.equal(ecommerceNode.widgets[1].options.getOptionLabel("详情页"), "Detail Pages");
assert.equal(ecommerceNode.widgets[2].options.getOptionLabel("中等"), "Standard");
assert.equal(ecommerceNode.outputs[0].label, "User Prompt");

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
