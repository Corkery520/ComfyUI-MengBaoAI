import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_CLASS = "WANGImageAPI";
const REGISTRATION_URL = "https://corkery.ai/api/console/keys";
const FEEDBACK_MESSAGE = "有bug和使用问题请联系微信：Corkery520";

const MODEL_WIDGETS = {
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
  "nano-banana-2-pro": [
    "banana_pro_aspect_ratio",
    "banana_pro_image_size",
  ],
};

const MODEL_SPECIFIC_WIDGETS = [...new Set(Object.values(MODEL_WIDGETS).flat())];
const ALWAYS_HIDDEN_WIDGETS = ["tt2_size", "ui_language"];
const LEGACY_WIDGET_NAMES = [
  "prompt",
  "connection_json",
  "api_key",
  "model_type",
  "batch_size",
  "tt2_size",
  "tt2_quality",
  "tt25_version",
  "tt25_aspect_ratio",
  "tt25_resolution",
  "tt25_quality",
  "tt25_background",
  "banana2_aspect_ratio",
  "banana2_image_size",
  "banana2_thinking_level",
  "banana_pro_aspect_ratio",
  "banana_pro_image_size",
  "timeout",
  "retries",
  "ui_language",
];

const DEFAULT_PROMPTS = {
  en: "Generate a cinematic image",
  zh: "生成一张电影感图片",
};

const TRANSPARENT_BACKGROUND_PROMPTS = {
  en:
    "Precisely isolate the current image subject and remove only the background outside " +
    "the subject. Output a transparent PNG with a real Alpha channel. Do not draw a " +
    "checkerboard, mosaic, white background, or any other simulated transparency.",
  zh:
    "精确提取当前图片主体，仅移除主体外背景，输出带真实 Alpha 通道的透明 PNG。" +
    "禁止绘制棋盘格、马赛克、白底或其他模拟透明背景。",
};

const TRANSLATIONS = {
  en: {
    title: "MengBao-Image-API",
    description: "Generate and edit images with TT Image and Nano Banana models.",
    widgets: {
      prompt: "Prompt",
      connection_json: "Connection JSON",
      api_key: "API Key",
      model_type: "Model",
      batch_size: "Batch Size",
      tt2_size: "Legacy Size",
      tt2_aspect_ratio: "Aspect Ratio",
      tt2_resolution: "Resolution",
      tt2_background: "Background",
      tt2_quality: "Quality",
      tt25_version: "Version",
      tt25_aspect_ratio: "Aspect Ratio",
      tt25_resolution: "Resolution",
      tt25_quality: "Quality",
      tt25_background: "Background",
      banana2_aspect_ratio: "Aspect Ratio",
      banana2_image_size: "Image Size",
      banana2_thinking_level: "Thinking Level",
      banana_pro_aspect_ratio: "Aspect Ratio",
      banana_pro_image_size: "Image Size",
      timeout: "Timeout (seconds)",
      retries: "Retries",
      ui_language: "UI Language",
    },
    inputs: {
      image_1: "Reference Image 1",
      image_2: "Reference Image 2",
      image_3: "Reference Image 3",
      image_4: "Reference Image 4",
      image_5: "Reference Image 5",
    },
    outputs: {
      images: "Images",
      text: "Response",
      failed_urls: "Failed URLs",
    },
    options: {
      auto: "auto",
      flare: "flare",
      sunburst: "sunburst",
      high: "high",
      medium: "medium",
      low: "low",
      xhigh: "xhigh",
      max: "max",
      opaque: "opaque",
      transparent: "transparent",
      minimal: "minimal",
    },
    account: {
      balance: "Balance",
      empty: "No cached balance. Click Refresh Balance.",
      register: "Register API",
      refresh: "Refresh Balance",
      feedback: "Feedback",
      refreshing: "Refreshing...",
      apiKeyRequired: "Enter an API Key before refreshing the balance.",
    },
  },
  zh: {
    title: "萌宝图像 API",
    description: "使用 TT Image 与 Nano Banana 模型生成和编辑图像。",
    widgets: {
      prompt: "提示词",
      connection_json: "连接 JSON",
      api_key: "API 密钥",
      model_type: "模型",
      batch_size: "生成数量",
      tt2_size: "旧版尺寸",
      tt2_aspect_ratio: "图片比例",
      tt2_resolution: "分辨率",
      tt2_background: "背景",
      tt2_quality: "图片质量",
      tt25_version: "模型版本",
      tt25_aspect_ratio: "图片比例",
      tt25_resolution: "分辨率",
      tt25_quality: "图片质量",
      tt25_background: "背景",
      banana2_aspect_ratio: "图片比例",
      banana2_image_size: "图像尺寸",
      banana2_thinking_level: "思考等级",
      banana_pro_aspect_ratio: "图片比例",
      banana_pro_image_size: "图像尺寸",
      timeout: "超时时间（秒）",
      retries: "重试次数",
      ui_language: "界面语言",
    },
    inputs: {
      image_1: "参考图 1",
      image_2: "参考图 2",
      image_3: "参考图 3",
      image_4: "参考图 4",
      image_5: "参考图 5",
    },
    outputs: {
      images: "图像",
      text: "响应文本",
      failed_urls: "失败 URL",
    },
    options: {
      auto: "自动",
      flare: "标准版",
      sunburst: "增强版",
      high: "高",
      medium: "中",
      low: "低",
      xhigh: "超高",
      max: "极致",
      opaque: "不透明",
      transparent: "透明",
      minimal: "最小",
    },
    account: {
      balance: "余额",
      empty: "暂无余额缓存，请点击“刷新余额”按钮刷新",
      register: "注册API",
      refresh: "刷新余额",
      feedback: "问题反馈",
      refreshing: "查询中...",
      apiKeyRequired: "请先输入 API Key 密钥，再刷新余额。",
    },
  },
};

const LOCALIZED_OPTION_WIDGETS = new Set([
  "tt2_size",
  "tt2_aspect_ratio",
  "tt2_resolution",
  "tt2_background",
  "tt2_quality",
  "tt25_version",
  "tt25_aspect_ratio",
  "tt25_resolution",
  "tt25_quality",
  "tt25_background",
  "banana2_thinking_level",
]);

function normalizeLanguage(locale) {
  return String(locale || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function currentLanguage() {
  return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale"));
}

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function rememberWidget(widget) {
  if (!widget || widget._mengBaoOriginal) {
    return;
  }
  widget._mengBaoOriginal = {
    type: widget.type,
    computeSize: widget.computeSize,
  };
}

function setWidgetVisible(widget, visible) {
  if (!widget) {
    return;
  }
  rememberWidget(widget);
  widget.hidden = !visible;
  widget.type = visible ? widget._mengBaoOriginal.type : "hidden";
  widget.computeSize = visible ? widget._mengBaoOriginal.computeSize : () => [0, -4];
}

function resizeNode(node) {
  const computed = node.computeSize?.();
  if (!computed) {
    return;
  }
  node.setSize?.([Math.max(node.size?.[0] || 0, computed[0]), computed[1]]);
  app.graph?.setDirtyCanvas(true, true);
}

function updateVisibility(node) {
  const selectedModel = findWidget(node, "model_type")?.value;
  const visibleNames = new Set(MODEL_WIDGETS[selectedModel] || []);

  for (const name of MODEL_SPECIFIC_WIDGETS) {
    setWidgetVisible(findWidget(node, name), visibleNames.has(name));
  }
  for (const name of ALWAYS_HIDDEN_WIDGETS) {
    setWidgetVisible(findWidget(node, name), false);
  }
  node._mengBaoVisibleModel = selectedModel;
  resizeNode(node);
}

function setSocketLabel(socket, labels) {
  const label = labels[socket.name];
  if (!label) {
    return;
  }
  socket.localized_name = label;
  socket.label = label;
}

function localizeOptions(widget, translation) {
  if (!LOCALIZED_OPTION_WIDGETS.has(widget.name)) {
    return;
  }
  widget.options ||= {};
  widget.options.getOptionLabel = (value) => translation.options[value] ?? value;
}

function updateDefaultPrompt(widget, language) {
  if (!widget || !Object.values(DEFAULT_PROMPTS).includes(widget.value)) {
    return;
  }
  widget.value = DEFAULT_PROMPTS[language];
}

function removeTransparentInstructions(prompt) {
  let result = String(prompt || "");
  for (const instruction of Object.values(TRANSPARENT_BACKGROUND_PROMPTS)) {
    result = result.replaceAll(instruction, "");
  }
  return result.trimEnd();
}

function hasTransparentBackground(node) {
  const model = findWidget(node, "model_type")?.value;
  if (model === "gpt-image-2") {
    return findWidget(node, "tt2_background")?.value === "transparent";
  }
  if (model === "gpt-image-2.5") {
    return findWidget(node, "tt25_background")?.value === "transparent";
  }
  return false;
}

function updatePromptForState(node, language) {
  const promptWidget = findWidget(node, "prompt");
  if (!promptWidget) {
    return;
  }

  let basePrompt = removeTransparentInstructions(promptWidget.value);
  if (Object.values(DEFAULT_PROMPTS).includes(basePrompt)) {
    basePrompt = DEFAULT_PROMPTS[language];
  }
  if (hasTransparentBackground(node)) {
    const instruction = TRANSPARENT_BACKGROUND_PROMPTS[language];
    promptWidget.value = basePrompt ? `${basePrompt}\n${instruction}` : instruction;
  } else {
    promptWidget.value = basePrompt;
  }
}

function openRegistration() {
  window.open(REGISTRATION_URL, "_blank", "noopener,noreferrer");
}

function showFeedback() {
  window.alert(FEEDBACK_MESSAGE);
}

function formatBalance(payload) {
  const containers = [payload?.data, payload].filter(
    (value) => value && typeof value === "object"
  );
  const balanceKeys = [
    "balance",
    "available_balance",
    "availableBalance",
    "remaining",
    "credits",
    "amount",
  ];

  for (const container of containers) {
    for (const key of balanceKeys) {
      if (container[key] === undefined || container[key] === null) {
        continue;
      }
      const value =
        typeof container[key] === "object"
          ? container[key].amount ?? container[key].value
          : container[key];
      if (value === undefined || value === null) {
        continue;
      }
      const currency =
        container.currency ?? payload?.currency ?? payload?.data?.currency ?? "";
      return `${value}${currency ? ` ${currency}` : ""}`;
    }
  }
  return JSON.stringify(payload) ?? String(payload ?? "");
}

function extractApiKey(node) {
  const connectionJson = String(findWidget(node, "connection_json")?.value || "").trim();
  if (connectionJson.startsWith("{")) {
    try {
      const connection = JSON.parse(connectionJson);
      if (connection.key) {
        return String(connection.key).trim();
      }
    } catch {
      // 后端会保留原始连接 JSON 的错误处理，这里继续尝试独立 API Key。
    }
  }
  return String(findWidget(node, "api_key")?.value || "").trim();
}

function balanceErrorMessage(payload, response) {
  return String(
    payload?.error?.message ||
      payload?.message ||
      response?.statusText ||
      `HTTP ${response?.status || 500}`
  );
}

function renderAccountControls(node) {
  const controls = node._mengBaoAccountControls;
  if (!controls) {
    return;
  }
  const language = normalizeLanguage(node._mengBaoLanguage || currentLanguage());
  const labels = TRANSLATIONS[language].account;
  const state = node._mengBaoBalanceState || { kind: "empty", value: "" };

  controls.balanceLabel.textContent = labels.balance;
  controls.registerButton.textContent = labels.register;
  controls.feedbackButton.textContent = labels.feedback;
  controls.refreshButton.textContent =
    state.kind === "loading" ? labels.refreshing : labels.refresh;
  controls.refreshButton.disabled = state.kind === "loading";
  controls.refreshButton.style.opacity = state.kind === "loading" ? "0.65" : "1";
  controls.balanceValue.style.color = state.kind === "error" ? "#ff8f8f" : "#d7d7d7";

  if (state.kind === "empty") {
    controls.balanceValue.textContent = labels.empty;
  } else {
    controls.balanceValue.textContent = state.value;
  }
}

async function refreshBalance(node) {
  const language = normalizeLanguage(node._mengBaoLanguage || currentLanguage());
  const labels = TRANSLATIONS[language].account;
  if (!extractApiKey(node)) {
    node._mengBaoBalanceState = { kind: "error", value: labels.apiKeyRequired };
    renderAccountControls(node);
    window.alert(labels.apiKeyRequired);
    return;
  }
  if (node._mengBaoBalanceState?.kind === "loading") {
    return;
  }

  node._mengBaoBalanceState = { kind: "loading", value: labels.refreshing };
  renderAccountControls(node);
  try {
    const response = await api.fetchApi("/mengbao_image_api/balance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        connection_json: findWidget(node, "connection_json")?.value || "",
        api_key: findWidget(node, "api_key")?.value || "",
      }),
    });
    let payload;
    try {
      payload = await response.json();
    } catch {
      payload = { error: { message: await response.text() } };
    }
    if (!response.ok || payload?.error) {
      throw new Error(balanceErrorMessage(payload, response));
    }
    node._mengBaoBalanceState = { kind: "value", value: formatBalance(payload) };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    node._mengBaoBalanceState = { kind: "error", value: message };
    window.alert(message);
  }
  renderAccountControls(node);
  resizeNode(node);
}

function styleElement(element, styles) {
  Object.assign(element.style, styles);
  return element;
}

function createActionButton(label, onClick) {
  const button = styleElement(document.createElement("button"), {
    flex: "1 1 0",
    minWidth: "0",
    height: "28px",
    border: "0",
    borderRadius: "6px",
    background: "#477ac1",
    color: "#ffffff",
    cursor: "pointer",
    fontSize: "13px",
  });
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function ensureAccountControls(node) {
  if (
    node._mengBaoAccountControls ||
    typeof document === "undefined" ||
    typeof node.addDOMWidget !== "function"
  ) {
    return;
  }

  const language = currentLanguage();
  const labels = TRANSLATIONS[language].account;
  const root = styleElement(document.createElement("div"), {
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    width: "100%",
    minHeight: "62px",
    padding: "2px 0",
  });
  const balanceRow = styleElement(document.createElement("div"), {
    boxSizing: "border-box",
    display: "grid",
    gridTemplateColumns: "56px minmax(0, 1fr)",
    alignItems: "center",
    minHeight: "28px",
    padding: "0 10px",
    border: "1px solid #666666",
    borderRadius: "6px",
    background: "#222222",
    color: "#a9a9a9",
    fontSize: "12px",
  });
  const balanceLabel = document.createElement("span");
  const balanceValue = styleElement(document.createElement("span"), {
    overflow: "hidden",
    textAlign: "center",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  });
  balanceRow.append(balanceLabel, balanceValue);

  const buttonRow = styleElement(document.createElement("div"), {
    display: "flex",
    gap: "8px",
    width: "100%",
  });
  const registerButton = createActionButton(labels.register, openRegistration);
  const refreshButton = createActionButton(labels.refresh, () => refreshBalance(node));
  const feedbackButton = createActionButton(labels.feedback, showFeedback);
  buttonRow.append(registerButton, refreshButton, feedbackButton);
  root.append(balanceRow, buttonRow);

  node.addDOMWidget("mengbao_account", "mengbao-account", root, {
    serialize: false,
    hideOnZoom: false,
    getMinHeight: () => 66,
    getMaxHeight: () => 66,
  });
  node._mengBaoAccountControls = {
    balanceLabel,
    balanceValue,
    registerButton,
    refreshButton,
    feedbackButton,
  };
  node._mengBaoBalanceState ||= { kind: "empty", value: "" };
  renderAccountControls(node);
}

function applyLocalization(node, requestedLanguage = currentLanguage()) {
  const language = normalizeLanguage(requestedLanguage);
  const translation = TRANSLATIONS[language];
  const widgets = node.widgets || [];

  node.title = translation.title;
  node.description = translation.description;
  node._mengBaoLanguage = language;

  for (const widget of widgets) {
    widget.label = translation.widgets[widget.name] ?? widget.name;
    localizeOptions(widget, translation);
  }
  updatePromptForState(node, language);

  const languageWidget = findWidget(node, "ui_language");
  if (languageWidget) {
    languageWidget.value = language;
  }
  for (const input of node.inputs || []) {
    setSocketLabel(input, translation.inputs);
  }
  for (const output of node.outputs || []) {
    setSocketLabel(output, translation.outputs);
  }

  renderAccountControls(node);
  updateVisibility(node);
}

function scheduleUpdate(node) {
  setTimeout(() => applyLocalization(node), 0);
  setTimeout(() => applyLocalization(node), 100);
}

function wrapCallback(node, widget, afterChange) {
  if (!widget || widget._mengBaoCallbackWrapped) {
    return;
  }
  widget._mengBaoCallbackWrapped = true;
  const originalCallback = widget.callback;
  widget.callback = function (...args) {
    const result = originalCallback?.apply(this, args);
    afterChange?.(widget.value);
    scheduleUpdate(node);
    return result;
  };
}

function parseLegacySize(value) {
  if (value === "auto" || value === "自动") {
    return { aspectRatio: "auto", resolution: "auto" };
  }
  const match = String(value || "").match(/^(1K|2K|4K)\s+(\d+:\d+)/);
  return match
    ? { resolution: match[1], aspectRatio: match[2] }
    : { resolution: "1K", aspectRatio: "1:1" };
}

function migrateLegacyWorkflow(node, serializedNode) {
  const values = serializedNode?.widgets_values;
  if (!Array.isArray(values) || ![19, 20].includes(values.length)) {
    return;
  }

  const legacyNames = LEGACY_WIDGET_NAMES.slice(0, values.length);
  legacyNames.forEach((name, index) => {
    const target = findWidget(node, name);
    if (target) {
      target.value = values[index];
    }
  });
  const migrated = parseLegacySize(findWidget(node, "tt2_size")?.value);
  const aspectRatio = findWidget(node, "tt2_aspect_ratio");
  const resolution = findWidget(node, "tt2_resolution");
  const background = findWidget(node, "tt2_background");
  if (aspectRatio) aspectRatio.value = migrated.aspectRatio;
  if (resolution) resolution.value = migrated.resolution;
  if (background) background.value = "opaque";
}

function linkAutoPair(node, aspectName, resolutionName) {
  const aspectRatio = findWidget(node, aspectName);
  const resolution = findWidget(node, resolutionName);
  wrapCallback(node, aspectRatio, (value) => {
    if (value === "auto" && resolution) {
      resolution.value = "auto";
    }
  });
  wrapCallback(node, resolution, (value) => {
    if (value === "auto" && aspectRatio) {
      aspectRatio.value = "auto";
    }
  });
}

function configureNode(node, serializedNode) {
  node._mengBaoNode = true;
  migrateLegacyWorkflow(node, serializedNode);

  const legacySize = findWidget(node, "tt2_size");
  if (
    legacySize?.value === "自动" ||
    /^(1K|2K|4K)\s+\d+:\d+/.test(String(legacySize?.value || ""))
  ) {
    const migrated = parseLegacySize(legacySize.value);
    const aspectRatio = findWidget(node, "tt2_aspect_ratio");
    const resolution = findWidget(node, "tt2_resolution");
    if (aspectRatio) aspectRatio.value = migrated.aspectRatio;
    if (resolution) resolution.value = migrated.resolution;
    if (legacySize.value === "自动") legacySize.value = "auto";
  }

  ensureAccountControls(node);
  wrapCallback(node, findWidget(node, "model_type"));
  wrapCallback(node, findWidget(node, "tt2_background"));
  wrapCallback(node, findWidget(node, "tt25_background"));
  linkAutoPair(node, "tt2_aspect_ratio", "tt2_resolution");
  linkAutoPair(node, "tt25_aspect_ratio", "tt25_resolution");
  scheduleUpdate(node);
}

function isMengBaoNode(node) {
  return Boolean(
    node?._mengBaoNode ||
      node?.comfyClass === NODE_CLASS ||
      node?.type === NODE_CLASS ||
      node?.constructor?.comfyClass === NODE_CLASS
  );
}

function localizeExistingNodes() {
  const language = currentLanguage();
  for (const node of app.graph?._nodes || []) {
    if (isMengBaoNode(node)) {
      applyLocalization(node, language);
    }
  }
}

function installLocaleListener() {
  const localeSetting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
  if (!localeSetting || localeSetting._mengBaoListenerInstalled) {
    return;
  }

  localeSetting._mengBaoListenerInstalled = true;
  const originalOnChange = localeSetting.onChange;
  localeSetting.onChange = function (...args) {
    const result = originalOnChange?.apply(this, args);
    setTimeout(localizeExistingNodes, 0);
    return result;
  };
}

app.registerExtension({
  name: "MengBao.image_api_nodes.localization.v4",
  async setup() {
    installLocaleListener();
    setTimeout(localizeExistingNodes, 0);
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) {
      return;
    }

    nodeType.prototype._mengBaoNode = true;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      configureNode(this);
      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      configureNode(this, arguments[0]);
      return result;
    };

    const onDrawForeground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function () {
      const language = currentLanguage();
      const selectedModel = findWidget(this, "model_type")?.value;
      if (
        language !== this._mengBaoLanguage ||
        selectedModel !== this._mengBaoVisibleModel
      ) {
        applyLocalization(this, language);
      }
      return onDrawForeground?.apply(this, arguments);
    };
  },
});
