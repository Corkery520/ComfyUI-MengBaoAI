import { api } from "../../../scripts/api.js";
import { bindUploadTarget } from "./material_uploads.js";

const BASE = "/mengbao_materials";
const TEXT = {
  en: {
    title: "MengBao Material Library", search: "Search name or category", all: "All Categories",
    favorites: "Favorites", import: "Import Images", refresh: "Refresh", addCategory: "New Category",
    renameCategory: "Rename Category", deleteCategory: "Delete Category", rename: "Rename", remove: "Delete",
    choose: "Load Selected Material", close: "Close", empty: "No matching materials", loading: "Loading...",
    hint: "Click to upload or press Ctrl+V to paste images. Multiple selection supported.",
    categoryPrompt: "Category name", namePrompt: "Material name", deletePrompt: "Delete this material from the library?",
    deleteCategoryPrompt: "Delete this category? Its images will be moved to Uncategorized.",
    imported: "Imported", dimensions: "pixels", favorite: "Favorite", unfavorite: "Remove Favorite",
  },
  zh: {
    title: "萌宝AI·素材库", search: "搜索素材名称或分类", all: "全部分类", favorites: "收藏",
    import: "导入图片", refresh: "刷新", addCategory: "新建分类", renameCategory: "重命名分类",
    deleteCategory: "删除分类", rename: "重命名", remove: "删除", choose: "加载选中素材", close: "关闭",
    empty: "暂无匹配素材", loading: "正在加载…", hint: "点击上传或 Ctrl+V 粘贴图片，支持一次多选",
    categoryPrompt: "分类名称", namePrompt: "素材名称", deletePrompt: "确定从素材库中删除这张图片吗？",
    deleteCategoryPrompt: "确定删除这个分类吗？其中的图片会移动到“未分类”。",
    imported: "已导入", dimensions: "像素", favorite: "收藏", unfavorite: "取消收藏",
  },
};
const CATEGORY_LABELS = { "角色": "Characters", "产品": "Products", "参考": "References", "背景": "Backgrounds", "字体": "Typography", "白底": "White Background", "未分类": "Uncategorized" };
let activeDialog = null;

function materialLabels(language) { return TEXT[language === "zh" ? "zh" : "en"]; }
function categoryLabel(category, language) { return language === "zh" ? category : CATEGORY_LABELS[category] || category; }
function materialFileUrl(id, thumbnail = false) { return `${BASE}/file/${encodeURIComponent(id)}${thumbnail ? "?thumbnail=1" : ""}`; }

function ensureMaterialStyles() {
  if (document.getElementById("mengbao-material-styles")) return;
  const link = document.createElement("link");
  link.id = "mengbao-material-styles";
  link.rel = "stylesheet";
  link.href = new URL("./materials.css", import.meta.url).href;
  document.head.append(link);
}

async function materialRequest(path, options = {}) {
  const response = await api.fetchApi(`${BASE}${path}`, options);
  const raw = await response.text();
  let payload;
  try { payload = JSON.parse(raw); } catch { throw new Error(raw || `HTTP ${response.status}`); }
  if (!response.ok || payload?.error) throw new Error(payload?.error?.message || `HTTP ${response.status}`);
  return payload;
}

function jsonRequest(path, body) {
  return materialRequest(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

async function importMaterial(file, category = "未分类") {
  const body = new FormData();
  body.append("category", category);
  body.append("image", file, file.name || "clipboard_image.png");
  return materialRequest("/import", { method: "POST", body });
}

function getMaterial(id) { return materialRequest(`/item/${encodeURIComponent(id)}`); }
function isMaterialDialogOpen() { return Boolean(activeDialog?.open); }

function openMaterialLibrary({ language, onSelect, selectedId = "" }) {
  activeDialog?.close();
  ensureMaterialStyles();
  const dialog = document.createElement("dialog");
  dialog.className = "mengbao-material-dialog";
  const state = { items: [], categories: [], category: "", query: "", favorites: false, selectedId, busy: false, error: "", closed: false };
  const text = () => materialLabels(language());
  const element = (tag, className = "") => {
    const result = document.createElement(tag);
    result.className = className;
    return result;
  };
  const button = (handler, className = "") => {
    const result = element("button", className);
    result.type = "button";
    result.addEventListener("click", handler);
    return result;
  };
  const header = element("header");
  const title = element("h2");
  const close = button(() => dialog.close(), "mengbao-material-close");
  close.textContent = "×";
  header.append(title, close);
  const toolbar = element("div", "mengbao-material-toolbar");
  const search = element("input");
  search.type = "search";
  const categories = element("select");
  const favoriteLabel = element("label", "mengbao-material-favorites");
  const favorites = element("input");
  favorites.type = "checkbox";
  const favoriteText = element("span");
  favoriteLabel.append(favorites, favoriteText);
  toolbar.append(search, categories, favoriteLabel);
  const actions = element("div", "mengbao-material-actions");
  const importButton = button(() => uploadBinding.chooseFiles(), "mengbao-primary");
  const refresh = button(() => run(async () => {}));
  const addCategory = button(() => {
    const name = window.prompt(text().categoryPrompt);
    if (name?.trim()) run(() => jsonRequest("/category", { action: "add", name })).then(() => { if (!state.error) state.category = name.trim(); render(); });
  });
  const renameCategory = button(() => {
    const name = window.prompt(text().categoryPrompt, state.category);
    if (name?.trim()) run(() => jsonRequest("/category", { action: "rename", current: state.category, name })).then(() => { if (!state.error) state.category = name.trim(); render(); });
  });
  const deleteCategory = button(() => {
    if (window.confirm(text().deleteCategoryPrompt)) run(() => jsonRequest("/category", { action: "delete", name: state.category }));
  });
  actions.append(importButton, refresh, addCategory, renameCategory, deleteCategory);
  const uploadZone = element("div", "mengbao-material-import-zone");
  uploadZone.tabIndex = 0;
  uploadZone.setAttribute("role", "button");
  uploadZone.addEventListener("click", () => uploadBinding.chooseFiles());
  uploadZone.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); uploadBinding.chooseFiles(); } });
  const grid = element("div", "mengbao-material-grid");
  const status = element("div", "mengbao-material-status");
  status.setAttribute("role", "status");
  const footer = element("footer");
  const count = element("span");
  const choose = button(async () => {
    if (!state.selectedId || state.busy) return;
    state.busy = true;
    render();
    try { await onSelect(await getMaterial(state.selectedId)); dialog.close(); }
    catch (error) { state.error = error.message; }
    finally { state.busy = false; if (!state.closed) render(); }
  }, "mengbao-primary");
  footer.append(count, choose);
  dialog.append(header, toolbar, actions, uploadZone, grid, status, footer);
  document.body.append(dialog);
  activeDialog = dialog;
  const uploadBinding = bindUploadTarget(uploadZone, {
    maxFiles: 20, available: () => dialog.open && !state.busy,
    upload: (files) => run(async () => {
      const category = state.category || "未分类";
      for (const file of files) {
        const item = await importMaterial(file, category);
        state.selectedId = item.id;
      }
    }),
    onError: (error) => { state.error = error.message; render(); },
  });
  dialog.addEventListener("close", () => {
    state.closed = true;
    uploadBinding.dispose();
    dialog.remove();
    if (activeDialog === dialog) activeDialog = null;
  });
  search.addEventListener("input", () => { state.query = search.value; renderGrid(); });
  categories.addEventListener("change", () => { state.category = categories.value; render(); });
  favorites.addEventListener("change", () => { state.favorites = favorites.checked; renderGrid(); });

  async function reload() {
    const payload = await materialRequest("/items");
    if (state.closed) return;
    state.items = payload.items;
    state.categories = payload.categories;
    if (!state.categories.includes(state.category)) state.category = "";
    if (!state.items.some(({ id }) => id === state.selectedId)) state.selectedId = "";
  }

  async function run(action) {
    if (state.busy || state.closed) return;
    state.busy = true;
    state.error = "";
    render();
    try { await action(); } catch (error) { state.error = error.message; }
    try { await reload(); } catch (error) { state.error ||= error.message; }
    finally { state.busy = false; if (!state.closed) render(); }
  }

  function categoryOptions(select, value, includeAll = false) {
    select.replaceChildren();
    for (const category of [...(includeAll ? [""] : []), ...state.categories]) {
      const option = element("option");
      option.value = category;
      option.textContent = category ? categoryLabel(category, language()) : text().all;
      select.append(option);
    }
    select.value = value;
  }

  function renderGrid() {
    if (state.closed) return;
    const query = state.query.trim().toLocaleLowerCase();
    const items = state.items.filter((item) => (!state.category || item.category === state.category)
      && (!state.favorites || item.favorite) && (!query || `${item.name} ${item.category} ${categoryLabel(item.category, language())}`.toLocaleLowerCase().includes(query)));
    grid.replaceChildren();
    for (const item of items) {
      const card = element("article", `mengbao-material-card${state.selectedId === item.id ? " selected" : ""}`);
      const preview = button(() => { state.selectedId = item.id; render(); }, "mengbao-material-preview");
      preview.disabled = state.busy;
      preview.setAttribute("aria-label", item.name);
      const image = element("img");
      image.src = materialFileUrl(item.id, true);
      image.alt = item.name;
      image.loading = "lazy";
      preview.append(image);
      const name = element("div", "mengbao-material-name");
      name.textContent = item.name;
      name.title = item.name;
      const dimensions = element("div", "mengbao-material-dimensions");
      dimensions.textContent = `${item.width} × ${item.height}`;
      const controls = element("div", "mengbao-material-card-controls");
      const star = button(() => run(() => jsonRequest(`/item/${item.id}`, { favorite: !item.favorite })), "mengbao-material-star");
      star.textContent = item.favorite ? "★" : "☆";
      star.title = item.favorite ? text().unfavorite : text().favorite;
      star.setAttribute("aria-label", star.title);
      const rename = button(() => {
        const name = window.prompt(text().namePrompt, item.name);
        if (name?.trim()) run(() => jsonRequest(`/item/${item.id}`, { name }));
      });
      rename.textContent = text().rename;
      const remove = button(() => {
        if (window.confirm(text().deletePrompt)) run(() => materialRequest(`/item/${item.id}`, { method: "DELETE" }));
      });
      remove.textContent = text().remove;
      controls.append(star, rename, remove);
      const category = element("select", "mengbao-material-card-category");
      category.setAttribute("aria-label", text().categoryPrompt);
      categoryOptions(category, item.category);
      category.addEventListener("change", () => run(() => jsonRequest(`/item/${item.id}`, { category: category.value })));
      for (const control of [star, rename, remove, category]) control.disabled = state.busy;
      card.append(preview, name, dimensions, controls, category);
      grid.append(card);
    }
    if (!items.length) {
      const empty = element("div", "mengbao-material-empty");
      empty.textContent = state.busy ? text().loading : text().empty;
      grid.append(empty);
    }
    count.textContent = `${items.length} / ${state.items.length}`;
    choose.disabled = state.busy || !items.some(({ id }) => id === state.selectedId);
  }

  function render() {
    if (state.closed) return;
    title.textContent = text().title;
    close.title = text().close;
    close.setAttribute("aria-label", text().close);
    search.placeholder = text().search;
    search.setAttribute("aria-label", text().search);
    favoriteText.textContent = text().favorites;
    for (const [control, label] of [[importButton, "import"], [refresh, "refresh"], [addCategory, "addCategory"], [renameCategory, "renameCategory"], [deleteCategory, "deleteCategory"], [choose, "choose"]]) control.textContent = text()[label];
    for (const control of [categories, favorites, importButton, refresh, addCategory]) control.disabled = state.busy;
    const lockedCategory = !state.category || state.category === "未分类";
    renameCategory.disabled = state.busy || lockedCategory;
    deleteCategory.disabled = state.busy || lockedCategory;
    uploadZone.textContent = text().hint;
    uploadZone.setAttribute("aria-label", text().hint);
    uploadZone.setAttribute("aria-disabled", String(state.busy));
    status.textContent = state.error || (state.busy ? text().loading : "");
    status.classList.toggle("error", Boolean(state.error));
    categoryOptions(categories, state.category, true);
    renderGrid();
  }
  dialog._mengBaoRefreshLocale = render;
  dialog.showModal();
  run(async () => {});
  return dialog;
}

function refreshMaterialDialogLocale() { activeDialog?._mengBaoRefreshLocale?.(); }

export { ensureMaterialStyles, getMaterial, importMaterial, isMaterialDialogOpen, materialFileUrl, materialLabels, openMaterialLibrary, refreshMaterialDialogLocale };
