import { app } from "../../../scripts/app.js";

const API_ROOT = "/wang_prompt_organizer";
const COLORS = ["#e25545", "#d33b6a", "#8f3db4", "#6647b8", "#4d5fbc", "#5596e6", "#4e9b8f", "#6dad5f", "#f0a23a", "#806454"];

const T = {
  fab: "\u8bcd",
  manager: "WANG \u63d0\u793a\u8bcd\u6574\u7406\u5668",
  refresh: "\u5237\u65b0",
  add: "\u6dfb\u52a0",
  editMode: "\u7f16\u8f91\u6a21\u5f0f",
  doneEdit: "\u5b8c\u6210\u7f16\u8f91",
  close: "\u6536\u8d77",
  searchPlaceholder: "\u641c\u7d22\u6807\u9898\u3001\u63d0\u793a\u8bcd\u3001\u6807\u7b7e",
  allGroups: "\u5168\u90e8\u5206\u7ec4",
  import: "\u5bfc\u5165",
  export: "\u5bfc\u51fa",
  addGroup: "\u6dfb\u52a0\u5206\u7ec4",
  newGroupPlaceholder: "\u65b0\u5206\u7ec4\u540d\u79f0",
  moveTo: "\u79fb\u52a8\u5230",
  moveSelected: "\u79fb\u52a8\u9009\u4e2d",
  selectedCount: "\u5df2\u9009\u4e2d",
  title: "\u6807\u9898",
  group: "\u5206\u7ec4",
  titlePlaceholder: "\u63d0\u793a\u8bcd\u6807\u9898",
  groupPlaceholder: "\u81ea\u5b9a\u4e49\u5206\u7ec4",
  prompt: "\u63d0\u793a\u8bcd\u7247\u6bb5",
  promptPlaceholder: "\u8f93\u5165\u6216\u7c98\u8d34\u63d0\u793a\u8bcd\u5185\u5bb9",
  tags: "\u6807\u7b7e",
  tagsPlaceholder: "\u9017\u53f7\u5206\u9694",
  note: "\u5907\u6ce8",
  optional: "\u53ef\u9009",
  color: "\u9009\u62e9\u989c\u8272:",
  delete: "\u5220\u9664",
  copy: "\u590d\u5236",
  save: "\u4fdd\u5b58",
  defaultGroup: "\u9ed8\u8ba4",
  newPrompt: "\u65b0\u5efa\u63d0\u793a\u8bcd",
  chooseDelete: "\u8bf7\u9009\u62e9\u8981\u5220\u9664\u7684\u63d0\u793a\u8bcd",
  confirmDelete: "\u786e\u5b9a\u5220\u9664\u8fd9\u4e2a\u63d0\u793a\u8bcd\u5417\uff1f",
  deleted: "\u5df2\u5220\u9664",
  copied: "\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f",
  imported: "\u5df2\u5bfc\u5165",
  exported: "\u5df2\u5bfc\u51fa JSON",
  created: "\u5df2\u6dfb\u52a0",
  saved: "\u5df2\u4fdd\u5b58",
  groupSaved: "\u5206\u7ec4\u5df2\u6dfb\u52a0",
  noGroupName: "\u8bf7\u8f93\u5165\u5206\u7ec4\u540d\u79f0",
  noSelection: "\u8bf7\u5148\u9009\u62e9\u8981\u79fb\u52a8\u7684\u63d0\u793a\u8bcd",
  moved: "\u5df2\u79fb\u52a8",
  preview: "\u9884\u89c8\u56fe",
  uploadPreview: "\u4e0a\u4f20\u9884\u89c8\u56fe",
  previewHint: "\u70b9\u51fb\u4e0a\u4f20\uff0c\u6216\u805a\u7126\u6b64\u533a\u57df\u540e\u6309 Ctrl+V \u7c98\u8d34\u56fe\u7247",
  changePreview: "\u66f4\u6539",
  removePreview: "\u5220\u9664",
  previewRemoved: "\u9884\u89c8\u56fe\u5df2\u5220\u9664",
  editOn: "\u7f16\u8f91\u6a21\u5f0f\u5df2\u5f00\u542f",
  editOff: "\u7f16\u8f91\u6a21\u5f0f\u5df2\u5173\u95ed",
};

const ZH_TEXT = { ...T };
const EN_TEXT = {
  fab: "P",
  manager: "MengBao AI Prompt Organizer",
  refresh: "Refresh",
  add: "Add",
  editMode: "Edit Mode",
  doneEdit: "Finish Editing",
  close: "Close",
  searchPlaceholder: "Search titles, prompts, and tags",
  allGroups: "All Groups",
  import: "Import",
  export: "Export",
  addGroup: "Add Group",
  newGroupPlaceholder: "New group name",
  moveTo: "Move to",
  moveSelected: "Move Selected",
  selectedCount: "Selected",
  title: "Title",
  group: "Group",
  titlePlaceholder: "Prompt title",
  groupPlaceholder: "Custom group",
  prompt: "Prompt",
  promptPlaceholder: "Enter or paste prompt content",
  tags: "Tags",
  tagsPlaceholder: "Comma separated",
  note: "Note",
  optional: "Optional",
  color: "Choose a color:",
  delete: "Delete",
  copy: "Copy",
  save: "Save",
  defaultGroup: "Default",
  newPrompt: "New prompt",
  chooseDelete: "Choose a prompt to delete",
  confirmDelete: "Delete this prompt?",
  deleted: "Deleted",
  copied: "Copied to clipboard",
  imported: "Imported",
  exported: "Exported JSON",
  created: "Added",
  saved: "Saved",
  groupSaved: "Group added",
  noGroupName: "Enter a group name",
  noSelection: "Select prompts to move first",
  moved: "Moved",
  preview: "Preview Image",
  uploadPreview: "Upload Preview Image",
  previewHint: "Click to upload or focus here and press Ctrl+V to paste an image",
  changePreview: "Change",
  removePreview: "Remove",
  previewRemoved: "Preview image removed",
  editOn: "Edit mode enabled",
  editOff: "Edit mode disabled",
};

function normalizeLanguage(locale) {
  return String(locale || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function currentLanguage() {
  return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale"));
}

Object.assign(T, currentLanguage() === "zh" ? ZH_TEXT : EN_TEXT);

const state = {
  open: false,
  editMode: false,
  prompts: [],
  groups: ["default"],
  selectedId: "",
  selectedIds: new Set(),
  selectedColor: COLORS[0],
  previewImage: "",
  filterGroup: "all",
  query: "",
  pasteTarget: "",
};

function displayGroup(group) {
  return !group || group === "default" ? T.defaultGroup : group;
}

function storeGroup(group) {
  return !group || group === T.defaultGroup ? "default" : group;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  for (const child of children) {
    if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else if (child) node.appendChild(child);
  }
  return node;
}

function injectStyle() {
  if (document.getElementById("wang-prompt-style")) return;
  document.head.appendChild(el("style", {
    id: "wang-prompt-style",
    text: `
      .wang-prompt-fab{position:fixed;right:18px;bottom:92px;z-index:99999;width:52px;height:52px;border-radius:14px;border:1px solid rgba(255,255,255,.18);background:#2f2f2f;color:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 34px rgba(0,0,0,.38);cursor:pointer;font-size:22px;font-weight:800}
      .wang-prompt-panel{position:fixed;right:18px;bottom:18px;z-index:100000;width:min(660px,calc(100vw - 36px));height:min(720px,calc(100vh - 36px));background:#202020;color:#f5f5f5;border:1px solid #3c3c3c;border-radius:10px;box-shadow:0 18px 60px rgba(0,0,0,.5);display:flex;flex-direction:column;overflow:hidden;font-family:Arial,"Microsoft YaHei",sans-serif}
      .wang-prompt-head{height:58px;display:flex;align-items:center;gap:10px;padding:0 16px;border-bottom:1px solid #353535;flex:0 0 auto}
      .wang-prompt-title{font-size:20px;font-weight:800;margin-right:auto}
      .wang-prompt-icon,.wang-prompt-btn{border:1px solid #555;background:#3b3b3b;color:#fff;border-radius:6px;height:36px;padding:0 13px;font-size:15px;cursor:pointer}
      .wang-prompt-icon{width:38px;padding:0;font-size:20px}
      .wang-prompt-btn.primary{background:#4e86df;border-color:#4e86df}
      .wang-prompt-btn.green{background:#4c8b3f;border-color:#5ca54d}
      .wang-prompt-body{display:grid;grid-template-columns:230px 1fr;min-height:0;flex:1}
      .wang-prompt-side{border-right:1px solid #353535;padding:12px;display:flex;flex-direction:column;gap:10px;min-width:0}
      .wang-prompt-main{padding:14px;display:flex;flex-direction:column;gap:12px;min-width:0;overflow:auto}
      .wang-prompt-input,.wang-prompt-select,.wang-prompt-textarea{width:100%;box-sizing:border-box;background:#303030;border:1px solid #595959;color:#fff;border-radius:6px;padding:9px 10px;font-size:14px;outline:none}
      .wang-prompt-input:focus,.wang-prompt-select:focus,.wang-prompt-textarea:focus{border-color:#d6a91f}
      .wang-prompt-textarea{min-height:178px;resize:vertical;line-height:1.5}
      .wang-prompt-list{display:flex;flex-direction:column;gap:8px;overflow:auto;min-height:0}
      .wang-prompt-item{border:1px solid #3d3d3d;border-left:5px solid var(--wang-color,#e25545);background:#2a2a2a;color:#fff;border-radius:7px;padding:9px;text-align:left;cursor:pointer}
      .wang-prompt-item.active{border-color:#d6a91f;border-left-color:var(--wang-color,#e25545)}
      .wang-prompt-item-title{font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .wang-prompt-item-meta{font-size:12px;color:#bdbdbd;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .wang-prompt-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
      .wang-prompt-label{font-size:13px;color:#ddd;margin:0 0 5px}
      .wang-prompt-colors{display:flex;gap:10px;flex-wrap:wrap}
      .wang-prompt-swatch{width:28px;height:28px;border-radius:50%;border:2px solid transparent;cursor:pointer;background:var(--wang-color)}
      .wang-prompt-swatch.active{border-color:#fff}
      .wang-prompt-actions{display:flex;gap:10px;justify-content:flex-end;align-items:center}
      .wang-prompt-status{font-size:12px;color:#cfcfcf;margin-right:auto}
      .wang-prompt-import{display:grid;grid-template-columns:1fr 1fr;gap:8px}
      .wang-prompt-group-tools{display:grid;grid-template-columns:1fr auto;gap:8px}
      .wang-prompt-move-tools{display:grid;grid-template-columns:1fr auto;gap:8px}
      .wang-prompt-check{display:flex;align-items:flex-start;gap:8px}
      .wang-prompt-check input{margin-top:3px;accent-color:#d6a91f}
      .wang-prompt-item-content{min-width:0;flex:1}
      .wang-prompt-small{font-size:12px;color:#cfcfcf}
      .wang-prompt-preview{position:relative;margin-top:18px;width:100%;height:300px;border:2px dashed #3d3a4d;background:#171621;border-radius:14px;display:flex;align-items:center;justify-content:center;color:#b7b1d6;cursor:pointer;overflow:hidden;box-sizing:border-box;transition:border-color .16s ease,background .16s ease,transform .16s ease}
      .wang-prompt-preview:hover{border-color:#6f68a8;background:#1d1b2a}
      .wang-prompt-preview-empty{display:flex;flex-direction:column;align-items:center;gap:9px;text-align:center;padding:22px}
      .wang-prompt-preview-icon{position:relative;width:38px;height:32px;border:3px solid #a8a2cb;border-radius:6px;box-sizing:border-box}
      .wang-prompt-preview-icon::before{content:"";position:absolute;left:7px;top:7px;width:7px;height:7px;border:3px solid #a8a2cb;border-radius:50%;box-sizing:border-box}
      .wang-prompt-preview-icon::after{content:"+";position:absolute;right:-11px;top:-16px;color:#a8a2cb;font-size:24px;font-weight:900;line-height:1}
      .wang-prompt-preview-mountain{position:absolute;left:8px;right:6px;bottom:6px;height:12px;border-left:3px solid #a8a2cb;border-bottom:3px solid #a8a2cb;transform:skewX(-24deg);border-radius:1px}
      .wang-prompt-preview-title{font-size:20px;font-weight:800;color:#d7d2ee}
      .wang-prompt-preview-hint{font-size:14px;font-weight:700;color:#77728e}
      .wang-prompt-preview img{width:100%;height:100%;object-fit:contain;display:block;background:#14131b}
      .wang-prompt-preview-tools{position:absolute;right:12px;top:12px;display:flex;gap:8px;opacity:0;transition:opacity .16s ease}
      .wang-prompt-preview:hover .wang-prompt-preview-tools{opacity:1}
      .wang-prompt-preview-tool{height:32px;border:1px solid rgba(255,255,255,.24);background:rgba(28,27,38,.86);color:#fff;border-radius:6px;padding:0 12px;font-size:13px;font-weight:800;cursor:pointer;backdrop-filter:blur(8px)}
      .wang-prompt-preview-tool:hover{background:rgba(72,67,105,.92);border-color:#8b84c3}
      .wang-prompt-preview-input{display:none}
      .wang-prompt-lightbox{position:fixed;inset:0;z-index:100001;background:rgba(0,0,0,.82);display:flex;align-items:center;justify-content:center;padding:28px;box-sizing:border-box;cursor:zoom-out}
      .wang-prompt-lightbox img{max-width:100%;max-height:100%;object-fit:contain;border-radius:6px;box-shadow:0 16px 60px rgba(0,0,0,.6)}
      .wang-prompt-file{display:none}
      @media (max-width:720px){.wang-prompt-panel{right:8px;bottom:8px;width:calc(100vw - 16px);height:calc(100vh - 16px)}.wang-prompt-body{grid-template-columns:1fr}.wang-prompt-side{border-right:0;border-bottom:1px solid #353535;max-height:260px}.wang-prompt-row,.wang-prompt-import{grid-template-columns:1fr}.wang-prompt-title{font-size:17px}}
    `,
  }));
}

async function api(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function field(label, input) {
  return el("label", {}, [el("div", { class: "wang-prompt-label", text: label }), input]);
}

function hashCode(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) hash = ((hash << 5) - hash + value.charCodeAt(i)) | 0;
  return hash;
}

function selectedPrompt() {
  return state.prompts.find((item) => item.id === state.selectedId) || null;
}

function status(text) {
  const node = document.getElementById("wang-prompt-status");
  if (node) node.textContent = text || "";
}

function renderColors() {
  const colors = document.getElementById("wang-prompt-colors");
  if (!colors) return;
  colors.innerHTML = "";
  for (const color of COLORS) {
    colors.appendChild(el("button", {
      type: "button",
      class: `wang-prompt-swatch${state.selectedColor === color ? " active" : ""}`,
      style: `--wang-color:${color}`,
      title: color,
      onclick: () => {
        state.selectedColor = color;
        renderColors();
      },
    }));
  }
}

function fillForm(item = null) {
  const form = document.getElementById("wang-prompt-form");
  if (!form) return;
  form.dataset.id = item?.id || "";
  form.dataset.group = item?.group || "default";
  form.elements.title.value = item?.title || "";
  form.elements.group.value = item?.group || "default";
  form.elements.prompt.value = item?.prompt || "";
  form.elements.tags.value = Array.isArray(item?.tags) ? item.tags.join(", ") : "";
  form.elements.note.value = item?.note || "";
  state.selectedColor = item?.color || COLORS[0];
  state.previewImage = item?.preview_image || "";
  renderColors();
  renderPreview();
}

function renderFilters() {
  const groupSelect = document.getElementById("wang-prompt-filter-group");
  const moveSelect = document.getElementById("wang-prompt-move-group");
  const formGroupSelect = document.getElementById("wang-prompt-form-group");
  const datalist = document.getElementById("wang-prompt-groups");
  if (groupSelect) {
    const current = groupSelect.value || state.filterGroup;
    groupSelect.innerHTML = "";
    groupSelect.appendChild(el("option", { value: "all", text: T.allGroups }));
    for (const group of state.groups) groupSelect.appendChild(el("option", { value: group, text: displayGroup(group) }));
    groupSelect.value = state.groups.includes(current) || current === "all" ? current : "all";
  }
  if (moveSelect) {
    const current = moveSelect.value || "default";
    moveSelect.innerHTML = "";
    for (const group of state.groups) moveSelect.appendChild(el("option", { value: group, text: displayGroup(group) }));
    moveSelect.value = state.groups.includes(current) ? current : "default";
  }
  if (formGroupSelect) {
    const form = document.getElementById("wang-prompt-form");
    const current = storeGroup(formGroupSelect.value || form?.dataset.group || "default");
    formGroupSelect.innerHTML = "";
    for (const group of state.groups) formGroupSelect.appendChild(el("option", { value: group, text: displayGroup(group) }));
    formGroupSelect.value = state.groups.includes(current) ? current : "default";
  }
  if (datalist) {
    datalist.innerHTML = "";
    for (const group of state.groups) datalist.appendChild(el("option", { value: displayGroup(group) }));
  }
}

function renderList() {
  const list = document.getElementById("wang-prompt-list");
  if (!list) return;
  list.innerHTML = "";
  for (const item of state.prompts) {
    const color = item.color || COLORS[Math.abs(hashCode(item.group || "")) % COLORS.length];
    list.appendChild(el("div", {
      class: `wang-prompt-item${item.id === state.selectedId ? " active" : ""}`,
      role: "button",
      tabindex: "0",
      style: `--wang-color:${color}`,
      onclick: () => {
        state.selectedId = item.id;
        fillForm(item);
        renderList();
      },
    }, [
      el("div", { class: "wang-prompt-check" }, [
        el("input", {
          type: "checkbox",
          checked: state.selectedIds.has(item.id) ? "checked" : null,
          onclick: (event) => {
            event.stopPropagation();
            if (event.currentTarget.checked) state.selectedIds.add(item.id);
            else state.selectedIds.delete(item.id);
            renderSelectionStatus();
          },
        }),
        el("div", { class: "wang-prompt-item-content" }, [
          el("div", { class: "wang-prompt-item-title", text: item.title || "Untitled" }),
          el("div", { class: "wang-prompt-item-meta", text: `${displayGroup(item.group)} - ${(item.tags || []).join(", ")}` }),
        ]),
      ]),
    ]));
  }
  renderSelectionStatus();
}

function renderSelectionStatus() {
  const node = document.getElementById("wang-prompt-selected-count");
  if (node) node.textContent = `${T.selectedCount} ${state.selectedIds.size}`;
}

function renderPreview() {
  const preview = document.getElementById("wang-prompt-preview");
  if (!preview) return;
  preview.innerHTML = "";
  if (state.previewImage) {
    preview.appendChild(el("img", { src: state.previewImage, alt: T.preview }));
    preview.appendChild(el("div", { class: "wang-prompt-preview-tools" }, [
      el("button", { class: "wang-prompt-preview-tool", type: "button", text: T.changePreview, onclick: onChangePreview }),
      el("button", { class: "wang-prompt-preview-tool", type: "button", text: T.removePreview, onclick: onRemovePreview }),
    ]));
    return;
  }
  preview.appendChild(el("div", { class: "wang-prompt-preview-empty" }, [
    el("div", { class: "wang-prompt-preview-icon" }, [el("span", { class: "wang-prompt-preview-mountain" })]),
    el("div", { class: "wang-prompt-preview-title", text: T.preview }),
    el("div", { class: "wang-prompt-preview-hint", text: T.previewHint }),
  ]));
}

function render() {
  renderFilters();
  renderList();
  if (state.selectedId) fillForm(selectedPrompt());
  else fillForm();
}

async function refresh() {
  const params = new URLSearchParams({ group: state.filterGroup || "all", query: state.query || "" });
  const data = await api(`/prompts?${params.toString()}`);
  state.prompts = data.prompts || [];
  state.groups = data.groups || ["default"];
  const visibleIds = new Set(state.prompts.map((item) => item.id));
  state.selectedIds = new Set([...state.selectedIds].filter((id) => visibleIds.has(id)));
  if (!state.prompts.some((item) => item.id === state.selectedId)) state.selectedId = state.prompts[0]?.id || "";
  render();
}

async function refreshAndNewPrompt() {
  await refresh();
  state.selectedId = "";
  fillForm();
  status(T.newPrompt);
}

function buildPanel() {
  const fileInput = el("input", { class: "wang-prompt-file", type: "file", accept: ".json,application/json", onchange: onImportFile });
  const previewInput = el("input", { class: "wang-prompt-preview-input", type: "file", accept: "image/*", onchange: onPreviewFile });
  return el("section", { class: "wang-prompt-panel", id: "wang-prompt-panel" }, [
    el("header", { class: "wang-prompt-head" }, [
      el("div", { class: "wang-prompt-title", text: T.manager }),
      el("button", { class: "wang-prompt-icon", title: T.add, text: "\u21bb", onclick: () => refreshAndNewPrompt().catch((err) => status(err.message)) }),
      el("button", { class: "wang-prompt-icon", title: T.close, text: "\u00d7", onclick: closePanel }),
    ]),
    el("div", { class: "wang-prompt-body" }, [
      el("aside", { class: "wang-prompt-side" }, [
        el("input", { class: "wang-prompt-input", placeholder: T.searchPlaceholder, value: state.query, oninput: (event) => { state.query = event.target.value; refresh().catch((err) => status(err.message)); } }),
        el("select", { class: "wang-prompt-select", id: "wang-prompt-filter-group", onchange: (event) => { state.filterGroup = event.target.value; refresh().catch((err) => status(err.message)); } }),
        el("div", { class: "wang-prompt-group-tools" }, [
          el("input", { class: "wang-prompt-input", id: "wang-prompt-new-group", placeholder: T.newGroupPlaceholder }),
          el("button", { class: "wang-prompt-btn green", text: T.addGroup, onclick: onAddGroup }),
        ]),
        el("div", { class: "wang-prompt-move-tools" }, [
          el("select", { class: "wang-prompt-select", id: "wang-prompt-move-group" }),
          el("button", { class: "wang-prompt-btn", text: T.moveSelected, onclick: onMoveSelected }),
        ]),
        el("div", { class: "wang-prompt-small", id: "wang-prompt-selected-count", text: `${T.selectedCount} 0` }),
        el("div", {
          class: "wang-prompt-import",
          tabindex: "0",
          title: `${T.import} JSON / Ctrl+V`,
          onmouseenter: () => { state.pasteTarget = "json"; },
          onmouseleave: () => { if (state.pasteTarget === "json") state.pasteTarget = ""; },
          onfocusin: () => { state.pasteTarget = "json"; },
          onfocusout: () => { if (state.pasteTarget === "json") state.pasteTarget = ""; },
        }, [
          el("button", { class: "wang-prompt-btn", text: `${T.import} / Ctrl+V`, onclick: () => fileInput.click() }),
          el("button", { class: "wang-prompt-btn", text: T.export, onclick: onExport }),
          fileInput,
        ]),
        el("div", { class: "wang-prompt-list", id: "wang-prompt-list" }),
      ]),
      el("main", { class: "wang-prompt-main" }, [
        el("form", { id: "wang-prompt-form", onsubmit: onSave }, [
          el("div", { class: "wang-prompt-row" }, [
            field(T.title, el("input", { class: "wang-prompt-input", name: "title", placeholder: T.titlePlaceholder, required: "required" })),
            field(T.group, el("select", { class: "wang-prompt-select", id: "wang-prompt-form-group", name: "group", required: "required" })),
          ]),
          el("datalist", { id: "wang-prompt-groups" }),
          field(T.prompt, el("textarea", { class: "wang-prompt-textarea", name: "prompt", placeholder: T.promptPlaceholder, required: "required" })),
          el("div", { class: "wang-prompt-row" }, [
            field(T.tags, el("input", { class: "wang-prompt-input", name: "tags", placeholder: T.tagsPlaceholder })),
            field(T.note, el("input", { class: "wang-prompt-input", name: "note", placeholder: T.optional })),
          ]),
          el("div", {}, [
            el("div", { class: "wang-prompt-label", text: T.color }),
            el("div", { class: "wang-prompt-colors", id: "wang-prompt-colors" }),
          ]),
          el("div", { class: "wang-prompt-actions" }, [
            el("span", { class: "wang-prompt-status", id: "wang-prompt-status" }),
            el("button", { class: "wang-prompt-btn", type: "button", text: T.delete, onclick: onDelete }),
            el("button", { class: "wang-prompt-btn", type: "button", text: T.copy, onclick: onCopy }),
            el("button", { class: "wang-prompt-btn primary", type: "submit", text: T.save }),
          ]),
          previewInput,
          el("div", {
            class: "wang-prompt-preview",
            id: "wang-prompt-preview",
            tabindex: "0",
            title: T.previewHint,
            onclick: onPreviewClick,
            onmouseenter: () => { state.pasteTarget = "image"; },
            onmouseleave: () => { if (state.pasteTarget === "image") state.pasteTarget = ""; },
            onfocusin: () => { state.pasteTarget = "image"; },
            onfocusout: () => { if (state.pasteTarget === "image") state.pasteTarget = ""; },
          }, [
            el("div", { class: "wang-prompt-preview-empty" }, [
              el("div", { class: "wang-prompt-preview-icon" }, [el("span", { class: "wang-prompt-preview-mountain" })]),
              el("div", { class: "wang-prompt-preview-title", text: T.preview }),
              el("div", { class: "wang-prompt-preview-hint", text: T.previewHint }),
            ]),
          ]),
        ]),
      ]),
    ]),
  ]);
}

function openPanel() {
  state.open = true;
  document.getElementById("wang-prompt-fab")?.remove();
  document.getElementById("wang-prompt-panel")?.remove();
  document.body.appendChild(buildPanel());
  refresh().catch((err) => status(err.message));
}

function closePanel() {
  state.open = false;
  document.getElementById("wang-prompt-panel")?.remove();
  ensureFab();
}

function ensureFab() {
  injectStyle();
  if (document.getElementById("wang-prompt-fab") || state.open) return;
  document.body.appendChild(el("button", { id: "wang-prompt-fab", class: "wang-prompt-fab", title: T.manager, text: T.fab, onclick: openPanel }));
}

function captureDraft() {
  const form = document.getElementById("wang-prompt-form");
  if (!form) return null;
  return {
    values: Object.fromEntries(new FormData(form).entries()),
    id: form.dataset.id || "",
    group: form.dataset.group || "default",
    color: state.selectedColor,
    previewImage: state.previewImage,
  };
}

function restoreDraft(draft) {
  const form = document.getElementById("wang-prompt-form");
  if (!form || !draft) return;
  form.dataset.id = draft.id;
  form.dataset.group = draft.group;
  for (const [name, value] of Object.entries(draft.values)) {
    if (form.elements[name]) form.elements[name].value = value;
  }
  state.selectedColor = draft.color;
  state.previewImage = draft.previewImage;
  renderColors();
  renderPreview();
}

function localizePromptNodeButtons(node) {
  for (const widget of node?.widgets || []) {
    if (widget._mengBaoPromptAction === "manager") widget.label = T.manager;
    if (widget._mengBaoPromptAction === "add") widget.label = T.add;
    if (widget._mengBaoPromptAction === "refresh") widget.label = T.refresh;
  }
  node?.setDirtyCanvas?.(true, true);
}

function applyLanguage() {
  Object.assign(T, currentLanguage() === "zh" ? ZH_TEXT : EN_TEXT);
  const draft = state.open ? captureDraft() : null;
  if (state.open) {
    document.getElementById("wang-prompt-panel")?.remove();
    document.body.appendChild(buildPanel());
    renderFilters();
    renderList();
    restoreDraft(draft);
  } else {
    document.getElementById("wang-prompt-fab")?.remove();
    ensureFab();
  }
  for (const node of app.graph?._nodes || []) {
    if (node?.comfyClass === "WANGPromptOrganizer" || node?.type === "WANGPromptOrganizer") {
      localizePromptNodeButtons(node);
    }
  }
}

function installLocaleListener() {
  const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
  if (!setting || setting._mengBaoPromptListenerInstalled) return;
  setting._mengBaoPromptListenerInstalled = true;
  const originalOnChange = setting.onChange;
  setting.onChange = function (...args) {
    const result = originalOnChange?.apply(this, args);
    setTimeout(applyLanguage, 0);
    return result;
  };
}

function toggleEditMode() {
  state.editMode = !state.editMode;
  openPanel();
  status(state.editMode ? T.editOn : T.editOff);
}

async function onSave(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  const result = await api("/prompt", {
    method: "POST",
    body: JSON.stringify({
      id: form.dataset.id || "",
      title: data.title,
      group: storeGroup(data.group),
      prompt: data.prompt,
      tags: data.tags,
      note: data.note,
      color: state.selectedColor,
      preview_image: state.previewImage,
    }),
  });
  state.selectedId = result.prompt?.id || state.selectedId;
  status(result.status === "created" ? T.created : T.saved);
  await refresh();
}

async function onDelete() {
  const id = document.getElementById("wang-prompt-form")?.dataset.id;
  if (!id) {
    status(T.chooseDelete);
    return;
  }
  if (!confirm(T.confirmDelete)) return;
  await api(`/prompt/${encodeURIComponent(id)}`, { method: "DELETE" });
  state.selectedId = "";
  fillForm();
  status(T.deleted);
  await refresh();
}

async function onAddGroup() {
  const input = document.getElementById("wang-prompt-new-group");
  const rawGroup = (input?.value || "").trim();
  if (!rawGroup) {
    status(T.noGroupName);
    return;
  }
  const group = storeGroup(rawGroup);
  const result = await api("/group", { method: "POST", body: JSON.stringify({ group }) });
  if (input) input.value = "";
  state.filterGroup = result.group || group;
  status(T.groupSaved);
  await refresh();
}

async function onMoveSelected() {
  if (!state.selectedIds.size) {
    status(T.noSelection);
    return;
  }
  const target = document.getElementById("wang-prompt-move-group")?.value || "default";
  const result = await api("/prompts/move", {
    method: "POST",
    body: JSON.stringify({ prompt_ids: [...state.selectedIds], target_group: target }),
  });
  state.selectedIds.clear();
  state.filterGroup = target;
  status(`${T.moved} ${result.moved || 0} \u6761`);
  await refresh();
}

async function onCopy() {
  const prompt = document.getElementById("wang-prompt-form")?.elements.prompt.value || "";
  await navigator.clipboard.writeText(prompt);
  status(T.copied);
}

function onPreviewClick() {
  if (!state.previewImage) {
    document.querySelector(".wang-prompt-preview-input")?.click();
    return;
  }
  document.body.appendChild(el("div", { class: "wang-prompt-lightbox", onclick: (event) => event.currentTarget.remove() }, [
    el("img", { src: state.previewImage, alt: T.preview }),
  ]));
}

function onChangePreview(event) {
  event.stopPropagation();
  document.querySelector(".wang-prompt-preview-input")?.click();
}

function onRemovePreview(event) {
  event.stopPropagation();
  state.previewImage = "";
  renderPreview();
  status(T.previewRemoved);
}

async function onPreviewFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  await setPreviewFile(file);
  event.target.value = "";
}

async function setPreviewFile(file) {
  if (!file?.type?.startsWith("image/")) return false;
  state.previewImage = await readFileAsDataUrl(file);
  renderPreview();
  status(T.uploadPreview);
  return true;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function onImportFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  await importJsonFile(file);
  event.target.value = "";
}

function isJsonFile(file) {
  return file?.type === "application/json" || String(file?.name || "").toLowerCase().endsWith(".json");
}

async function importJsonFile(file) {
  if (!isJsonFile(file)) return false;
  const importJson = await file.text();
  const result = await api("/import", { method: "POST", body: JSON.stringify({ import_json: importJson, merge_mode: "update" }) });
  status(`${T.imported} ${result.imported || 0} \u6761`);
  await refresh();
  return true;
}

function isEditableTarget(target) {
  const tagName = String(target?.tagName || "").toLowerCase();
  return tagName === "input" || tagName === "textarea" || Boolean(target?.isContentEditable);
}

document.addEventListener("paste", async (event) => {
  if (!state.open || !state.pasteTarget || isEditableTarget(event.target)) return;
  const files = [...(event.clipboardData?.files || [])];
  const file = state.pasteTarget === "image"
    ? files.find((item) => item.type?.startsWith("image/"))
    : files.find(isJsonFile);
  if (!file) return;
  event.preventDefault();
  if (state.pasteTarget === "image") await setPreviewFile(file);
  else await importJsonFile(file);
}, true);

async function onExport() {
  const params = new URLSearchParams({ group: state.filterGroup || "all", query: state.query || "" });
  const payload = await api(`/export?${params.toString()}`);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: `MengBao_prompts_export_${Date.now()}.json` });
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  status(T.exported);
}

function installNodeButtons(nodeType, nodeData) {
  if (nodeData.name !== "WANGPromptOrganizer") return;
  const onNodeCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    const result = onNodeCreated?.apply(this, arguments);
    const managerButton = this.addWidget?.("button", T.manager, null, () => openPanel());
    const addButton = this.addWidget?.("button", T.add, null, () => {
      openPanel();
      setTimeout(() => {
        state.selectedId = "";
        fillForm();
        status(T.newPrompt);
      }, 50);
    });
    const refreshButton = this.addWidget?.("button", T.refresh, null, () => refresh().catch((err) => status(err.message)));
    if (managerButton) managerButton._mengBaoPromptAction = "manager";
    if (addButton) addButton._mengBaoPromptAction = "add";
    if (refreshButton) refreshButton._mengBaoPromptAction = "refresh";
    localizePromptNodeButtons(this);
    return result;
  };
}

app.registerExtension({
  name: "MengBaoAI.prompt_organizer.floating_panel",
  async setup() {
    installLocaleListener();
    applyLanguage();
    injectStyle();
    ensureFab();
    setTimeout(ensureFab, 500);
    setTimeout(ensureFab, 2000);
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    installNodeButtons(nodeType, nodeData);
  },
});

window.WANGPromptOrganizerOpen = openPanel;
window.MengBaoPromptOrganizerOpen = openPanel;
