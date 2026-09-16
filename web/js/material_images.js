import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { bindUploadTarget } from "./material_uploads.js";
import { ensureMaterialStyles, getMaterial, importMaterial, isMaterialDialogOpen, materialFileUrl, openMaterialLibrary, refreshMaterialDialogLocale } from "./material_library.js";

const LOAD_NODE = "MengBaoLoadImage";
const LIBRARY_NODE = "MengBaoMaterialLibrary";
const MATERIAL_PREFIX = "mengbao-material:";
const TEXT = {
  en: { loader: "MengBao AI · Load Image", library: "MengBao AI · Material Library", image: "Image", mask: "Mask", clear: "Clear Image", load: "Load Material", hint: "Click upload or press Ctrl+V to paste an image", libraryHint: "Click to import images or press Ctrl+V. Multiple selection supported.", empty: "No image selected", loading: "Loading..." },
  zh: { loader: "萌宝AI·加载图片", library: "萌宝AI·素材库", image: "图像", mask: "遮罩", clear: "清除图片", load: "加载素材", hint: "点击上传或 Ctrl+V 粘贴图片", libraryHint: "点击导入或 Ctrl+V 粘贴图片，支持一次多选", empty: "未选择图片", loading: "正在加载…" },
};

function currentLanguage() { return String(app.ui?.settings?.getSettingValue?.("Comfy.Locale") || "").toLowerCase().startsWith("zh") ? "zh" : "en"; }
function nodeClass(node) { return node?.comfyClass || node?.type || node?.constructor?.comfyClass; }
function isLibrary(node) { return nodeClass(node) === LIBRARY_NODE; }
function selectionWidget(node) { return node.widgets?.find(({ name }) => name === (isLibrary(node) ? "material_id" : "image")); }
function coreImageUrl(reference) {
  const match = String(reference).match(/^(.*?)(?:\s*\[(input|output|temp)\])?$/);
  const path = match?.[1] || "";
  const separator = path.lastIndexOf("/");
  return `/view?${new URLSearchParams({ filename: path.slice(separator + 1), subfolder: separator < 0 ? "" : path.slice(0, separator), type: match?.[2] || "input" })}`;
}

function renderNode(node) {
  const controls = node._mengBaoMaterialControls;
  if (!controls) return;
  const labels = TEXT[currentLanguage()];
  const state = node._mengBaoMaterialState;
  node.title = isLibrary(node) ? labels.library : labels.loader;
  for (const [index, output] of (node.outputs || []).entries()) {
    output.label = output.localized_name = index === 0 ? labels.image : labels.mask;
  }
  controls.name.textContent = state.name || labels.empty;
  controls.name.title = state.name;
  controls.hint.textContent = isLibrary(node) ? labels.libraryHint : labels.hint;
  controls.zone.title = controls.hint.textContent;
  controls.zone.setAttribute("aria-label", controls.hint.textContent);
  controls.zone.setAttribute("aria-disabled", String(state.busy));
  controls.image.hidden = !state.url;
  if (state.url && controls.image.getAttribute("src") !== state.url) controls.image.src = state.url;
  if (!state.url) controls.image.removeAttribute("src");
  controls.clear.textContent = labels.clear;
  controls.load.textContent = labels.load;
  controls.clear.disabled = state.busy || !selectionWidget(node)?.value;
  controls.load.disabled = state.busy;
  controls.status.textContent = state.error || (state.busy ? labels.loading : state.width ? `${state.width} × ${state.height}` : "");
  controls.status.classList.toggle("error", Boolean(state.error));
  node.setDirtyCanvas?.(true, true);
}

function setMaterial(node, item) {
  const widget = selectionWidget(node);
  if (widget) widget.value = isLibrary(node) ? item.id : `${MATERIAL_PREFIX}${item.id}`;
  Object.assign(node._mengBaoMaterialState, { name: item.name, url: materialFileUrl(item.id), width: item.width, height: item.height, error: "" });
  renderNode(node);
  app.graph?.setDirtyCanvas?.(true, true);
}

function clearImage(node) {
  if (node._mengBaoMaterialState.busy) return;
  const widget = selectionWidget(node);
  if (widget) widget.value = "";
  Object.assign(node._mengBaoMaterialState, { name: "", url: "", width: 0, height: 0, error: "" });
  node.imgs = null;
  renderNode(node);
  app.graph?.setDirtyCanvas?.(true, true);
}

async function uploadNodeFiles(node, files) {
  const state = node._mengBaoMaterialState;
  if (state.busy) return;
  state.busy = true;
  state.error = "";
  renderNode(node);
  try {
    if (isLibrary(node)) {
      for (const file of files) setMaterial(node, await importMaterial(file));
    } else {
      const file = files[0];
      // 文件选择、拖拽和粘贴共用同一解码、大小校验与 ComfyUI 持久化链路。
      const decoded = await createImageBitmap(file);
      const dimensions = { width: decoded.width, height: decoded.height };
      decoded.close();
      const body = new FormData();
      body.append("image", file, file.name || "clipboard_image.png");
      body.append("subfolder", "mengbao");
      const response = await api.fetchApi("/upload/image", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok || payload?.error) throw new Error(payload?.error?.message || `HTTP ${response.status}`);
      if (typeof payload.name !== "string" || !payload.name) throw new Error("Image upload response is invalid");
      const reference = `${payload.subfolder ? `${payload.subfolder}/` : ""}${payload.name}${payload.type && payload.type !== "input" ? ` [${payload.type}]` : ""}`;
      selectionWidget(node).value = reference;
      Object.assign(state, dimensions, { name: file.name || payload.name, url: coreImageUrl(reference) });
      app.graph?.setDirtyCanvas?.(true, true);
    }
  } catch (error) { state.error = error instanceof Error ? error.message : String(error); }
  finally { state.busy = false; renderNode(node); }
}

async function restoreSelection(node) {
  const value = String(selectionWidget(node)?.value || "");
  if (!value) return clearImage(node);
  const materialId = isLibrary(node) ? value : value.startsWith(MATERIAL_PREFIX) ? value.slice(MATERIAL_PREFIX.length) : "";
  if (materialId) {
    Object.assign(node._mengBaoMaterialState, { name: "", url: "", width: 0, height: 0, error: "" });
    renderNode(node);
    try {
      const item = await getMaterial(materialId);
      if (selectionWidget(node)?.value === value) setMaterial(node, item);
    } catch (error) {
      if (selectionWidget(node)?.value === value) { node._mengBaoMaterialState.error = error.message; renderNode(node); }
    }
  } else {
    Object.assign(node._mengBaoMaterialState, { name: value.split("/").pop(), url: coreImageUrl(value), width: 0, height: 0, error: "" });
    renderNode(node);
  }
}

function setupNode(node) {
  const widget = selectionWidget(node);
  if (widget) { widget.hidden = true; widget.type = "hidden"; widget.computeSize = () => [0, -4]; }
  node._mengBaoMaterialState ||= { name: "", url: "", width: 0, height: 0, busy: false, error: "" };
  if (!node._mengBaoMaterialControls) {
    ensureMaterialStyles();
    const root = document.createElement("div");
    root.className = "mengbao-material-node";
    const name = document.createElement("div");
    name.className = "mengbao-material-node-name";
    const zone = document.createElement("div");
    zone.className = "mengbao-material-node-zone";
    zone.tabIndex = 0;
    zone.setAttribute("role", "button");
    const hint = document.createElement("span");
    hint.className = "mengbao-material-node-hint";
    const image = document.createElement("img");
    image.alt = "";
    image.addEventListener("load", () => {
      if (!node._mengBaoMaterialState.url) return;
      Object.assign(node._mengBaoMaterialState, { width: image.naturalWidth, height: image.naturalHeight });
      renderNode(node);
    });
    image.addEventListener("error", () => {
      if (!node._mengBaoMaterialState.url) return;
      node._mengBaoMaterialState.error = "Image preview could not be loaded";
      renderNode(node);
    });
    zone.append(hint, image);
    const actions = document.createElement("div");
    actions.className = "mengbao-material-node-actions";
    const clear = document.createElement("button");
    clear.type = "button";
    clear.addEventListener("click", () => clearImage(node));
    const load = document.createElement("button");
    load.type = "button";
    load.className = "mengbao-primary";
    load.addEventListener("click", () => openMaterialLibrary({ language: currentLanguage,
      selectedId: isLibrary(node) ? widget?.value || "" : String(widget?.value || "").replace(MATERIAL_PREFIX, ""), onSelect: (item) => setMaterial(node, item) }));
    actions.append(clear, load);
    const status = document.createElement("div");
    status.className = "mengbao-material-node-status";
    status.setAttribute("role", "status");
    root.append(name, zone, actions, status);
    const binding = bindUploadTarget(zone, {
      maxFiles: isLibrary(node) ? 20 : 1,
      available: () => !node._mengBaoMaterialState.busy && !isMaterialDialogOpen() && !document.querySelector("dialog[open]"),
      upload: (files) => uploadNodeFiles(node, files),
      onError: (error) => { node._mengBaoMaterialState.error = error.message; renderNode(node); },
    });
    zone.addEventListener("click", () => binding.chooseFiles());
    zone.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); binding.chooseFiles(); } });
    node.addDOMWidget("mengbao_material_image", "mengbao-material-image", root, { serialize: false, hideOnZoom: false, getMinHeight: () => 336, getMaxHeight: () => 336 });
    node._mengBaoMaterialControls = { root, name, zone, image, hint, clear, load, status, binding };
  }
  renderNode(node);
  const size = node.computeSize?.();
  if (size) node.setSize?.([Math.max(360, node.size?.[0] || 0, size[0]), size[1]]);
  node._mengBaoMaterialRestorePromise = restoreSelection(node);
}

app.registerExtension({
  name: "MengBaoAI.material_images",
  async setup() {
    const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
    if (!setting || setting._mengBaoMaterialLocaleInstalled) return;
    setting._mengBaoMaterialLocaleInstalled = true;
    const original = setting.onChange;
    setting.onChange = function (...args) {
      const result = original?.apply(this, args);
      setTimeout(() => {
        for (const node of app.graph?._nodes || []) if ([LOAD_NODE, LIBRARY_NODE].includes(nodeClass(node))) renderNode(node);
        refreshMaterialDialogLocale();
      }, 0);
      return result;
    };
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (![LOAD_NODE, LIBRARY_NODE].includes(nodeData.name)) return;
    for (const hook of ["onNodeCreated", "onConfigure"]) {
      const original = nodeType.prototype[hook];
      nodeType.prototype[hook] = function () { const result = original?.apply(this, arguments); setupNode(this); return result; };
    }
    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () { this._mengBaoMaterialControls?.binding.dispose(); return onRemoved?.apply(this, arguments); };
  },
});

export { clearImage, coreImageUrl, renderNode, restoreSelection, setMaterial, setupNode, uploadNodeFiles };
