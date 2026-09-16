import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { importMaterial } from "./material_library.js";

const NODE_CLASSES = new Set(["MengBaoSaveImage", "MengBaoPreviewImage"]);
const TEXT = {
  en: { save: "MengBao AI · Save Image", preview: "MengBao AI · Preview Image", images: "Images", prompt: "Generation Prompt", prefix: "Filename Prefix", add: "Add to Prompt Library", choose: "Select a generation prompt", source: "Prompt Source", loading: "Preparing...", noPrompt: "No generation prompt found; complete the prompt in the library form.", empty: "No generated image", opened: "Prompt draft opened", explicit: "Connected Prompt", generator: "Image Generation", positive: "Positive Prompt" },
  zh: { save: "萌宝AI·保存图片", preview: "萌宝AI·预览图片", images: "图像", prompt: "生图提示词", prefix: "文件名前缀", add: "加入提示词库", choose: "选择对应的生图提示词", source: "提示词来源", loading: "正在准备…", noPrompt: "未找到关联提示词，请在提示词库表单中补充。", empty: "暂无生成图片", opened: "已打开提示词草稿", explicit: "连接的提示词", generator: "图像生成", positive: "正向提示词" },
};
Object.assign(TEXT.en, { material: "Add to Material Library", imported: "Added to Material Library", waiting: "Waiting for generated image", previous: "Previous Image", next: "Next Image" });
Object.assign(TEXT.zh, { material: "加入素材库", imported: "已加入素材库", waiting: "等待生成图片", previous: "上一张图片", next: "下一张图片" });
const CONTROL_HEIGHT = 404;
function language() { return String(app.ui?.settings?.getSettingValue?.("Comfy.Locale") || "").toLowerCase().startsWith("zh") ? "zh" : "en"; }
function nodeClass(node) { return node.comfyClass || node.type || node.constructor?.comfyClass; }
function labels() { return TEXT[language()]; }

function imageOutputUrl(image) {
  if (!image?.filename || !["output", "temp"].includes(image.type)) throw new Error("Image output reference is invalid");
  return `/view?${new URLSearchParams({ filename: image.filename, subfolder: image.subfolder || "", type: image.type })}`;
}

function selectedImage(node) {
  const images = node._mengBaoImageOutputState.images;
  const index = Number.isInteger(node.imageIndex) && node.imageIndex >= 0 && node.imageIndex < images.length ? node.imageIndex : 0;
  return { image: images[index], index };
}

function ensureOutputStyles() {
  if (document.getElementById("mengbao-image-output-styles")) return;
  const link = document.createElement("link");
  link.id = "mengbao-image-output-styles"; link.rel = "stylesheet";
  link.href = new URL("./image_output.css", import.meta.url).href;
  document.head.append(link);
}

function renderImageOutput(node) {
  const controls = node._mengBaoImageOutputControls;
  if (!controls) return;
  const state = node._mengBaoImageOutputState;
  const text = labels();
  const { image, index } = selectedImage(node);
  controls.name.textContent = image?.filename || text.empty;
  controls.name.title = controls.name.textContent;
  controls.hint.textContent = text.waiting;
  controls.hint.hidden = Boolean(image);
  controls.image.hidden = !image;
  if (image) {
    const path = imageOutputUrl(image);
    const url = api.apiURL?.(path) || path;
    if (controls.image.getAttribute("src") !== url) {
      state.width = state.height = 0;
      controls.image.src = url;
    }
  } else controls.image.removeAttribute("src");
  controls.image.alt = text.images;
  controls.zone.setAttribute("aria-label", image ? image.filename : text.waiting);
  controls.pager.hidden = state.images.length < 2;
  controls.counter.textContent = `${index + 1} / ${state.images.length}`;
  for (const [button, title] of [[controls.previous, text.previous], [controls.next, text.next]]) {
    button.title = title; button.setAttribute("aria-label", title); button.disabled = state.busy;
  }
  node.title = nodeClass(node) === "MengBaoPreviewImage" ? text.preview : text.save;
  for (const input of node.inputs || []) input.label = input.localized_name = input.name === "generation_prompt" ? text.prompt : input.name === "images" ? text.images : input.label || input.name;
  const prefix = node.widgets?.find(({ name }) => name === "filename_prefix");
  if (prefix) prefix.label = text.prefix;
  controls.select.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = ""; placeholder.textContent = text.choose; controls.select.append(placeholder);
  for (const [index, candidate] of state.candidates.entries()) {
    const option = document.createElement("option");
    option.value = String(index);
    const source = candidate.class_type === "explicit" ? text.explicit : candidate.class_type === "CLIPTextEncode" ? text.positive : text.generator;
    option.textContent = `${source}${candidate.node_id ? ` #${candidate.node_id}` : ""}`;
    controls.select.append(option);
  }
  controls.select.value = state.selectedIndex < 0 ? "" : String(state.selectedIndex);
  controls.select.hidden = state.candidates.length < 2;
  controls.select.disabled = state.busy;
  controls.select.setAttribute("aria-label", text.source);
  controls.button.textContent = text.add;
  controls.materialButton.textContent = text.material;
  controls.materialButton.disabled = state.busy || !state.images.length;
  controls.button.disabled = state.busy || !state.images.length || (state.candidates.length > 1 && state.selectedIndex < 0);
  controls.button.style.opacity = controls.button.disabled ? "0.55" : "1";
  controls.button.style.cursor = controls.button.disabled ? "not-allowed" : "pointer";
  const dimensions = state.width ? `${state.width} × ${state.height}` : "";
  controls.status.textContent = state.error || (state.busy ? text.loading : state.warning ? text.noPrompt : state.notice === "material" ? text.imported : state.notice === "prompt" ? text.opened : state.candidates.length > 1 && state.selectedIndex < 0 ? `${dimensions}${dimensions ? " · " : ""}${text.choose}` : dimensions);
  controls.status.title = controls.status.textContent;
  controls.status.style.color = state.error ? "#f3a2a2" : "#bbb";
  node.setDirtyCanvas?.(true, true);
}

async function outputImageBlob(image) {
  const response = await api.fetchApi(imageOutputUrl(image));
  if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
  return response.blob();
}

async function imageThumbnail(image) {
  const bitmap = await createImageBitmap(await outputImageBlob(image));
  try {
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 512 / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas context is unavailable");
    // 缩略图只保留像素，避免把原 PNG 中的整张工作流和连接配置写进提示词库。
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally { bitmap.close(); }
}

async function addImagePrompt(node) {
  const state = node._mengBaoImageOutputState;
  if (state.busy || !state.images.length || (state.candidates.length > 1 && state.selectedIndex < 0)) return;
  state.busy = true; state.error = ""; state.warning = false; state.notice = ""; renderImageOutput(node);
  const candidate = state.candidates[state.selectedIndex];
  const { image } = selectedImage(node);
  try {
    if (typeof window.MengBaoPromptOrganizerDraft !== "function") throw new Error("Prompt library is unavailable");
    const thumbnail = await imageThumbnail(image);
    window.MengBaoPromptOrganizerDraft({ title: candidate?.text?.trim().split(/\r?\n/)[0].slice(0, 80) || image.filename,
      group: "default", prompt: candidate?.text || "", preview_image: thumbnail, tags: [], note: "" });
    state.warning = !candidate?.text;
    state.notice = "prompt";
  } catch (error) { state.error = error instanceof Error ? error.message : String(error); }
  finally { state.busy = false; renderImageOutput(node); }
}

async function addImageMaterial(node) {
  const state = node._mengBaoImageOutputState;
  if (state.busy || !state.images.length) return;
  const { image } = selectedImage(node);
  state.busy = true; state.error = ""; state.warning = false; state.notice = ""; renderImageOutput(node);
  try {
    // 复用素材库的大小校验与持久化，提交原图而不是预览缩略图。
    await importMaterial(new File([await outputImageBlob(image)], image.filename, { type: "image/png" }));
    state.notice = "material";
  } catch (error) { state.error = error instanceof Error ? error.message : String(error); }
  finally { state.busy = false; renderImageOutput(node); }
}

function setOutputMessage(node, message) {
  const state = node._mengBaoImageOutputState;
  state.images = (message?.images || []).filter((image) => typeof image?.filename === "string" && ["output", "temp"].includes(image.type));
  state.candidates = (message?.mengbao_prompt_candidates || []).filter((item) => typeof item?.text === "string" && item.text.trim());
  state.selectedIndex = state.candidates.length === 1 ? 0 : -1;
  state.error = ""; state.notice = ""; state.warning = false;
  node.imageIndex = 0;
}

function setupImageOutput(node) {
  node._mengBaoImageOutputState ||= { images: [], candidates: [], selectedIndex: -1, busy: false, error: "" };
  if (!node._mengBaoImageOutputControls) {
    ensureOutputStyles();
    const root = document.createElement("div");
    root.className = "mengbao-image-output-node";
    const name = document.createElement("div"); name.className = "mengbao-image-output-name";
    const zone = document.createElement("div"); zone.className = "mengbao-image-output-zone";
    const image = document.createElement("img");
    const hint = document.createElement("span"); hint.className = "mengbao-image-output-hint";
    image.addEventListener("load", () => {
      if (!node._mengBaoImageOutputState.images.length) return;
      Object.assign(node._mengBaoImageOutputState, { width: image.naturalWidth, height: image.naturalHeight });
      renderImageOutput(node);
    });
    image.addEventListener("error", () => {
      if (!node._mengBaoImageOutputState.images.length) return;
      node._mengBaoImageOutputState.error = "Image preview could not be loaded";
      renderImageOutput(node);
    });
    zone.append(image, hint);
    const pager = document.createElement("div"); pager.className = "mengbao-image-output-pager";
    const counter = document.createElement("span");
    const arrow = (direction, icon) => {
      const button = document.createElement("button"); button.type = "button";
      const symbol = document.createElement("i"); symbol.className = `pi pi-angle-${icon}`; symbol.setAttribute("aria-hidden", "true"); button.append(symbol);
      button.addEventListener("click", () => {
        const state = node._mengBaoImageOutputState;
        if (state.busy || state.images.length < 2) return;
        node.imageIndex = (selectedImage(node).index + direction + state.images.length) % state.images.length;
        state.error = ""; state.notice = ""; state.warning = false; renderImageOutput(node);
      });
      return button;
    };
    const previous = arrow(-1, "left"), next = arrow(1, "right");
    pager.append(previous, counter, next);
    const select = document.createElement("select");
    select.className = "mengbao-image-output-source";
    select.addEventListener("change", () => { node._mengBaoImageOutputState.selectedIndex = select.value === "" ? -1 : Number(select.value); renderImageOutput(node); });
    const button = document.createElement("button");
    button.type = "button";
    button.addEventListener("click", () => addImagePrompt(node));
    const materialButton = document.createElement("button"); materialButton.type = "button";
    materialButton.addEventListener("click", () => addImageMaterial(node));
    const actions = document.createElement("div"); actions.className = "mengbao-image-output-actions";
    actions.append(materialButton, button);
    const status = document.createElement("div");
    status.className = "mengbao-image-output-status";
    status.setAttribute("role", "status");
    root.append(name, zone, pager, select, actions, status);
    // ComfyUI 会扣除 20px 内部间距，预留后保证多图、来源选择和状态文字完整显示。
    node.addDOMWidget("mengbao_image_prompt", "mengbao-image-prompt", root, { serialize: false, hideOnZoom: false, getMinHeight: () => CONTROL_HEIGHT + 20, getMaxHeight: () => CONTROL_HEIGHT + 20 });
    node._mengBaoImageOutputControls = { root, name, zone, image, hint, pager, counter, previous, next, select, actions, materialButton, button, status };
  }
  const cached = app.nodeOutputs?.[node.id];
  if (!node._mengBaoImageOutputState.images.length && cached?.images?.length) setOutputMessage(node, cached);
  renderImageOutput(node);
  const size = node.computeSize?.();
  if (size) node.setSize?.([Math.max(360, node.size?.[0] || 0, size[0]), size[1]]);
}

app.registerExtension({
  name: "MengBaoAI.image_output",
  async setup() {
    const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
    if (!setting || setting._mengBaoImageOutputLocaleInstalled) return;
    setting._mengBaoImageOutputLocaleInstalled = true;
    const original = setting.onChange;
    setting.onChange = function (...args) {
      const result = original?.apply(this, args);
      setTimeout(() => { for (const node of app.graph?._nodes || []) if (NODE_CLASSES.has(nodeClass(node))) renderImageOutput(node); }, 0);
      return result;
    };
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!NODE_CLASSES.has(nodeData.name)) return;
    // 这两个节点由 DOM 占位区显示结果，避免原生预览在按钮下方再绘制一份。
    nodeType.prototype.onDrawBackground = function () {
      const cached = app.nodeOutputs?.[this.id];
      if (!this._mengBaoImageOutputState?.images.length && cached?.images?.length) {
        setupImageOutput(this);
      }
    };
    for (const hook of ["onNodeCreated", "onConfigure"]) {
      const original = nodeType.prototype[hook];
      nodeType.prototype[hook] = function () { const result = original?.apply(this, arguments); setupImageOutput(this); return result; };
    }
    const original = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      const result = original?.apply(this, arguments);
      setupImageOutput(this);
      setOutputMessage(this, message);
      renderImageOutput(this);
      return result;
    };
  },
});

export { addImageMaterial, addImagePrompt, imageOutputUrl, imageThumbnail, renderImageOutput, setupImageOutput };
