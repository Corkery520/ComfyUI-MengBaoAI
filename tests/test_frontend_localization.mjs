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
  "\nexport { addReferenceInput, applyLocalization, configureNode, extractApiKey, formatBalance, normalizeLanguage, openRegistration, referenceInputs, refreshBalance, removeReferenceInput, saveApiKey, showFeedback, updateDefaultPrompt, updateVisibility };\n";

const localeState = { value: "en" };
const localeSetting = {
  onChange() {},
};
let registeredExtension;
let openedUrl;
let alertMessage;
const apiEventListeners = {};

globalThis.window = {
  open(url) {
    openedUrl = url;
  },
  alert(message) {
    alertMessage = message;
  },
};

globalThis.__mengBaoTestApi = {
  addEventListener(name, callback) {
    apiEventListeners[name] = callback;
  },
  async fetchApi() {
    throw new Error("Unexpected API request");
  },
};

globalThis.__mengBaoTestApp = {
  graph: {
    _nodes: [],
    setDirtyCanvas() {},
    getNodeById(id) {
      return this._nodes.find((node) => String(node.id) === String(id));
    },
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
    tt2_aspect_ratio: "auto",
    tt2_resolution: "auto",
    tt2_background: "opaque",
    tt2_quality: "auto",
    tt25_version: "flare",
    tt25_aspect_ratio: "auto",
    tt25_resolution: "auto",
    tt25_quality: "auto",
    tt25_background: "opaque",
    banana2_aspect_ratio: "1:1",
    banana2_image_size: "1K",
    banana2_thinking_level: "minimal",
    banana_pro_aspect_ratio: "1:1",
    banana_pro_image_size: "1K",
    timeout: 600,
    retries: 2,
    ui_language: "en",
  };
  return {
    id: Math.floor(Math.random() * 100000),
    _mengBaoNode: true,
    _mengBaoInitialBalanceRefreshed: true,
    widgets: Object.entries(values).map(([name, value]) => makeWidget(name, value)),
    inputs: Array.from({ length: 16 }, (_, index) => ({
      name: `image_${index + 1}`,
      type: "IMAGE",
      link: null,
    })),
    outputs: [{ name: "images" }, { name: "text" }, { name: "failed_urls" }],
    size: [300, 400],
    computeSize() {
      return [300, 400];
    },
    setSize(size) {
      this.size = size;
    },
    addInput(name, type) {
      const input = { name, type, link: null };
      this.inputs.push(input);
      return input;
    },
    removeInput(index) {
      this.inputs.splice(index, 1);
    },
    setDirtyCanvas() {},
  };
}

function widget(node, name) {
  return node.widgets.find((item) => item.name === name);
}

function waitForUpdates(delay = 10) {
  return new Promise((resolve) => setTimeout(resolve, delay));
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
  assert.equal(widget(node, "connection_json").hidden, true);
}

const legacyNode = makeNode();
widget(legacyNode, "tt2_size").value = "自动";
localization.configureNode(legacyNode);
assert.equal(widget(legacyNode, "tt2_size").value, "auto");
assert.equal(localization.referenceInputs(legacyNode).length, 3);

localization.addReferenceInput(legacyNode);
assert.equal(localization.referenceInputs(legacyNode).length, 4);
assert.equal(legacyNode.inputs.at(-1).name, "image_4");
localization.removeReferenceInput(legacyNode);
assert.equal(localization.referenceInputs(legacyNode).length, 3);
localization.removeReferenceInput(legacyNode);
assert.equal(localization.referenceInputs(legacyNode).length, 3);
for (let count = 3; count < 14; count += 1) {
  localization.addReferenceInput(legacyNode);
}
assert.equal(localization.referenceInputs(legacyNode).length, 14);
localization.addReferenceInput(legacyNode);
assert.equal(localization.referenceInputs(legacyNode).length, 14);

widget(legacyNode, "model_type").value = "gpt-image-2.5";
localization.updateVisibility(legacyNode);
localization.addReferenceInput(legacyNode);
localization.addReferenceInput(legacyNode);
assert.equal(localization.referenceInputs(legacyNode).length, 16);

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

const expandedWorkflowNode = makeNode();
localization.configureNode(expandedWorkflowNode, {
  inputs: Array.from({ length: 8 }, (_, index) => ({ name: `image_${index + 1}` })),
});
assert.equal(localization.referenceInputs(expandedWorkflowNode).length, 8);

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

widget(accountNode, "api_key").value = '{"_type":"newapi_channel_conn","key":"json-key"}';
assert.equal(localization.extractApiKey(accountNode), "json-key");
widget(accountNode, "connection_json").value = '{"key":"legacy-key"}';
assert.equal(localization.extractApiKey(accountNode), "json-key");
widget(accountNode, "api_key").value = "";
assert.equal(localization.extractApiKey(accountNode), "legacy-key");

let balanceRequest;
let balanceRequestCount = 0;
globalThis.__mengBaoTestApi.fetchApi = async (url, options) => {
  balanceRequest = { url, options };
  balanceRequestCount += 1;
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

const saveNode = makeNode();
widget(saveNode, "api_key").value = "save-this-key";
const saveRequests = [];
globalThis.__mengBaoTestApi.fetchApi = async (url, options) => {
  saveRequests.push({ url, options });
  return {
    ok: true,
    async json() {
      return url === "/mengbao_image_api/api_key"
        ? { saved: true }
        : { data: { balance: 31.25, currency: "CNY" } };
    },
  };
};
await localization.saveApiKey(saveNode);
assert.deepEqual(
  saveRequests.map((request) => request.url),
  ["/mengbao_image_api/api_key", "/mengbao_image_api/balance"]
);
assert.equal(JSON.parse(saveRequests[0].options.body).api_key, "save-this-key");
assert.equal(saveNode._mengBaoBalanceState.value, "31.25 CNY");

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
  const domWidget = { name, type, root, options };
  this.widgets.push(domWidget);
  return domWidget;
};
localization.configureNode(domNode);
assert.equal(domNode._mengBaoReferenceControls.addButton.style.background, "#477ac1");
assert.match(domNode._mengBaoReferenceControls.addButton.textContent, /4 \(3\/14\)/);
assert.equal(domNode._mengBaoReferenceControls.removeButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoReferenceControls.removeButton.disabled, true);
assert.equal(typeof domNode._mengBaoReferenceControls.addButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoReferenceControls.removeButton.listeners.click, "function");
domNode._mengBaoReferenceControls.addButton.listeners.click();
assert.equal(localization.referenceInputs(domNode).length, 4);
assert.equal(domNode._mengBaoReferenceControls.removeButton.disabled, false);
domNode._mengBaoReferenceControls.removeButton.listeners.click();
assert.equal(localization.referenceInputs(domNode).length, 3);
assert.equal(domNode._mengBaoReferenceControls.removeButton.disabled, true);
domNode._mengBaoReferenceControls.removeButton.listeners.click();
assert.equal(localization.referenceInputs(domNode).length, 3);
assert.equal(domNode._mengBaoAccountControls.registerButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoAccountControls.saveButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoAccountControls.refreshButton.style.background, "#477ac1");
assert.equal(domNode._mengBaoAccountControls.feedbackButton.style.background, "#477ac1");
assert.equal(typeof domNode._mengBaoAccountControls.registerButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoAccountControls.saveButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoAccountControls.refreshButton.listeners.click, "function");
assert.equal(typeof domNode._mengBaoAccountControls.feedbackButton.listeners.click, "function");

const initialBalanceNode = makeNode();
delete initialBalanceNode._mengBaoInitialBalanceRefreshed;
widget(initialBalanceNode, "api_key").value = "initial-key";
let initialBalanceRequests = 0;
globalThis.__mengBaoTestApi.fetchApi = async () => {
  initialBalanceRequests += 1;
  return {
    ok: true,
    async json() {
      return { data: { balance: 20, currency: "CNY" } };
    },
  };
};
localization.configureNode(initialBalanceNode);
await waitForUpdates(130);
assert.equal(initialBalanceRequests, 1);
assert.deepEqual(initialBalanceNode._mengBaoBalanceState, {
  kind: "value",
  value: "20 CNY",
});

const liveNode = makeNode();
globalThis.__mengBaoTestApp.graph._nodes = [liveNode];
await registeredExtension.setup();
await waitForUpdates();
assert.equal(liveNode.title, "MengBao AI · Image Generation");

localeState.value = "zh-CN";
localeSetting.onChange("zh-CN");
await waitForUpdates();
assert.equal(liveNode.title, "萌宝AI·图像生成");
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
assert.equal(liveNode.title, "MengBao AI · Image Generation");
assert.equal(widget(liveNode, "prompt").value, "不要改写这条自定义提示词");
assert.equal(widget(liveNode, "ui_language").value, "en");

widget(liveNode, "api_key").value = "execution-key";
let automaticBalanceRequests = 0;
globalThis.__mengBaoTestApi.fetchApi = async () => {
  automaticBalanceRequests += 1;
  return {
    ok: true,
    async json() {
      return { data: { balance: 12, currency: "CNY" } };
    },
  };
};
apiEventListeners.executed({ detail: { node: String(liveNode.id) } });
await waitForUpdates();
assert.equal(automaticBalanceRequests, 1);
assert.deepEqual(liveNode._mengBaoBalanceState, { kind: "value", value: "12 CNY" });

console.log("Frontend localization tests passed.");
