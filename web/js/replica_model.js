const LABELS = {
  zh: {
    reverseTitle: "萌宝AI·图片反推", settingsTitle: "萌宝AI·图片复刻设置", auditTitle: "萌宝AI·复刻检查",
    source: "原图", analysis: "分析数据", reversePrompt: "反推提示词", prompt: "提示词", settings: "复刻设置", images: "图像", report: "检查报告",
    analyze: "识别图片", reanalyze: "重新识别", open: "打开复刻设置", empty: "尚未识别图片", ready: "已识别", requesting: "正在分析", parsing: "正在解析元素", switching: "连接失败，正在切换备用模型", confirmed: "设置已确认", unconfirmed: "设置尚未确认",
    close: "关闭", save: "保存草稿", confirm: "确认设置", saved: "草稿已保存", saving: "正在保存", add: "添加元素", remove: "删除元素",
    composition: "构图与风格", name: "元素名称", kind: "元素类型", parent: "归属产品", independent: "独立元素", group: "同款产品分组", link: "联动替换同款产品",
    action: "操作", keep: "保留", replace: "替换", originalText: "原文", newText: "新文案", style: "文字样式", description: "原元素描述", replacement: "替换描述", reviewed: "内容已核对", inherited: "随目标产品更新",
    position: "位置 (%)", positionConfirm: "确认位置", pending: "位置待确认", contentPending: "内容待核对", clipped: "已裁至图片边界",
    references: "替换参考图", upload: "添加素材", material: "加载素材", uploadHint: "点击上传、拖拽或 Ctrl+V 粘贴图片", aiDescribe: "AI 产品描述", describing: "正在编写产品描述", viewer: "查看原图", newElement: "新元素", count: "参考图", noAnalysis: "请先连接反推节点并点击“识别图片”", invalidPosition: "请填写有效的位置：坐标在 0–100%，宽高大于 0，且不能超出图片边界。",
    limit: "参考图超过所连接模型的数量限制", ratio: "复刻比例", autoResolution: "为保持复刻比例，自动分辨率已按 GPT 模型基础档映射为 1K", auditReady: "检查已完成", checked: "通过", mismatch: "发现文字差异", failed: "检查失败",
  },
  en: {
    reverseTitle: "MengBao AI · Image Reverse", settingsTitle: "MengBao AI · Replica Settings", auditTitle: "MengBao AI · Replica Audit",
    source: "Source Image", analysis: "Analysis", reversePrompt: "Reverse Prompt", prompt: "Prompt", settings: "Replica Settings", images: "Images", report: "Report",
    analyze: "Analyze Image", reanalyze: "Re-analyze", open: "Open Replica Settings", empty: "No image analyzed", ready: "Analyzed", requesting: "Analyzing", parsing: "Parsing elements", switching: "Connection failed; switching to backup", confirmed: "Settings confirmed", unconfirmed: "Settings not confirmed",
    close: "Close", save: "Save Draft", confirm: "Confirm Settings", saved: "Draft saved", saving: "Saving", add: "Add Element", remove: "Delete Element",
    composition: "Composition and Style", name: "Element Name", kind: "Element Type", parent: "Parent Product", independent: "Independent", group: "Product Group", link: "Link matching products",
    action: "Action", keep: "Keep", replace: "Replace", originalText: "Original Copy", newText: "Replacement Copy", style: "Text Style", description: "Original Description", reviewed: "Content reviewed", replacement: "Replacement Description", inherited: "Updates with target product",
    position: "Position (%)", positionConfirm: "Confirm Position", pending: "Position needs review", contentPending: "Content needs review", clipped: "Clipped to image boundary",
    references: "Replacement References", upload: "Add References", material: "Load Material", uploadHint: "Click upload, drop or press Ctrl+V to paste images", aiDescribe: "AI Product Description", describing: "Writing product description", viewer: "View Original", newElement: "New Element", count: "References", noAnalysis: "Connect Image Reverse and click Analyze Image first", invalidPosition: "Enter valid percentages: coordinates 0–100%, positive width/height, and no overflow beyond the image.",
    limit: "Reference count exceeds the connected model limit", ratio: "Replica ratio", autoResolution: "Auto resolution mapped to the GPT base 1K tier to preserve the replica ratio", auditReady: "Audit completed", checked: "Passed", mismatch: "Copy differences found", failed: "Audit failed",
  },
};
const KIND_LABELS = { zh: { product: "产品", text: "文字", logo: "品牌标识", background: "背景场景", person: "人物", decoration: "装饰", other: "其他" }, en: { product: "Product", text: "Text", logo: "Logo", background: "Background", person: "Person", decoration: "Decoration", other: "Other" } };
function normalizeLanguage(locale) { return String(locale || "").toLowerCase().startsWith("zh") ? "zh" : "en"; }
function labels(locale) { return LABELS[normalizeLanguage(locale)]; }
function newId() { return crypto.randomUUID().replaceAll("-", ""); }
function replacement(draft, id) { return draft.replacements[id] || { mode: "keep", text: "", description: "", images: [] }; }
function draftFor(record, existing) {
  if (existing?.analysis_id === record.id && Array.isArray(existing.analysis?.elements)) return structuredClone(existing);
  return { analysis_id: record.id, analysis: structuredClone(record.analysis), replacements: {}, linkedGroups: [], confirmed: false };
}
function changeReplacement(draft, element, patch) {
  const group = element.kind === "product" && element.productGroup;
  const targets = group && draft.linkedGroups?.includes(group) ? draft.analysis.elements.filter(item => item.kind === "product" && item.productGroup === group) : [element];
  for (const target of targets) draft.replacements[target.id] = { ...replacement(draft, target.id), ...structuredClone(patch) };
  draft.confirmed = false;
}
function inherited(draft, element) { return Boolean(element.parentId && replacement(draft, element.parentId).mode === "replace"); }
function removeElement(draft, id) {
  const removed = new Set([id, ...draft.analysis.elements.filter(element => element.parentId === id).map(element => element.id)]);
  draft.analysis.elements = draft.analysis.elements.filter(element => !removed.has(element.id));
  for (const id of removed) delete draft.replacements[id];
  draft.confirmed = false;
}
function references(draft, sourceId) {
  const ids = [sourceId];
  for (const element of draft.analysis.elements) {
    const value = replacement(draft, element.id);
    if (inherited(draft, element) || element.kind === "text" || value.mode !== "replace") continue;
    for (const id of value.images || []) if (!ids.includes(id)) ids.push(id);
  }
  return ids;
}
function validBox(box) {
  return box && [box.x, box.y, box.w, box.h].every(Number.isFinite) && box.x >= 0 && box.y >= 0 && box.w > 0 && box.h > 0 && box.x + box.w <= 1 + 1e-12 && box.y + box.h <= 1 + 1e-12;
}
function analysisQueue(nodeId, output) {
  const root = String(nodeId), selected = {};
  function collect(id) {
    if (selected[id]) return;
    const node = output[id];
    if (!node) throw new Error(`Cannot resolve analysis dependency: ${id}`);
    selected[id] = node;
    for (const value of Object.values(node.inputs || {})) {
      if (Array.isArray(value) && value.length === 2 && typeof value[0] === "string" && typeof value[1] === "number") collect(value[0]);
    }
  }
  collect(root);
  return { prompt: selected, partial_execution_targets: [root] };
}
export { KIND_LABELS, analysisQueue, changeReplacement, draftFor, inherited, labels, newId, normalizeLanguage, references, removeElement, replacement, validBox };
