import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { analysisQueue, draftFor, labels, newId, normalizeLanguage } from "./replica_model.js";
import { fileUrl, invalidateReplicaEditor, openReplicaEditor, refreshReplicaEditorLocale, replicaRequest } from "./replica_editor.js";

const REVERSE = "MengBaoImageReverse", SETTINGS = "MengBaoImageReplicaSettings", AUDIT = "MengBaoReplicaAudit";
const CLASSES = new Set([REVERSE, SETTINGS, AUDIT]);
let capabilities = {};
function language() { return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale")); }
function nodeClass(node) { return node?.comfyClass || node?.type; }
function widget(node, name) { return node.widgets?.find(value => value.name === name); }
function graphNode(id) { return app.graph?.getNodeById?.(id); }
function linkById(id) { return app.graph?.links?.get?.(id) || app.graph?.links?.[id]; }
function linkedAnalysis(node) {
  const input = node.inputs?.find(input => input.name === "analysis");
  return graphNode(linkById(input?.link)?.origin_id);
}
function currentDraft(node) {
  try { return JSON.parse(widget(node, "draft_json")?.value || "null"); }
  catch { return null; }
}
function storeDraft(node, draft) {
  const control = widget(node, "draft_json");
  if (control) control.value = JSON.stringify(draft);
  app.graph?.setDirtyCanvas?.(true, true);
  renderNode(node);
}
function modelLimit(node) {
  const output = node.outputs?.find(output => output.name === "replica_settings");
  const limits = (output?.links || []).map(id => graphNode(linkById(id)?.target_id)).filter(node => nodeClass(node) === "WANGImageAPI")
    .map(node => capabilities[widget(node, "model_type")?.value]).filter(Number.isFinite);
  return limits.length ? Math.min(...limits) : Math.max(16, ...Object.values(capabilities));
}
function hideTechnicalWidgets(node) {
  for (const name of ["request_id", "draft_json", "draft_id"]) {
    const control = widget(node, name);
    if (!control) continue;
    control.type = "hidden"; control.hidden = true;
    control.computeSize = () => [0, -4]; control.draw = () => {};
    if (control.inputEl) control.inputEl.style.display = "none";
    if (control.element) control.element.style.display = "none";
  }
}
function renderNode(node) {
  const state = node._mengBaoReplicaState, controls = node._mengBaoReplicaControls;
  if (!state || !controls) return;
  const text = labels(language()), type = nodeClass(node);
  state.language = language();
  node.title = type === REVERSE ? text.reverseTitle : type === SETTINGS ? text.settingsTitle : text.auditTitle;
  const names = { image: text.source, analysis: text.analysis, images: text.images, replica_settings: text.settings };
  for (const input of node.inputs || []) if (names[input.name]) input.label = input.localized_name = names[input.name];
  const outputs = type === REVERSE ? [text.analysis, text.reversePrompt] : type === SETTINGS ? [text.prompt, text.settings] : [text.images, text.report];
  for (const [index, output] of (node.outputs || []).entries()) output.label = output.localized_name = outputs[index];
  if (type === AUDIT) {
    controls.report.textContent = state.report || text.empty;
    controls.status.textContent = state.error || (state.stage ? `${text[state.stage] || text.requesting} · ${state.model || ""}` : state.report ? text.auditReady : "");
  } else {
    const record = state.record;
    controls.image.hidden = !record; controls.empty.hidden = Boolean(record); controls.empty.textContent = text.empty;
    if (record) { const url = fileUrl(record.source.id); if (controls.image.getAttribute("src") !== url) controls.image.src = url; }
    controls.button.textContent = type === SETTINGS ? text.open : record ? text.reanalyze : text.analyze;
    controls.button.disabled = state.busy || (type === SETTINGS && !record);
    const ready = type === SETTINGS ? currentDraft(node)?.confirmed ? text.confirmed : text.unconfirmed : text.ready;
    const attempts = (record?.attempts || []).filter(attempt => !attempt.success).map(attempt => `\n${attempt.model}: ${attempt.error}`).join("");
    controls.status.textContent = state.error || (state.busy ? `${text[state.stage] || text.requesting} · ${state.model || "gem-3.7-flash"}${state.previousError ? `\n${text.switching}\n${state.previousError}` : ""}` : record ? `${ready} · ${record.model}\n${record.analysis.elements.length} · ${text.analysis}${attempts}` : "");
  }
  node.setDirtyCanvas?.(true, true);
}
function refreshSettings(node) {
  const source = linkedAnalysis(node), record = source?._mengBaoReplicaState?.record;
  if (record && widget(source, "request_id")?.value === record.id) {
    const old = node._mengBaoReplicaState.record;
    node._mengBaoReplicaState.record = record;
    const draft = draftFor(record, currentDraft(node));
    if (old?.id && old.id !== record.id) invalidateReplicaEditor(old.id);
    storeDraft(node, draft);
  } else { node._mengBaoReplicaState.record = null; renderNode(node); }
}
function receiveAnalysis(node, record) {
  if (!record?.analysis || record.id !== widget(node, "request_id")?.value) return;
  Object.assign(node._mengBaoReplicaState, { record, busy: false, stage: "", error: "", model: record.model, previousError: "" });
  renderNode(node);
  for (const target of app.graph?._nodes || []) if (nodeClass(target) === SETTINGS && linkedAnalysis(target) === node) refreshSettings(target);
}
async function analyze(node) {
  const state = node._mengBaoReplicaState;
  if (state.busy) return;
  widget(node, "request_id").value = newId();
  Object.assign(state, { busy: true, stage: "requesting", model: "gem-3.7-flash", error: "", previousError: "" });
  renderNode(node);
  for (const target of app.graph?._nodes || []) if (nodeClass(target) === SETTINGS && linkedAnalysis(target) === node) refreshSettings(target);
  try {
    const prompt = await app.graphToPrompt();
    const payload = { ...analysisQueue(node.id, prompt.output), client_id: api.clientId };
    const response = await api.fetchApi("/prompt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(JSON.stringify(data.error || data.node_errors || `HTTP ${response.status}`));
    state.promptId = data.prompt_id;
  } catch (error) { state.busy = false; state.error = error.message; renderNode(node); }
}
async function edit(node) {
  refreshSettings(node);
  const state = node._mengBaoReplicaState;
  if (!state.record) { state.error = labels(language()).noAnalysis; renderNode(node); return; }
  try {
    capabilities = await replicaRequest("/capabilities");
    const record = state.record;
    await openReplicaEditor({ record, draft: draftFor(record, currentDraft(node)), draftId: widget(node, "draft_id").value,
      onChange: draft => storeDraft(node, draft), language, limit: () => modelLimit(node) });
  } catch (error) { state.error = error.message; renderNode(node); }
}
async function restore(node) {
  try {
    if (nodeClass(node) === REVERSE && widget(node, "request_id")?.value) {
      const id = widget(node, "request_id").value;
      const record = await replicaRequest(`/analysis/${id}`);
      if (widget(node, "request_id")?.value === id) receiveAnalysis(node, record);
    } else if (nodeClass(node) === SETTINGS) {
      if (!currentDraft(node)) { const draft = await replicaRequest(`/drafts/${widget(node, "draft_id").value}`); if (draft.analysis_id) storeDraft(node, draft); }
      refreshSettings(node);
    }
  } catch (error) { node._mengBaoReplicaState.error = error.message; renderNode(node); }
}
function configure(node) {
  hideTechnicalWidgets(node);
  if (nodeClass(node) === SETTINGS && !widget(node, "draft_id")?.value) widget(node, "draft_id").value = newId();
  if (!node._mengBaoReplicaControls) {
    node._mengBaoReplicaState = { record: null, busy: false, error: "", report: "" };
    const root = document.createElement("div"); root.className = "mengbao-replica-node";
    const status = document.createElement("div"); status.className = "replica-node-status"; status.setAttribute("role", "status");
    const controls = { root, status };
    if (nodeClass(node) === AUDIT) { controls.report = document.createElement("pre"); controls.report.className = "replica-node-report"; root.append(controls.report); }
    else {
      controls.image = document.createElement("img"); controls.image.alt = "Source"; controls.image.hidden = true;
      controls.empty = document.createElement("div"); controls.empty.className = "replica-node-empty";
      controls.button = document.createElement("button"); controls.button.type = "button";
      controls.button.addEventListener("click", () => nodeClass(node) === REVERSE ? analyze(node) : edit(node));
      root.append(controls.image, controls.empty, controls.button);
    }
    root.append(status); node._mengBaoReplicaControls = controls;
    node.addDOMWidget("mengbao_replica_controls", "mengbao-replica", root, { serialize: false, hideOnZoom: false, getMinHeight: () => 350, getMaxHeight: () => 350 });
    node.setSize?.([Math.max(360, node.size?.[0] || 0), node.computeSize?.()[1] || 410]);
  }
  renderNode(node); void restore(node);
}
function installListeners() {
  api.addEventListener?.("mengbao_replica_status", ({ detail }) => {
    const node = graphNode(detail.node_id), state = node?._mengBaoReplicaState;
    if (!state || (detail.request_id && detail.request_id !== widget(node, "request_id")?.value)) return;
    Object.assign(state, { stage: detail.stage, model: detail.model, previousError: detail.previous_error || "" }); renderNode(node);
  });
  api.addEventListener?.("executed", ({ detail }) => {
    const node = graphNode(detail.node);
    if (detail.output?.mengbao_replica_analysis && node?._mengBaoReplicaState) receiveAnalysis(node, detail.output.mengbao_replica_analysis[0]);
    if (detail.output?.mengbao_replica_report && node?._mengBaoReplicaState) { Object.assign(node._mengBaoReplicaState, { report: detail.output.mengbao_replica_report[0], stage: "", error: "" }); renderNode(node); }
    const notice = detail.output?.mengbao_replica_ratio?.[0];
    if (notice) {
      const [w, h] = notice.ratio.split(":").map(Number);
      if (notice.auto_resolution_mapped || Math.abs(w / h - notice.source_width / notice.source_height) > 1e-9) app.extensionManager?.toast?.add?.({ severity: "info", summary: labels(language()).ratio, detail: `${notice.source_width}×${notice.source_height} → ${notice.ratio}${notice.auto_resolution_mapped ? ` · ${labels(language()).autoResolution}` : ""}`, life: 9000 });
    }
  });
  for (const eventName of ["execution_error", "execution_interrupted"]) api.addEventListener?.(eventName, ({ detail }) => {
    for (const node of app.graph?._nodes || []) {
      const state = node._mengBaoReplicaState;
      if (!state || state.promptId !== detail.prompt_id) continue;
      state.busy = false; state.stage = ""; state.error = detail.exception_message || "Vision request cancelled"; renderNode(node);
    }
  });
  const locale = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
  if (locale) { const original = locale.onChange; locale.onChange = function (...args) { const result = original?.apply(this, args); setTimeout(() => { for (const node of app.graph?._nodes || []) if (CLASSES.has(nodeClass(node))) renderNode(node); refreshReplicaEditorLocale(); }, 0); return result; }; }
}
app.registerExtension({
  name: "MengBaoAI.replica",
  setup() {
    if (!document.querySelector("#mengbao-replica-style")) { const link = document.createElement("link"); link.id = "mengbao-replica-style"; link.rel = "stylesheet"; link.href = new URL("./replica.css", import.meta.url).href; document.head.append(link); }
    installListeners();
  },
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (!CLASSES.has(nodeData.name)) return;
    for (const name of ["onNodeCreated", "onConfigure"]) {
      const original = nodeType.prototype[name]; nodeType.prototype[name] = function () { const result = original?.apply(this, arguments); configure(this); return result; };
    }
    const executed = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      const result = executed?.apply(this, arguments);
      if (message?.mengbao_replica_analysis) receiveAnalysis(this, message.mengbao_replica_analysis[0]);
      if (message?.mengbao_replica_report) { Object.assign(this._mengBaoReplicaState, { report: message.mengbao_replica_report[0], stage: "" }); renderNode(this); }
      return result;
    };
    const connections = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function () { const result = connections?.apply(this, arguments); if (nodeClass(this) === SETTINGS) setTimeout(() => refreshSettings(this), 0); return result; };
    const foreground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function () { if (this._mengBaoReplicaState?.language !== language()) renderNode(this); return foreground?.apply(this, arguments); };
  },
});
export { analyze, configure, modelLimit, receiveAnalysis, renderNode };
