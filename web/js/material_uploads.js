const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "image/bmp", "image/x-ms-bmp"];
const MAX_UPLOAD_BYTES = 32 * 1024 * 1024;
const targets = new Set();
let hoveredTarget = null;
let pasteInstalled = false;

function isEditableTarget(target) {
  return ["input", "textarea", "select"].includes(String(target?.tagName || "").toLowerCase()) || Boolean(target?.isContentEditable);
}

function isImageFile(file) {
  return ACCEPTED_TYPES.includes(file?.type) || (!file?.type && /\.(png|jpe?g|webp|bmp)$/i.test(file?.name || ""));
}

function validateFiles(files, maxFiles) {
  if (!files.length || files.length > maxFiles) throw new Error(`Select at most ${maxFiles} image${maxFiles === 1 ? "" : "s"}`);
  for (const file of files) {
    if (!isImageFile(file)) throw new Error("Supported image formats: PNG, JPEG, WebP, BMP");
    if (file.size < 1 || file.size > MAX_UPLOAD_BYTES) throw new Error("Image file must be between 1 byte and 32 MB");
  }
}

function available(target) {
  const scope = document.querySelector?.("[data-mengbao-upload-scope]");
  if (scope && !scope.contains(target.element)) return false;
  const visibility = globalThis.getComputedStyle?.(target.element)?.visibility;
  return target.element.isConnected && target.element.getClientRects().length > 0
    && visibility !== "hidden" && visibility !== "collapse" && (target.available?.() ?? true);
}

function pasteTarget() {
  const eligible = [...targets].filter(available);
  if (hoveredTarget && eligible.includes(hoveredTarget)) return hoveredTarget;
  const focused = eligible.filter(({ element }) => element.contains(document.activeElement));
  if (focused.length === 1) return focused[0];
  return eligible.length === 1 ? eligible[0] : null;
}

function installPaste() {
  if (pasteInstalled) return;
  pasteInstalled = true;
  document.addEventListener("paste", async (event) => {
    if (event.defaultPrevented || isEditableTarget(event.target)) return;
    const target = pasteTarget();
    const files = [...(event.clipboardData?.files || [])].filter(isImageFile);
    if (!target || !files.length) return;
    event.preventDefault();
    await target.receiveFiles(files);
  }, true);
}

function bindUploadTarget(element, options) {
  const target = { ...options, element };
  target.receiveFiles = async (files) => {
    if (!available(target)) return;
    try {
      validateFiles(files, options.maxFiles);
      await options.upload(files);
    } catch (error) {
      options.onError(error instanceof Error ? error : new Error(String(error)));
    }
  };
  const handlers = {
    mouseenter: () => { hoveredTarget = target; },
    mouseleave: () => { if (hoveredTarget === target) hoveredTarget = null; },
    dragover: (event) => { if (available(target)) event.preventDefault(); },
    drop: async (event) => {
      if (!available(target)) return;
      event.preventDefault();
      await target.receiveFiles([...(event.dataTransfer?.files || [])]);
    },
  };
  for (const [name, handler] of Object.entries(handlers)) element.addEventListener(name, handler);
  targets.add(target);
  installPaste();
  return {
    receiveFiles: target.receiveFiles,
    chooseFiles() {
      if (!available(target)) return;
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ACCEPTED_TYPES.join(",");
      input.multiple = options.maxFiles > 1;
      input.onchange = () => target.receiveFiles([...(input.files || [])]);
      input.click();
      return input;
    },
    dispose() {
      targets.delete(target);
      if (hoveredTarget === target) hoveredTarget = null;
      for (const [name, handler] of Object.entries(handlers)) element.removeEventListener(name, handler);
    },
  };
}

export { ACCEPTED_TYPES, bindUploadTarget, isEditableTarget, isImageFile, validateFiles };
