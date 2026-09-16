import { app } from "../../../scripts/app.js";

const NODE_NAME = "WANGLoadImageUploadPaste";
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "image/bmp"];
const TEXT = {
  en: {
    upload: "Upload Image",
    paste: "Paste Clipboard Image",
    hint: "Click upload or select this node and press Ctrl+V to paste an image",
    unavailable: "Clipboard image permission was not available",
    empty: "Clipboard does not contain a supported image",
  },
  zh: {
    upload: "上传图片",
    paste: "粘贴剪贴板图片",
    hint: "点击上传，或选中此节点后按 Ctrl+V 粘贴图片",
    unavailable: "无法读取剪贴板图片权限",
    empty: "剪贴板中没有支持的图片",
  },
};

let activePasteNode = null;

function currentLanguage() {
  const locale = app.ui?.settings?.getSettingValue?.("Comfy.Locale");
  return String(locale || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function labels() {
  return TEXT[currentLanguage()];
}

function isEditableTarget(target) {
  const tagName = String(target?.tagName || "").toLowerCase();
  return tagName === "input" || tagName === "textarea" || Boolean(target?.isContentEditable);
}

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function rememberWidget(widget) {
  if (!widget || widget._wangRemembered) {
    return;
  }
  widget._wangRemembered = true;
  widget._wangOriginalType = widget.type || "text";
  widget._wangOriginalComputeSize = widget.computeSize;
  widget._wangOriginalSerialize = widget.serialize;
}

function setWidgetVisible(widget, visible) {
  if (!widget) {
    return;
  }
  rememberWidget(widget);

  if (visible) {
    widget.type = widget._wangOriginalType;
    widget.computeSize = widget._wangOriginalComputeSize;
    widget.serialize = widget._wangOriginalSerialize;
    return;
  }

  widget.type = "hidden";
  widget.computeSize = () => [0, -4];
  widget.serialize = true;
}

function selectedWangNodes() {
  const selected = app.canvas?.selected_nodes;
  if (!selected) {
    return [];
  }
  return Object.values(selected).filter((node) => node?.comfyClass === NODE_NAME || node?.type === NODE_NAME);
}

function pasteTargetNode() {
  if (activePasteNode) {
    return activePasteNode;
  }
  const selected = selectedWangNodes();
  return selected.length === 1 ? selected[0] : null;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function setNodeImage(node, file, sourceLabel) {
  if (!file || !ACCEPTED_TYPES.includes(file.type)) {
    return;
  }

  const dataUrl = await fileToDataUrl(file);
  const imageWidget = findWidget(node, "image_data");
  const filenameWidget = findWidget(node, "filename");
  if (imageWidget) {
    imageWidget.value = dataUrl;
  }
  if (filenameWidget) {
    filenameWidget.value = file.name || sourceLabel || "clipboard_image.png";
  }

  node._wangPreviewUrl = dataUrl;
  node._wangStatus = `${file.name || sourceLabel || "clipboard image"}`;
  node.setSize?.(node.computeSize());
  app.graph?.setDirtyCanvas(true, true);
}

function chooseImageFile(node) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ACCEPTED_TYPES.join(",");
  input.onchange = async () => {
    const file = input.files?.[0];
    if (file) {
      await setNodeImage(node, file, "uploaded_image");
    }
  };
  input.click();
}

async function pasteClipboardImage(node) {
  const items = await navigator.clipboard?.read?.();
  if (!items?.length) {
    node._wangStatus = labels().unavailable;
    app.graph?.setDirtyCanvas(true, true);
    return;
  }

  for (const item of items) {
    const imageType = item.types.find((type) => ACCEPTED_TYPES.includes(type));
    if (imageType) {
      const blob = await item.getType(imageType);
      const file = new File([blob], "clipboard_image.png", { type: imageType });
      await setNodeImage(node, file, "clipboard_image.png");
      return;
    }
  }

  node._wangStatus = labels().empty;
  app.graph?.setDirtyCanvas(true, true);
}

function addPreview(node) {
  if (node._wangPreviewAdded) {
    return;
  }
  node._wangPreviewAdded = true;

  const drawForeground = node.onDrawForeground;
  node.onDrawForeground = function (ctx) {
    drawForeground?.apply(this, arguments);

    const y = (this.widgets?.length || 0) * 20 + 42;
    const width = Math.max(220, this.size?.[0] || 220);
    ctx.save();
    ctx.fillStyle = "#2f3542";
    ctx.fillRect(10, y, width - 20, 26);
    ctx.fillStyle = "#dfe4ea";
    ctx.font = "12px sans-serif";
    const text = this._wangStatus || labels().hint;
    ctx.fillText(text.slice(0, 42), 18, y + 17);
    ctx.restore();
  };
}

function setupNode(node) {
  setWidgetVisible(findWidget(node, "image_data"), false);
  setWidgetVisible(findWidget(node, "filename"), false);

  let uploadButton = node.widgets?.find((widget) => widget._mengBaoLoadAction === "upload");
  if (!uploadButton) {
    uploadButton = node.addWidget("button", labels().upload, "upload_image", () => chooseImageFile(node));
    uploadButton._mengBaoLoadAction = "upload";
  }
  let pasteButton = node.widgets?.find((widget) => widget._mengBaoLoadAction === "paste");
  if (!pasteButton) {
    pasteButton = node.addWidget("button", labels().paste, "paste_image", () => pasteClipboardImage(node));
    pasteButton._mengBaoLoadAction = "paste";
  }
  uploadButton.label = labels().upload;
  pasteButton.label = labels().paste;

  if (!node._mengBaoPasteFocusWrapped) {
    node._mengBaoPasteFocusWrapped = true;
    const onMouseEnter = node.onMouseEnter;
    node.onMouseEnter = function () {
      activePasteNode = this;
      return onMouseEnter?.apply(this, arguments);
    };
    const onMouseLeave = node.onMouseLeave;
    node.onMouseLeave = function () {
      if (activePasteNode === this) activePasteNode = null;
      return onMouseLeave?.apply(this, arguments);
    };
  }

  addPreview(node);
  node.setSize?.(node.computeSize());
}

document.addEventListener(
  "paste",
  async (event) => {
    if (isEditableTarget(event.target)) {
      return;
    }
    const node = pasteTargetNode();
    if (!node) return;
    const files = [...(event.clipboardData?.files || [])];
    const imageFile = files.find((file) => ACCEPTED_TYPES.includes(file.type));
    if (imageFile) {
      event.preventDefault();
      await setNodeImage(node, imageFile, "clipboard_image.png");
    }
  },
  true
);

app.registerExtension({
  name: "MengBaoAI.load_image.upload_paste",
  async setup() {
    const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
    if (setting && !setting._mengBaoLoadImageListenerInstalled) {
      setting._mengBaoLoadImageListenerInstalled = true;
      const originalOnChange = setting.onChange;
      setting.onChange = function (...args) {
        const result = originalOnChange?.apply(this, args);
        setTimeout(() => {
          for (const node of app.graph?._nodes || []) {
            if (node?.comfyClass === NODE_NAME || node?.type === NODE_NAME) setupNode(node);
          }
        }, 0);
        return result;
      };
    }
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) {
      return;
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      setupNode(this);
      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      setupNode(this);
      return result;
    };
  },
});
