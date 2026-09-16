import { api } from "../../../scripts/api.js";
import { bindUploadTarget, isEditableTarget } from "./material_uploads.js";
import { materialFileUrl, openMaterialLibrary, refreshMaterialDialogLocale } from "./material_library.js";
import { KIND_LABELS, changeReplacement, inherited, labels, newId, normalizeLanguage, references, removeElement, replacement, validBox } from "./replica_model.js";

let activeEditor = null;
async function replicaRequest(path, options) {
  const response = await api.fetchApi(`/mengbao_replica${path}`, options);
  const data = await response.json();
  if (!response.ok || data?.error) throw new Error(data?.error?.message || `HTTP ${response.status}`);
  return data;
}
function jsonOptions(data) { return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }; }
function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}
function button(text, action, className = "") {
  const control = element("button", className, text);
  control.type = "button";
  control.addEventListener("click", action);
  return control;
}
function fileUrl(id) { return api.apiURL?.(`/mengbao_replica/assets/${id}/file`) || `/mengbao_replica/assets/${id}/file`; }

async function openReplicaEditor(options) {
  if (activeEditor && !(await activeEditor.close())) return;
  const { record, draft, draftId, onChange, language, limit } = options;
  const dialog = element("dialog", "mengbao-replica-dialog");
  dialog.setAttribute("data-mengbao-upload-scope", "");
  let selected = draft.analysis.elements[0]?.id, busy = false, closed = false, notice = "", descriptionRequestId = "", timer, saveChain = Promise.resolve();
  const bindings = [];
  const text = () => labels(language());
  const descriptionStatus = event => {
    const detail = event.detail;
    if (closed || !descriptionRequestId || detail.request_id !== descriptionRequestId) return;
    notice = `${text().describing} · ${detail.model}${detail.previous_error ? `\n${detail.previous_error}` : ""}`;
    renderStatus();
  };
  api.addEventListener("mengbao_replica_description_status", descriptionStatus);
  const header = element("header");
  const title = element("h2");
  const closeButton = button("×", () => void close(), "replica-close");
  header.append(title, closeButton);
  const body = element("div", "replica-body");
  const canvasPane = element("section", "replica-canvas-pane");
  const compositionLabel = element("label", "replica-field");
  const compositionName = element("span");
  const composition = element("textarea");
  composition.rows = 3;
  composition.value = draft.analysis.composition;
  composition.addEventListener("input", () => { draft.analysis.composition = composition.value; changed(); });
  compositionLabel.append(compositionName, composition);
  const stage = element("div", "replica-stage");
  const image = element("img", "replica-source");
  image.src = fileUrl(record.source.id);
  image.alt = record.source.name;
  const overlay = element("div", "replica-overlay");
  stage.append(image, overlay);
  const viewerButton = button("", () => viewImage(record.source.id));
  canvasPane.append(stage, viewerButton, compositionLabel);
  const editorPane = element("section", "replica-editor-pane");
  body.append(canvasPane, editorPane);
  const fitSource = () => { stage.style.width = `${Math.max(1, Math.min(canvasPane.clientWidth - 28, Math.max(120, canvasPane.clientHeight - 70) * record.source.width / record.source.height))}px`; };
  const resizeObserver = new ResizeObserver(fitSource);
  resizeObserver.observe(canvasPane);
  const footer = element("footer");
  const status = element("div", "replica-status");
  status.setAttribute("role", "status");
  const footerActions = element("div", "replica-footer-actions");
  const saveButton = button("", () => void perform(() => save(false)), "replica-secondary");
  const confirmButton = button("", () => void perform(() => save(true)), "replica-primary");
  footerActions.append(saveButton, confirmButton);
  footer.append(status, footerActions);
  dialog.append(header, body, footer);
  document.body.append(dialog);

  function changed() {
    draft.confirmed = false;
    notice = "";
    onChange(structuredClone(draft));
    renderStatus();
    clearTimeout(timer);
    timer = setTimeout(() => { enqueueSave(structuredClone(draft)); }, 500);
  }
  function enqueueSave(snapshot) {
    saveChain = saveChain.catch(() => {}).then(() => replicaRequest(`/drafts/${draftId}`, jsonOptions(snapshot)));
    saveChain.catch(error => { if (!closed) { notice = error.message; renderStatus(); } });
    return saveChain;
  }
  async function save(confirm) {
    clearTimeout(timer);
    await saveChain.catch(() => {});
    const snapshot = { ...structuredClone(draft), confirmed: confirm };
    if (confirm && references(snapshot, record.source.id).length > limit()) throw new Error(text().limit);
    await enqueueSave(snapshot);
    draft.confirmed = confirm;
    onChange(structuredClone(draft));
    notice = confirm ? text().confirmed : text().saved;
    if (confirm) dialog.close();
  }
  async function perform(action) {
    if (busy) return;
    busy = true;
    renderStatus();
    try { await action(); }
    catch (error) { notice = error.message; }
    finally { busy = false; if (!closed) { renderStatus(); renderEditor(); } }
  }
  async function close() {
    if (busy) return false;
    busy = true;
    renderStatus();
    try {
      clearTimeout(timer);
      await saveChain.catch(() => {});
      await enqueueSave(structuredClone(draft));
      dialog.close();
      return true;
    } catch (error) { notice = error.message; busy = false; renderStatus(); return false; }
  }
  function renderStatus() {
    const count = references(draft, record.source.id).length;
    status.textContent = `${count}/${limit()} ${text().count} · ${notice || (busy ? text().saving : draft.confirmed ? text().confirmed : text().unconfirmed)}`;
    status.classList.toggle("error", count > limit());
    for (const control of dialog.querySelectorAll("input, textarea, select, button")) control.disabled = busy;
    for (const control of dialog.querySelectorAll("[data-requires-images]")) control.disabled = busy || !(replacement(draft, control.dataset.elementId).images || []).length;
    saveButton.disabled = confirmButton.disabled = closeButton.disabled = busy;
  }
  function field(label, value, onInput, multiline = false) {
    const wrapper = element("label", "replica-field");
    const control = element(multiline ? "textarea" : "input");
    if (multiline) control.rows = 3;
    else control.type = "text";
    control.value = value || "";
    control.setAttribute("aria-label", label);
    control.addEventListener("input", () => { onInput(control.value); changed(); paintBoxes(); });
    wrapper.append(element("span", "", label), control);
    return wrapper;
  }
  function selectField(label, value, choices, change) {
    const wrapper = element("label", "replica-field");
    const select = element("select");
    select.setAttribute("aria-label", label);
    for (const [id, name] of Object.entries(choices)) {
      const option = element("option", "", name); option.value = id; select.append(option);
    }
    select.value = value;
    select.addEventListener("change", () => { change(select.value); changed(); renderEditor(); renderBoxes(); });
    wrapper.append(element("span", "", label), select);
    return wrapper;
  }
  function checkbox(label, checked, change) {
    const wrapper = element("label", "replica-checkbox");
    const input = element("input"); input.type = "checkbox"; input.checked = checked;
    input.addEventListener("change", () => { change(input.checked); changed(); renderEditor(); });
    wrapper.append(input, element("span", "", label));
    return wrapper;
  }
  function select(id) { selected = id; renderEditor(); paintBoxes(); }
  function paintBoxes() {
    for (const box of overlay.children) {
      const item = draft.analysis.elements.find(item => item.id === box.dataset.elementId);
      if (!item?.box) continue;
      box.style.left = `${item.box.x * 100}%`; box.style.top = `${item.box.y * 100}%`;
      box.style.width = `${item.box.w * 100}%`; box.style.height = `${item.box.h * 100}%`;
      box.classList.toggle("selected", item.id === selected);
      box.classList.toggle("pending", item.boxStatus === "pending");
      box.style.zIndex = item.kind === "background" ? "0" : String((item.id === selected ? 200 : 0) + 100 - Math.round(item.box.w * item.box.h * 100));
      box.title = item.name;
    }
  }
  function renderBoxes() {
    overlay.replaceChildren();
    draft.analysis.elements.forEach((item, index) => {
      if (!validBox(item.box)) return;
      const box = button(String(index + 1), () => select(item.id), "replica-box");
      box.dataset.elementId = item.id;
      const handle = element("span", "replica-handle", "↘");
      box.append(handle);
      box.addEventListener("pointerdown", event => {
        if (busy || event.button !== 0) return;
        event.preventDefault(); event.stopPropagation();
        selected = item.id; renderEditor(); paintBoxes();
        const initial = { ...item.box }, bounds = stage.getBoundingClientRect();
        const startX = event.clientX, startY = event.clientY, resizing = event.target === handle;
        box.setPointerCapture(event.pointerId);
        const move = event => {
          const dx = (event.clientX - startX) / bounds.width, dy = (event.clientY - startY) / bounds.height;
          item.box = resizing ? { ...initial, w: Math.max(.005, Math.min(1 - initial.x, initial.w + dx)), h: Math.max(.005, Math.min(1 - initial.y, initial.h + dy)) }
            : { ...initial, x: Math.max(0, Math.min(1 - initial.w, initial.x + dx)), y: Math.max(0, Math.min(1 - initial.h, initial.y + dy)) };
          item.boxStatus = "pending"; paintBoxes(); changed();
        };
        const end = () => { box.removeEventListener("pointermove", move); box.removeEventListener("pointerup", end); box.removeEventListener("pointercancel", end); renderEditor(); };
        box.addEventListener("pointermove", move); box.addEventListener("pointerup", end); box.addEventListener("pointercancel", end);
      });
      overlay.append(box);
    });
    paintBoxes();
  }
  function positionFields(item) {
    const wrapper = element("div", "replica-position");
    wrapper.append(element("span", "replica-position-label", `${text().position} · ${item.boxStatus === "pending" || !item.box ? text().pending : item.boxStatus === "clipped" ? text().clipped : ""}`));
    const controls = {};
    for (const key of ["x", "y", "w", "h"]) {
      const label = element("label"); const input = element("input");
      input.type = "number"; input.min = "0"; input.max = "100"; input.step = "0.1";
      input.value = item.box ? String(Number((item.box[key] * 100).toFixed(3))) : "";
      input.setAttribute("aria-label", `${item.id} ${key} %`);
      controls[key] = input;
      input.addEventListener("input", () => {
        const next = Object.fromEntries(Object.entries(controls).map(([key, input]) => [key, input.value.trim() ? Number(input.value) / 100 : NaN]));
        item.box = validBox(next) ? next : null; item.boxStatus = "pending"; changed(); renderBoxes();
      });
      label.append(element("span", "", key.toUpperCase()), input); wrapper.append(label);
    }
    const confirm = button(text().positionConfirm, () => {
      const box = Object.fromEntries(Object.entries(controls).map(([key, input]) => [key, input.value.trim() ? Number(input.value) / 100 : NaN]));
      if (!validBox(box)) { notice = text().invalidPosition; renderStatus(); return; }
      item.box = box; item.boxStatus = "valid"; changed(); renderBoxes(); renderEditor();
    });
    wrapper.append(confirm);
    return wrapper;
  }
  async function upload(item, files) {
    if (references(draft, record.source.id).length + files.length > limit()) throw new Error(text().limit);
    for (const file of files) {
      const form = new FormData(); form.append("image", file, file.name || "clipboard.png");
      const asset = await replicaRequest("/assets", { method: "POST", body: form });
      const ids = [...new Set([...(replacement(draft, item.id).images || []), asset.id])];
      changeReplacement(draft, item, { images: ids }); changed();
    }
  }
  function referenceFields(item) {
    const wrapper = element("div", "replica-references");
    wrapper.append(element("span", "", text().references));
    const zone = element("div", "replica-upload-zone"); zone.tabIndex = 0;
    zone.setAttribute("aria-label", text().uploadHint);
    const thumbnails = element("div", "replica-thumbnails");
    for (const id of replacement(draft, item.id).images || []) {
      const thumbnail = element("div", "replica-thumbnail");
      const view = button("", () => viewImage(id));
      const image = element("img"); image.src = fileUrl(id); image.alt = text().references; view.append(image);
      const remove = button("×", () => { changeReplacement(draft, item, { images: replacement(draft, item.id).images.filter(value => value !== id) }); changed(); renderEditor(); }, "replica-reference-remove");
      remove.title = text().remove;
      thumbnail.append(view, remove); thumbnails.append(thumbnail);
    }
    zone.append(thumbnails, element("span", "replica-upload-hint", text().uploadHint));
    const binding = bindUploadTarget(zone, { maxFiles: 16, available: () => !busy && !closed && !document.querySelector(".mengbao-material-dialog[open]") && references(draft, record.source.id).length < limit(),
      upload: files => perform(async () => upload(item, files)), onError: error => { notice = error.message; renderStatus(); } });
    bindings.push(binding);
    zone.addEventListener("click", event => { if (!event.target.closest("button")) binding.chooseFiles(); });
    const actions = element("div", "replica-reference-actions");
    actions.append(button(text().upload, () => binding.chooseFiles(), "replica-primary"), button(text().material, () => {
      dialog.removeAttribute("data-mengbao-upload-scope");
      const library = openMaterialLibrary({ language, onSelect: async asset => {
        const response = await api.fetchApi(materialFileUrl(asset.id));
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const file = new File([await response.blob()], asset.name, { type: "image/png" });
        await perform(() => upload(item, [file]));
      } });
      library.addEventListener("close", () => { if (!closed) dialog.setAttribute("data-mengbao-upload-scope", ""); });
    }));
    wrapper.append(zone, actions);
    return wrapper;
  }
  function renderEditor() {
    for (const binding of bindings.splice(0)) binding.dispose();
    editorPane.replaceChildren();
    editorPane.append(button(text().add, () => {
      if (draft.analysis.elements.length >= 100) return;
      const item = { id: `e_${newId()}`, name: text().newElement, kind: "other", description: "", text: "", textStyle: "", needsConfirmation: true, box: { x: .1, y: .1, w: .3, h: .3 }, boxStatus: "pending" };
      draft.analysis.elements.push(item); selected = item.id; changed(); renderEditor(); renderBoxes();
    }, "replica-primary replica-add"));
    draft.analysis.elements.forEach((item, index) => {
      const entry = element("details", "replica-element"); entry.open = item.id === selected;
      const summary = element("summary");
      summary.textContent = `${index + 1}. ${item.name} · ${inherited(draft, item) ? text().inherited : labels(language())[replacement(draft, item.id).mode]}`;
      if (!item.box || item.boxStatus === "pending") summary.append(element("span", "replica-review", text().pending));
      if (!inherited(draft, item) && replacement(draft, item.id).mode === "keep" && item.needsConfirmation) summary.append(element("span", "replica-review", text().contentPending));
      summary.addEventListener("click", event => { event.preventDefault(); select(item.id === selected ? null : item.id); });
      entry.append(summary);
      if (entry.open) {
        const fields = element("fieldset");
        fields.append(field(text().name, item.name, value => { item.name = value; }));
        fields.append(selectField(text().kind, item.kind, KIND_LABELS[normalizeLanguage(language())], value => { item.kind = value; delete item.parentId; delete item.productGroup; }));
        if (item.kind === "text" || item.kind === "logo") fields.append(selectField(text().parent, item.parentId || "", { "": text().independent, ...Object.fromEntries(draft.analysis.elements.filter(value => value.kind === "product").map(value => [value.id, value.name])) }, value => { if (value) item.parentId = value; else delete item.parentId; }));
        fields.append(positionFields(item));
        if (item.kind === "product") {
          fields.append(field(text().group, item.productGroup, value => { item.productGroup = value.trim(); }));
          if (item.productGroup) fields.append(checkbox(text().link, draft.linkedGroups?.includes(item.productGroup), checked => {
            draft.linkedGroups = (draft.linkedGroups || []).filter(value => value !== item.productGroup);
            if (checked) { draft.linkedGroups.push(item.productGroup); changeReplacement(draft, item, replacement(draft, item.id)); }
          }));
        }
        if (!inherited(draft, item)) {
          fields.append(selectField(text().action, replacement(draft, item.id).mode, { keep: text().keep, replace: text().replace }, value => changeReplacement(draft, item, { mode: value })));
          const value = replacement(draft, item.id);
          if (item.kind === "text") {
            fields.append(field(text().originalText, item.text, value => { item.text = value; }, true));
            fields.append(field(text().style, item.textStyle, value => { item.textStyle = value; }, true));
            if (value.mode === "replace") fields.append(field(text().newText, value.text, value => changeReplacement(draft, item, { text: value }), true));
          } else fields.append(field(text().description, item.description, value => { item.description = value; }, true));
          if (value.mode === "keep") fields.append(checkbox(text().reviewed, !item.needsConfirmation, checked => { item.needsConfirmation = !checked; }));
          else if (item.kind !== "text") {
            fields.append(field(text().replacement, value.description, value => changeReplacement(draft, item, { description: value }), true));
            fields.append(referenceFields(item));
            if (item.kind === "product") {
              const describe = button(text().aiDescribe, () => void perform(async () => {
                notice = text().describing; renderStatus();
                const value = replacement(draft, item.id);
                descriptionRequestId = newId();
                try {
                  const result = await replicaRequest("/describe", jsonOptions({ request_id: descriptionRequestId, client_id: api.clientId, element: item, images: value.images || [], description: value.description || "" }));
                  changeReplacement(draft, item, { description: result.data }); changed();
                  notice = `${text().aiDescribe} · ${result.model}${result.attempts.filter(attempt => !attempt.success).map(attempt => `\n${attempt.model}: ${attempt.error}`).join("")}`;
                } finally { descriptionRequestId = ""; }
              }), "replica-primary");
              describe.disabled = !(value.images || []).length;
              describe.dataset.requiresImages = "true"; describe.dataset.elementId = item.id;
              fields.append(describe);
            }
          }
        }
        fields.append(button(text().remove, () => {
          removeElement(draft, item.id); selected = draft.analysis.elements[0]?.id; changed(); renderEditor(); renderBoxes();
        }, "replica-delete"));
        entry.append(fields);
      }
      editorPane.append(entry);
    });
    renderStatus();
    for (const control of dialog.querySelectorAll("[data-requires-images]")) control.disabled = busy || !(replacement(draft, control.dataset.elementId).images || []).length;
  }
  function viewImage(id) {
    dialog.removeAttribute("data-mengbao-upload-scope");
    const viewer = element("dialog", "replica-viewer"); viewer.setAttribute("data-mengbao-upload-scope", "");
    const image = element("img"); image.src = fileUrl(id);
    viewer.append(button("×", () => viewer.close(), "replica-close"), image);
    viewer.addEventListener("click", event => { if (event.target === viewer) viewer.close(); });
    viewer.addEventListener("close", () => { viewer.remove(); if (!closed) dialog.setAttribute("data-mengbao-upload-scope", ""); });
    document.body.append(viewer); viewer.showModal();
  }
  function render() {
    title.textContent = text().settingsTitle; closeButton.title = text().close;
    compositionName.textContent = text().composition; viewerButton.textContent = text().viewer;
    saveButton.textContent = text().save; confirmButton.textContent = text().confirm;
    renderEditor(); renderBoxes(); refreshMaterialDialogLocale();
  }
  dialog.addEventListener("cancel", event => { event.preventDefault(); void close(); });
  dialog.addEventListener("keydown", event => {
    if (event.key !== "Delete" || busy || isEditableTarget(event.target)) return;
    const item = draft.analysis.elements.find(item => item.id === selected);
    if (!item) return;
    event.preventDefault(); removeElement(draft, item.id); selected = null; changed(); renderEditor(); renderBoxes();
  });
  dialog.addEventListener("close", () => { closed = true; clearTimeout(timer); api.removeEventListener("mengbao_replica_description_status", descriptionStatus); resizeObserver.disconnect(); for (const binding of bindings) binding.dispose(); dialog.remove(); if (activeEditor?.dialog === dialog) activeEditor = null; });
  activeEditor = { dialog, close, render, analysisId: record.id };
  render(); dialog.showModal();
  return activeEditor;
}
function refreshReplicaEditorLocale() { activeEditor?.render(); }
function invalidateReplicaEditor(analysisId) { if (activeEditor?.analysisId === analysisId) { activeEditor.dialog.close(); } }
export { fileUrl, invalidateReplicaEditor, openReplicaEditor, refreshReplicaEditorLocale, replicaRequest };
