import { app } from "../../../scripts/app.js";
import { applyNodeLocalization, normalizeLanguage } from "./node_localization.js";

const NODE_CLASS = "MengBaoSmartCollage";
const DEFAULT_IMAGE_COUNT = 4;
const MAX_IMAGE_COUNT = 20;
const MIN_NODE_WIDTH = 560;
const LABELS = {
  en: { add: "Add Image", remove: "Remove Image", minimum: "Keep at least 4", limit: "Image limit reached" },
  zh: { add: "添加图片", remove: "删除图片", minimum: "最少保留 4 个", limit: "已达图片上限" },
};

function currentLanguage() {
  return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale"));
}

function imageInputs(node) {
  return (node.inputs || [])
    .map((input, index) => ({ input, index, number: Number(input.name?.match(/^image_(\d+)$/)?.[1]) }))
    .filter(({ number }) => number >= 1 && number <= MAX_IMAGE_COUNT)
    .sort((left, right) => left.number - right.number);
}

function nextImageNumber(node) {
  const used = new Set(imageInputs(node).map(({ number }) => number));
  for (let number = 1; number <= MAX_IMAGE_COUNT; number += 1) {
    if (!used.has(number)) return number;
  }
  return null;
}

function resizeNode(node) {
  if (typeof node.computeSize !== "function") return;
  const size = node.computeSize();
  node.setSize?.([Math.max(MIN_NODE_WIDTH, node.size?.[0] || 0, size[0]), size[1]]);
  node.setDirtyCanvas?.(true, true);
}

function renderControls(node, language = currentLanguage()) {
  const controls = node._mengBaoCollageControls;
  if (!controls) return;
  const labels = LABELS[normalizeLanguage(language)];
  const entries = imageInputs(node);
  const count = entries.length;
  const next = nextImageNumber(node);
  const addDisabled = count >= MAX_IMAGE_COUNT || next === null;
  const removeDisabled = count <= DEFAULT_IMAGE_COUNT;
  controls.addButton.textContent = addDisabled
    ? `${labels.limit} (${count}/${MAX_IMAGE_COUNT})`
    : `${labels.add} ${next} (${count}/${MAX_IMAGE_COUNT})`;
  controls.removeButton.textContent = removeDisabled
    ? `${labels.remove} (${labels.minimum})`
    : `${labels.remove} ${entries.at(-1).number} (${count}/${MAX_IMAGE_COUNT})`;
  for (const [button, disabled] of [[controls.addButton, addDisabled], [controls.removeButton, removeDisabled]]) {
    button.disabled = disabled;
    button.style.cursor = disabled ? "not-allowed" : "pointer";
    button.style.opacity = disabled ? "0.65" : "1";
  }
}

function addImage(node) {
  const number = nextImageNumber(node);
  if (number === null || typeof node.addInput !== "function") return;
  node.addInput(`image_${number}`, "IMAGE");
  applyNodeLocalization(node);
  resizeNode(node);
}

function removeImage(node) {
  const entries = imageInputs(node);
  if (entries.length <= DEFAULT_IMAGE_COUNT || typeof node.removeInput !== "function") return;
  // 使用 LiteGraph 原生删除方法，仅断开被删除的最后一个端口的连线。
  node.removeInput(entries.at(-1).index);
  applyNodeLocalization(node);
  resizeNode(node);
}

function ensureControls(node) {
  if (node._mengBaoCollageControls || typeof document === "undefined" || typeof node.addDOMWidget !== "function") return;
  const root = document.createElement("div");
  Object.assign(root.style, {
    display: "flex", gap: "8px", width: "100%", minHeight: "40px", padding: "2px 0", boxSizing: "border-box",
  });
  function createButton(onClick) {
    const button = document.createElement("button");
    button.type = "button";
    Object.assign(button.style, {
      flex: "1 1 0", minWidth: "0", minHeight: "36px", border: "0", borderRadius: "6px",
      background: "#477ac1", color: "#ffffff", cursor: "pointer", fontSize: "13px", overflowWrap: "anywhere",
    });
    button.addEventListener("click", onClick);
    return button;
  }
  const addButton = createButton(() => addImage(node));
  const removeButton = createButton(() => removeImage(node));
  root.append(addButton, removeButton);
  const widget = node.addDOMWidget("mengbao_collage_controls", "mengbao-collage-controls", root, {
    serialize: false, hideOnZoom: false, getMinHeight: () => 42, getMaxHeight: () => 42,
  });
  node._mengBaoCollageControls = { addButton, removeButton, widget, render: (language) => renderControls(node, language) };
}

function configureNode(node, serializedNode) {
  const savedInputs = serializedNode?.inputs;
  const target = Array.isArray(savedInputs)
    ? Math.max(DEFAULT_IMAGE_COUNT, ...savedInputs.map((input) => Number(input.name?.match(/^image_(\d+)$/)?.[1]) || 0))
    : node._mengBaoCollageInputsInitialized ? imageInputs(node).length : DEFAULT_IMAGE_COUNT;
  const clampedTarget = Math.min(MAX_IMAGE_COUNT, target);
  // 新节点虽声明了 20 个后端输入，界面只保留 4 个；重载时按保存的端口还原。
  let entries = imageInputs(node);
  while (entries.length > clampedTarget && typeof node.removeInput === "function") {
    const last = entries.at(-1);
    if (last.input.link != null) break;
    node.removeInput(last.index);
    entries = imageInputs(node);
  }
  while (entries.length < clampedTarget && typeof node.addInput === "function") {
    const number = nextImageNumber(node);
    if (number === null) break;
    node.addInput(`image_${number}`, "IMAGE");
    entries = imageInputs(node);
  }
  node._mengBaoCollageInputsInitialized = true;
  ensureControls(node);
  applyNodeLocalization(node);
  resizeNode(node);
}

app.registerExtension({
  name: "MengBaoAI.smart_collage",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      configureNode(this);
      return result;
    };
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (serializedNode) {
      const result = onConfigure?.apply(this, arguments);
      configureNode(this, serializedNode);
      return result;
    };
  },
});
