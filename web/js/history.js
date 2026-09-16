import { api } from "../../../scripts/api.js";

const BASE = "/mengbao_history";
const TEXT = {
  zh: {
    title: "萌宝AI·历史记录", search: "搜索提示词 / 模型 / ID", all: "全部", running: "生成中",
    success: "已完成", partial: "部分完成", failed: "失败", refresh: "刷新", close: "关闭",
    auto: "自动刷新", newest: "最新优先", oldest: "最早优先", loading: "正在加载…",
    empty: "暂无生成记录", noMatch: "暂无匹配记录", prompt: "提示词", settings: "生成参数",
    download: "下载原图", preview: "预览图片", count: "张", previous: "上一页", next: "下一页",
    error: "错误信息", imageError: "Image preview could not be loaded",
  },
  en: {
    title: "MengBao AI · History", search: "Search prompt / model / ID", all: "All", running: "Generating",
    success: "Completed", partial: "Partially Completed", failed: "Failed", refresh: "Refresh", close: "Close",
    auto: "Auto Refresh", newest: "Newest First", oldest: "Oldest First", loading: "Loading...",
    empty: "No generations yet", noMatch: "No matching records", prompt: "Prompt", settings: "Generation Settings",
    download: "Download Original", preview: "Preview Image", count: "images", previous: "Previous", next: "Next",
    error: "Error", imageError: "Image preview could not be loaded",
  },
};
let activeDialog;

function historyLabels(language) { return TEXT[language === "zh" ? "zh" : "en"]; }
function historyFileUrl(id, index = 0, { thumbnail = false, download = false } = {}) {
  const query = new URLSearchParams();
  if (thumbnail) query.set("thumbnail", "1");
  if (download) query.set("download", "1");
  return `${BASE}/file/${encodeURIComponent(id)}/${index}${query.size ? `?${query}` : ""}`;
}
async function historyRequest(query) {
  const response = await api.fetchApi(`${BASE}/items?${new URLSearchParams(query)}`);
  const raw = await response.text();
  let payload;
  try { payload = JSON.parse(raw); } catch { throw new Error(raw || `HTTP ${response.status}`); }
  if (!response.ok || payload.error) throw new Error(payload.error?.message || `HTTP ${response.status}`);
  return payload;
}
function ensureHistoryStyles() {
  if (document.getElementById("mengbao-history-styles")) return;
  const link = document.createElement("link");
  link.id = "mengbao-history-styles";
  link.rel = "stylesheet";
  link.href = new URL("./history.css", import.meta.url).href;
  document.head.append(link);
}
function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}
function command(label, handler, icon = "") {
  const button = element("button", "", label);
  button.type = "button";
  if (icon) {
    button.textContent = "";
    const image = element("i", `pi pi-${icon}`);
    image.setAttribute("aria-hidden", "true");
    button.append(image);
  }
  button.title = label;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", handler);
  return button;
}

function openHistory({ language }) {
  if (activeDialog?.open) { activeDialog.focus(); return activeDialog; }
  ensureHistoryStyles();
  const dialog = element("dialog", "mengbao-history-dialog");
  const state = { items: [], counts: {}, total: 0, query: "", filter: "", offset: 0, oldest: false,
    auto: true, busy: false, closed: false, error: "", searchTimer: null, detail: null, detailsDialog: null };
  const text = () => historyLabels(language());
  const header = element("header");
  const title = element("h2");
  const actions = element("div", "mengbao-history-actions");
  const refresh = command(text().refresh, () => reload(), "refresh");
  const close = command(text().close, () => dialog.close(), "times");
  actions.append(refresh, close);
  header.append(title, actions);
  const toolbar = element("div", "mengbao-history-toolbar");
  const search = element("input");
  search.type = "search";
  const order = element("select");
  for (const value of ["newest", "oldest"]) {
    const option = element("option");
    option.value = value;
    order.append(option);
  }
  const autoLabel = element("label");
  const auto = element("input");
  auto.type = "checkbox";
  auto.checked = true;
  const autoText = element("span");
  autoLabel.append(auto, autoText);
  toolbar.append(search, order, autoLabel);
  const filters = element("nav", "mengbao-history-filters");
  filters.setAttribute("aria-label", text().title);
  const grid = element("div", "mengbao-history-grid");
  const status = element("div", "mengbao-history-status");
  status.setAttribute("role", "status");
  const footer = element("footer");
  const count = element("span");
  const pages = element("div", "mengbao-history-actions");
  const previous = command(text().previous, () => { state.offset = Math.max(0, state.offset - 60); reload(); }, "angle-left");
  const next = command(text().next, () => { state.offset += 60; reload(); }, "angle-right");
  pages.append(previous, next);
  footer.append(count, pages);
  dialog.append(header, toolbar, filters, grid, status, footer);
  document.body.append(dialog);
  activeDialog = dialog;

  async function reload() {
    if (state.busy || state.closed) return;
    state.busy = true;
    state.error = "";
    const requested = { query: state.query, state: state.filter, offset: state.offset, oldest: state.oldest ? "1" : "0" };
    render();
    try {
      const payload = await historyRequest(requested);
      if (!state.closed) Object.assign(state, { items: payload.items, counts: payload.counts, total: payload.total });
    } catch (error) { state.error = error.message; }
    finally {
      state.busy = false;
      if (!state.closed) {
        render();
        // 搜索或筛选在请求期间改变时，只重发最新条件，避免旧响应覆盖新条件。
        if (requested.query !== state.query || requested.state !== state.filter || requested.offset !== state.offset
          || requested.oldest !== (state.oldest ? "1" : "0")) reload();
      }
    }
  }

  function openDetails(item) {
    state.detailsDialog?.close();
    const details = element("dialog", "mengbao-history-dialog mengbao-history-detail");
    state.detail = item;
    state.detailsDialog = details;
    const head = element("header");
    head.append(element("h2", "", item.model), command(text().close, () => details.close(), "times"));
    const body = element("div", "mengbao-history-detail-body");
    const preview = element("img", "mengbao-history-original");
    preview.alt = text().preview;
    const downloads = element("div", "mengbao-history-thumbnails");
    for (const image of item.images) {
      const pick = command(`${text().preview} ${image.index + 1}`, () => { preview.src = historyFileUrl(item.id, image.index); });
      const thumb = element("img");
      thumb.src = historyFileUrl(item.id, image.index, { thumbnail: true });
      thumb.alt = `${image.width} × ${image.height}`;
      pick.replaceChildren(thumb);
      const download = element("a", "mengbao-history-download", `${text().download} ${image.index + 1}`);
      download.href = historyFileUrl(item.id, image.index, { download: true });
      download.download = `${item.model}-${item.id}-${image.index + 1}.png`;
      const group = element("div");
      group.append(pick, download);
      downloads.append(group);
    }
    if (item.images.length) preview.src = historyFileUrl(item.id, 0);
    else preview.hidden = true;
    preview.addEventListener("error", () => { preview.alt = text().imageError; });
    body.append(preview, downloads, element("h3", "", text().prompt), element("pre", "", item.prompt),
      element("h3", "", text().settings), element("pre", "", JSON.stringify(item.params, null, 2)));
    if (item.error) body.append(element("h3", "", text().error), element("pre", "mengbao-history-error", item.error));
    details.append(head, body);
    details.addEventListener("close", () => { details.remove(); state.detailsDialog = null; state.detail = null; });
    document.body.append(details);
    details.showModal();
  }

  function render() {
    if (state.closed) return;
    const labels = text();
    title.textContent = labels.title;
    search.placeholder = labels.search;
    search.setAttribute("aria-label", labels.search);
    order.setAttribute("aria-label", labels.newest);
    for (const option of order.children) option.textContent = labels[option.value];
    autoText.textContent = labels.auto;
    for (const [control, label] of [[refresh, "refresh"], [close, "close"], [previous, "previous"], [next, "next"]]) {
      control.title = labels[label];
      control.setAttribute("aria-label", labels[label]);
    }
    refresh.disabled = state.busy;
    previous.disabled = state.busy || state.offset === 0;
    next.disabled = state.busy || state.offset + state.items.length >= state.total;
    filters.replaceChildren();
    for (const value of ["", "running", "success", "partial", "failed"]) {
      const amount = value ? state.counts[value] || 0 : Object.values(state.counts).reduce((sum, number) => sum + number, 0);
      const button = command(`${labels[value || "all"]} ${amount}`, () => { state.filter = value; state.offset = 0; reload(); });
      button.classList.toggle("selected", state.filter === value);
      button.setAttribute("aria-pressed", String(state.filter === value));
      filters.append(button);
    }
    grid.replaceChildren();
    for (const item of state.items) {
      const card = element("article", "mengbao-history-card");
      const preview = command(`${labels.preview}: ${item.model}`, () => openDetails(item));
      preview.className = "mengbao-history-preview";
      preview.textContent = "";
      if (item.images.length) {
        const image = element("img");
        image.src = historyFileUrl(item.id, 0, { thumbnail: true });
        image.alt = item.model;
        image.loading = "lazy";
        image.addEventListener("error", () => { image.alt = labels.imageError; });
        preview.append(image);
      } else {
        const icon = element("i", `pi pi-${item.state === "running" ? "clock" : "exclamation-triangle"}`);
        icon.setAttribute("aria-hidden", "true");
        preview.append(icon);
      }
      const badge = element("span", `mengbao-history-badge ${item.state}`, `${labels[item.state]}${item.state === "running" ? ` ${item.progress}%` : ""}`);
      preview.append(badge);
      if (item.images.length) preview.append(element("span", "mengbao-history-image-count", `${item.image_count} ${labels.count}`));
      const info = element("div", "mengbao-history-info");
      const model = element("strong", "", item.model);
      model.title = item.model;
      const date = element("time", "", new Date(item.created_at).toLocaleString(language() === "zh" ? "zh-CN" : "en"));
      date.dateTime = item.created_at;
      const prompt = element("p", "", item.prompt);
      prompt.title = item.prompt;
      info.append(model, date, prompt);
      card.append(preview, info);
      grid.append(card);
    }
    if (!state.items.length) grid.append(element("div", "mengbao-history-empty", state.busy ? labels.loading : state.query || state.filter ? labels.noMatch : labels.empty));
    status.textContent = state.error || (state.busy ? labels.loading : "");
    status.classList.toggle("mengbao-history-error", Boolean(state.error));
    count.textContent = `${state.total ? state.offset + 1 : 0}–${state.offset + state.items.length} / ${state.total}`;
  }
  search.addEventListener("input", () => {
    state.query = search.value;
    state.offset = 0;
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(reload, 200);
  });
  order.addEventListener("change", () => { state.oldest = order.value === "oldest"; state.offset = 0; reload(); });
  auto.addEventListener("change", () => { state.auto = auto.checked; if (state.auto) reload(); });
  const timer = setInterval(() => { if (state.auto && !document.hidden && !state.detailsDialog?.open) reload(); }, 5000);
  dialog.addEventListener("close", () => {
    state.closed = true;
    clearInterval(timer);
    clearTimeout(state.searchTimer);
    state.detailsDialog?.close();
    dialog.remove();
    if (activeDialog === dialog) activeDialog = null;
  });
  dialog._mengBaoRefresh = () => { if (state.auto) reload(); };
  dialog._mengBaoRefreshLocale = () => {
    render();
    if (state.detail) openDetails(state.detail);
  };
  dialog.showModal();
  reload();
  return dialog;
}
function refreshHistory() { activeDialog?._mengBaoRefresh?.(); }
function refreshHistoryLocale() { activeDialog?._mengBaoRefreshLocale?.(); }

export { ensureHistoryStyles, historyFileUrl, historyLabels, historyRequest, openHistory, refreshHistory, refreshHistoryLocale };
