import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { applyNodeLocalization, normalizeLanguage } from "./node_localization.js";

const NODE_CLASS = "MengBaoGlobalAPIKey";
const KEY_ENDPOINT = "/mengbao_image_api/api_key";
const KEY_CHANGED_EVENT = "mengbao-api-key-changed";
const LABELS = {
  en: {
    input: "API Key", save: "Save Global API Key", clear: "Clear Global API Key",
    loading: "Checking global API Key...", saving: "Saving...", clearing: "Clearing...",
    saved: "Global API Key saved", cleared: "Global API Key cleared", unset: "Global API Key not set",
    required: "api_key is empty", confirm: "Clear the saved global API Key?",
  },
  zh: {
    input: "API 密钥", save: "保存全局API Key", clear: "清除全局API Key",
    loading: "正在查询全局API Key...", saving: "正在保存...", clearing: "正在清除...",
    saved: "全局API Key已保存", cleared: "全局API Key已清除", unset: "未设置全局API Key",
    required: "请先输入API密钥", confirm: "确定清除已保存的全局API Key吗？",
  },
};

function currentLanguage() {
  return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale"));
}

function isManager(node) {
  return (node?.comfyClass || node?.type || node?.constructor?.comfyClass) === NODE_CLASS;
}

function busy(node) {
  return ["loading", "saving", "clearing"].includes(node._mengBaoGlobalKeyState?.kind);
}

function renderControls(node, language = currentLanguage()) {
  const controls = node._mengBaoGlobalKeyControls;
  if (!controls) return;
  const labels = LABELS[normalizeLanguage(language)];
  const state = node._mengBaoGlobalKeyState || { kind: "loading" };
  controls.input.placeholder = labels.input;
  controls.input.setAttribute("aria-label", labels.input);
  controls.input.disabled = busy(node);
  controls.saveButton.textContent = state.kind === "saving" ? labels.saving : labels.save;
  controls.clearButton.textContent = state.kind === "clearing" ? labels.clearing : labels.clear;
  controls.saveButton.disabled = busy(node) || !controls.input.value.trim();
  controls.clearButton.disabled = busy(node) || state.saved !== true;
  for (const button of [controls.saveButton, controls.clearButton]) {
    button.style.opacity = button.disabled ? "0.65" : "1";
    button.style.cursor = button.disabled ? "not-allowed" : "pointer";
  }
  controls.status.textContent = state.kind === "error" ? state.error : labels[state.kind] || labels.unset;
  controls.status.title = controls.status.textContent;
  controls.status.style.color = state.kind === "error" ? "#ff8f8f" : "#d7d7d7";
  node.setDirtyCanvas?.(true, true);
}

async function responseStatus(response) {
  const payload = await response.json();
  if (!response.ok || payload?.error || typeof payload?.saved !== "boolean") {
    throw new Error(String(payload?.error?.message || response.statusText || `HTTP ${response.status || 500}`));
  }
  return payload.saved;
}

async function loadStatus(node) {
  const sequence = (node._mengBaoGlobalKeyStatusSequence || 0) + 1;
  node._mengBaoGlobalKeyStatusSequence = sequence;
  node._mengBaoGlobalKeyState = { ...node._mengBaoGlobalKeyState, kind: "loading" };
  renderControls(node);
  try {
    const saved = await responseStatus(await api.fetchApi(KEY_ENDPOINT));
    if (sequence !== node._mengBaoGlobalKeyStatusSequence) return;
    node._mengBaoGlobalKeyState = { kind: saved ? "saved" : "unset", saved };
  } catch (error) {
    if (sequence !== node._mengBaoGlobalKeyStatusSequence) return;
    node._mengBaoGlobalKeyState = { ...node._mengBaoGlobalKeyState, kind: "error", error: error.message || String(error) };
  }
  renderControls(node);
}

async function updateKey(node, action) {
  if (busy(node)) return;
  const controls = node._mengBaoGlobalKeyControls;
  const labels = LABELS[currentLanguage()];
  const key = controls.input.value.trim();
  if (action === "save" && !key) {
    node._mengBaoGlobalKeyState = { ...node._mengBaoGlobalKeyState, kind: "error", error: labels.required };
    renderControls(node);
    return;
  }
  if (action === "clear" && (node._mengBaoGlobalKeyState.saved !== true || !window.confirm(labels.confirm))) return;
  node._mengBaoGlobalKeyState = { ...node._mengBaoGlobalKeyState, kind: action === "save" ? "saving" : "clearing" };
  renderControls(node);
  try {
    const saved = await responseStatus(await api.fetchApi(KEY_ENDPOINT, {
      method: action === "save" ? "POST" : "DELETE",
      ...(action === "save" ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ api_key: key }) } : {}),
    }));
    if (saved !== (action === "save")) throw new Error("Unexpected API Key status");
    controls.input.value = "";
    node._mengBaoGlobalKeyState = { kind: saved ? "saved" : "cleared", saved };
    // 只广播是否已保存，不把密钥放进事件、状态文字或工作流。
    api.dispatchEvent(new CustomEvent(KEY_CHANGED_EVENT, { detail: { saved } }));
  } catch (error) {
    node._mengBaoGlobalKeyState = { ...node._mengBaoGlobalKeyState, kind: "error", error: error.message || String(error) };
  }
  renderControls(node);
}

function ensureControls(node) {
  if (node._mengBaoGlobalKeyControls || typeof document === "undefined" || typeof node.addDOMWidget !== "function") return;
  const root = document.createElement("div");
  Object.assign(root.style, { display: "flex", flexDirection: "column", gap: "8px", width: "100%", padding: "4px 0", boxSizing: "border-box" });
  const input = document.createElement("input");
  input.type = "password";
  input.autocomplete = "off";
  input.spellcheck = false;
  Object.assign(input.style, { width: "100%", height: "30px", padding: "0 12px", boxSizing: "border-box", border: "1px solid #666666", borderRadius: "6px", background: "#222222", color: "#ffffff", fontSize: "13px" });
  input.addEventListener("input", () => renderControls(node));
  const row = document.createElement("div");
  Object.assign(row.style, { display: "flex", gap: "8px", width: "100%" });
  function button(action, color) {
    const element = document.createElement("button");
    element.type = "button";
    Object.assign(element.style, { flex: "1 1 0", minWidth: "0", minHeight: "32px", border: "0", borderRadius: "6px", background: color, color: "#ffffff", fontSize: "13px", overflowWrap: "anywhere" });
    element.addEventListener("click", () => updateKey(node, action));
    return element;
  }
  const saveButton = button("save", "#477ac1");
  const clearButton = button("clear", "#c65645");
  row.append(saveButton, clearButton);
  const status = document.createElement("div");
  status.setAttribute("role", "status");
  Object.assign(status.style, { fontSize: "12px", height: "18px", lineHeight: "18px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" });
  root.append(input, row, status);
  const widget = node.addDOMWidget("mengbao_global_key_controls", "mengbao-global-key-controls", root, {
    serialize: false, hideOnZoom: false, getMinHeight: () => 108, getMaxHeight: () => 108,
  });
  node._mengBaoGlobalKeyControls = { input, saveButton, clearButton, status, widget, render: (language) => renderControls(node, language) };
}

function configureNode(node) {
  const keyWidget = node.widgets?.find(({ name }) => name === "api_key");
  if (keyWidget) {
    keyWidget.value = "";
    keyWidget.hidden = true;
    keyWidget.type = "hidden";
    keyWidget.computeSize = () => [0, -4];
    keyWidget.serializeValue = () => "";
  }
  ensureControls(node);
  if (node._mengBaoGlobalKeyControls) node._mengBaoGlobalKeyControls.input.value = "";
  applyNodeLocalization(node);
  const size = node.computeSize?.();
  if (size) node.setSize?.([Math.max(480, node.size?.[0] || 0, size[0]), size[1]]);
  node._mengBaoGlobalKeyStatusPromise = loadStatus(node);
}

app.registerExtension({
  name: "MengBaoAI.global_api_key",
  async setup() {
    api.addEventListener(KEY_CHANGED_EVENT, ({ detail }) => {
      if (typeof detail?.saved !== "boolean") return;
      for (const node of app.graph?._nodes || []) {
        if (!isManager(node)) continue;
        node._mengBaoGlobalKeyStatusSequence = (node._mengBaoGlobalKeyStatusSequence || 0) + 1;
        const actionPending = ["saving", "clearing"].includes(node._mengBaoGlobalKeyState?.kind);
        node._mengBaoGlobalKeyState = actionPending
          ? { ...node._mengBaoGlobalKeyState, saved: detail.saved }
          : { kind: detail.saved ? "saved" : "cleared", saved: detail.saved };
        renderControls(node);
      }
    });
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      configureNode(this);
      return result;
    };
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      configureNode(this);
      return result;
    };
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      const result = onExecuted?.apply(this, arguments);
      if (!busy(this) && typeof message?.saved?.[0] === "boolean") {
        this._mengBaoGlobalKeyState = { kind: message.saved[0] ? "saved" : "unset", saved: message.saved[0] };
        renderControls(this);
      }
      return result;
    };
  },
});
