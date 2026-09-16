import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const sourceUrl = new URL("../web/MengBao_image_api_nodes_v4.js", import.meta.url);
const source = readFileSync(fileURLToPath(sourceUrl), "utf8");
const testableSource = source.replace(
  'import { app } from "../../../scripts/app.js";',
  "const app = globalThis.__mengBaoTestApp;"
).replace(
  'import { api } from "../../../scripts/api.js";',
  "const api = globalThis.__mengBaoTestApi;"
) +
  "\nexport { applyLocalization, configureNode, formatBalance, normalizeLanguage, openRegistration, refreshBalance, showFeedback, updateDefaultPrompt, updateVisibility };\n";

const localeState = { value: "en" };
const localeSetting = {
  onChange() {},
};
let registeredExtension;
let openedUrl;
let alertMessage;

globalThis.window = {
  open(url) {
    openedUrl = url;
  },
  alert(message) {
    alertMessage = message;
  },
};

globalThis.__mengBaoTestApi = {
  async fetchApi() {
    throw new Error("Unexpected API request");
  },
};

globalThis.__mengBaoTestApp = {
  graph: {
    _nodes: [],
    setDirtyCanvas() {},
  },
  ui: {
    settings: {
      getSettingValue(name) {
        return name === "Comfy.Locale" ? localeState.value : undefined;
      },
      settingsLookup: {
        "Comfy.Locale": localeSetting,
      },
    },
  },
  registerExtension(extension) {
    registeredExtension = extension;
  },
};

const moduleUrl = `data:text/javascript;base64,${Buffer.from(testableSource).toString("base64")}`;
const localization = await import(moduleUrl);

function makeWidget(name, value) {
  return {
    name,
    value,
    type: "combo",
    options: {},
    computeSize() {
      return [300, 24];
    },
  };
}

function makeNode(model = "gpt-image-2", prompt = "Generate a cinematic image") {
  const values = {
    prompt,
    connection_json: "",
    api_key: "",
    model_type: model,
    tt2_size: "auto",
    tt2_aspect_ratio: "1:1",
    tt2_resolution: "1K",
    tt2_background: "opaque",
    tt2_quality: "auto",
    tt25_version: "flare",
    tt25_aspect_ratio: "1:1",
    tt25_resolution: "1K",
    tt25_quality: "auto",
    tt25_background: "opaque",
    banana2_aspect_ratio: "1:1",
    banana2_image_size: "1K",
    banana2_thinking_level: "minimal",
    banana_pro_aspect_ratio: "1:1",
    banana_pro_image_size: "1K",
    ui_language: "en",
  };
  return {
    _mengBaoNode: true,
    widgets: Object.entries(values).map(([name, value]) => makeWidget(name, value)),
    inputs: [{ name: "image_1" }],
    outputs: [{ name: "images" }, { name: "text" }, { name: "failed_urls" }],
    size: [300, 400],
    computeSize() {
      return [300, 400];
    },
    setSize(size) {
      this.size = size;
    },
  };
}

function widget(node, name) {
  return node.widgets.find((item) => item.name === name);
}

function waitForUpdates() {
  return new Promise((resolve) => setTimeout(resolve, 10));
}

assert.equal(localization.normalizeLanguage("zh-CN"), "zh");
assert.equal(localization.normalizeLanguage("zh-TW"), "zh");
assert.equal(localization.normalizeLanguage("fr"), "en");

const defaultPrompt = makeWidget("prompt", "Generate a cinematic image");
localization.updateDefaultPrompt(defaultPrompt, "zh");
assert.equal(defaultPrompt.value, "生成一张电影感图片");
const customPrompt = makeWidget("prompt", "自定义提示词");
localization.updateDefaultPrompt(customPrompt, "en");
assert.equal(customPrompt.value, "自定义提示词");

const modelVisibility = {
  "gpt-image-2": [
    "tt2_aspect_ratio",
    "tt2_resolution",
    "tt2_background",
    "tt2_quality",
  ],
  "gpt-image-2.5": [
    "tt25_version",
    "tt25_aspect_ratio",
    "tt25_resolution",
    "tt25_quality",
    "tt25_background",
  ],
  "nano-banana-2": [
    "banana2_aspect_ratio",
    "banana2_image_size",
    "banana2_thinking_level",
  ],
  "nano-banana-2-pro": ["banana_pro_aspect_ratio", "banana_pro_image_size"],
};

for (const [model, visibleNames] of Object.entries(modelVisibility)) {
  const node = makeNode(model);
  localization.updateVisibility(node);
  for (const name of Object.values(modelVisibility).flat()) {
    assert.equal(widget(node, name).hidden, !visibleNames.includes(name), `${model}: ${name}`);
  }
  assert.equal(widget(node, "ui_language").hidden, true);
  assert.equal(widget(node, "tt2_size").hidden, true);
}

const legacyNode = makeNode();
widget(legacyNode, "tt2_size").value = "自动";
localization.configureNode(legacyNode);
assert.equal(widget(legacyNode, "tt2_size").value, "auto");

const migratedWorkflowNode = makeNode();
localization.configureNode(migratedWorkflowNode, {
  widgets_values: [
    "旧提示词",
    "",
    "test-key",
    "gpt-image-2",
    1,
    "2K 9:16 1440x2560",
    "high",
    "sunburst",
    "16:9",
    "2K",
    "max",
    "transparent",
    "9:16",
    "2K",
    "high",
    "16:9",
    "4K",
    420,
    3,
    "zh",
  ],
});
assert.equal(widget(migratedWorkflowNode, "tt2_aspect_ratio").value, "9:16");
assert.equal(widget(migratedWorkflowNode, "tt2_resolution").value, "2K");
assert.equal(widget(migratedWorkflowNode, "tt2_background").value, "opaque");
assert.equal(widget(migratedWorkflowNode, "tt2_quality").value, "high");
assert.equal(widget(migratedWorkflowNode, "tt25_version").value, "sunburst");

const transparentNode = makeNode("gpt-image-2", "产品摄影");
widget(transparentNode, "tt2_background").value = "transparent";
localization.applyLocalization(transparentNode, "zh");
localization.applyLocalization(transparentNode, "zh");
const transparentInstruction =
  "精确提取当前图片主体，仅移除主体外背景，输出带真实 Alpha 通道的透明 PNG。" +
  "禁止绘制棋盘格、马赛克、白底或其他模拟透明背景。";
assert.equal(widget(transparentNode, "prompt").value.match(new RegExp(transparentInstruction, "g")).length, 1);
widget(transparentNode, "tt2_background").value = "opaque";
localization.applyLocalization(transparentNode, "zh");
assert.equal(widget(transparentNode, "prompt").value, "产品摄影");

assert.equal(localization.formatBalance({ data: { balance: 18.75, currency: "CNY" } }), "18.75 CNY");
localization.openRegistration();
assert.equal(openedUrl, "https://corkery.ai/api/console/keys");
localization.showFeedback();
assert.equal(alertMessage, "有bug和使用问题请联系微信：Corkery520");

const accountNode = makeNode();
accountNode._mengBaoLanguage = "zh";
await localization.refreshBalance(accountNode);
assert.equal(alertMessage, "请先输入 API Key 密钥，再刷新余额。");
assert.equal(accountNode._mengBaoBalanceState.kind, "error");

let balanceRequest;
globalThis.__mengBaoTestApi.fetchApi = async (url, options) => {
  balanceRequest = { url, options };
  return {
    ok: true,
    async json() {
      return { data: { balance: 28.5, currency: "CNY" } };
    },
  };
};
widget(accountNode, "api_key").value = "test-key";
await localization.refreshBalance(accountNode);
assert.equal(balanceRequest.url, "/mengbao_image_api/balance");
assert.equal(JSON.parse(balanceRequest.options.body).api_key, "test-key");
assert.deepEqual(accountNode._mengBaoBalanceState, { kind: "value", value: "28.5 CNY" });

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.style = {};
    this.listeners = {};
    this.children = [];
    this.textContent = "";
  }
  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }
  append(...children) {
    this.children.push(...children);
  }
}

globalThis.document = {
  createElement(tagName) {
    return new FakeElement(tagName);
  },
};
const domNode = makeNode();
domNode.addDOMWidget = function (name, type, root, options) {
  this.domWidget = { name, type, root, options };
  return this.domWidget;
};
localization.configureNode(domNode);
assert.equal(domNode._mengBaoAccountControls.registerButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoAccountControls.refreshButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoAccountControls.feedbackButton.style.background, "#477ac1");
assert.equal(typeof domNode._mengBaoAccountControls.registerButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoAccountControls.refreshButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoAccountControls.feedbackButton.listeners.click, "function");

const liveNode = makeNode();
globalThis.__mengBaoTestApp.graph._nodes = [liveNode];
await registeredExtension.setup();
await waitForUpdates();
assert.equal(liveNode.title, "MengBao-Image-API");

localeState.value = "zh-CN";
localeSetting.onChange("zh-CN");
await waitForUpdates();
assert.equal(liveNode.title, "萌宝图像 API");
assert.equal(widget(liveNode, "prompt").value, "生成一张电影感图片");
assert.equal(widget(liveNode, "ui_language").value, "zh");
assert.equal(widget(liveNode, "tt2_size").value, "auto");
assert.equal(widget(liveNode, "tt2_size").options.getOptionLabel("auto"), "自动");
assert.equal(widget(liveNode, "tt25_version").options.getOptionLabel("flare"), "标准版");
assert.deepEqual(
  liveNode.outputs.map((output) => output.localized_name),
  ["图像", "响应文本", "失败 URL"]
);

widget(liveNode, "prompt").value = "不要改写这条自定义提示词";
localeState.value = "en-US";
localeSetting.onChange("en-US");
await waitForUpdates();
assert.equal(liveNode.title, "MengBao-Image-API");
assert.equal(widget(liveNode, "prompt").value, "不要改写这条自定义提示词");
assert.equal(widget(liveNode, "ui_language").value, "en");

console.log("Frontend localization tests passed.");
