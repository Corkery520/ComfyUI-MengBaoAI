import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { ensureHistoryStyles, openHistory, refreshHistory, refreshHistoryLocale } from "./history.js";
import { openMaterialLibrary, refreshMaterialDialogLocale } from "./material_library.js";

const TEXT = {
  zh: { prompts: "萌宝AI·提示词库", history: "萌宝AI·历史记录", materials: "萌宝AI·素材库", dock: "萌宝AI工具库" },
  en: { prompts: "MengBao AI · Prompt Library", history: "MengBao AI · History", materials: "MengBao AI · Material Library", dock: "MengBao AI Libraries" },
};
let activeModal = null;
let activeKind = "";
function currentLanguage() {
  return String(app.ui?.settings?.getSettingValue?.("Comfy.Locale") || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}
function openMaterials() {
  return openMaterialLibrary({ language: currentLanguage, onSelect: (item) => {
    const node = globalThis.LiteGraph?.createNode("MengBaoLoadImage");
    if (!node) throw new Error("MengBaoLoadImage node is not available; reload ComfyUI");
    const canvas = app.canvas;
    node.pos = canvas?.ds ? [120 / canvas.ds.scale - canvas.ds.offset[0], 100 / canvas.ds.scale - canvas.ds.offset[1]] : [100, 100];
    app.graph.add(node);
    const widget = node.widgets?.find(({ name }) => name === "image");
    if (widget) widget.value = `mengbao-material:${item.id}`;
    node.onConfigure?.({});
    app.graph.setDirtyCanvas(true, true);
  } });
}
function launchLibrary(kind) {
  const dock = document.getElementById("mengbao-library-dock");
  if (activeModal?.open && activeKind === kind) { activeModal.focus(); return; }
  if (activeModal?.open) {
    document.body.append(dock);
    activeModal.close();
  }
  let dialog;
  if (kind === "prompts") {
    if (!document.getElementById("wang-prompt-panel")) window.MengBaoPromptOrganizerOpen?.();
  } else {
    dialog = kind === "history" ? openHistory({ language: currentLanguage }) : openMaterials();
  }
  activeModal = dialog || null;
  activeKind = kind;
  if (dialog) {
    // 原生模态框会使外部控件失效，将工具框放进当前面板，保持三个入口可以直接切换。
    dialog.append(dock);
    dialog.addEventListener("close", () => {
      if (dock.parentElement === dialog) document.body.append(dock);
      if (activeModal === dialog) activeModal = null;
    });
  }
}
function ensureLibraryLaunchers() {
  ensureHistoryStyles();
  let dock = document.getElementById("mengbao-library-dock");
  if (!dock) {
    dock = document.createElement("div");
    dock.id = "mengbao-library-dock";
    dock.className = "mengbao-library-dock";
    dock.setAttribute("role", "toolbar");
    document.body.append(dock);
  }
  dock.setAttribute("aria-label", TEXT[currentLanguage()].dock);
  document.getElementById("wang-prompt-fab")?.remove();
  for (const [kind, icon] of [["prompts", "book"], ["materials", "images"], ["history", "history"]]) {
    const id = `mengbao-${kind}-fab`;
    let button = document.getElementById(id);
    if (!button) {
      button = document.createElement("button");
      button.id = id;
      button.type = "button";
      button.className = `mengbao-library-fab ${kind}`;
      const symbol = document.createElement("i");
      symbol.className = `pi pi-${icon}`;
      symbol.setAttribute("aria-hidden", "true");
      button.append(symbol);
      button.addEventListener("click", () => launchLibrary(kind));
      dock.append(button);
    }
    button.title = TEXT[currentLanguage()][kind];
    button.setAttribute("aria-label", button.title);
  }
}
app.registerExtension({
  name: "MengBaoAI.library_launchers",
  async setup() {
    ensureLibraryLaunchers();
    api.addEventListener?.("executed", (event) => {
      if (event.detail?.output?.mengbao_balance_refresh) refreshHistory();
    });
    const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
    if (!setting || setting._mengBaoLibraryLocaleInstalled) return;
    setting._mengBaoLibraryLocaleInstalled = true;
    const original = setting.onChange;
    setting.onChange = function (...args) {
      const result = original?.apply(this, args);
      setTimeout(() => { ensureLibraryLaunchers(); refreshHistoryLocale(); refreshMaterialDialogLocale(); }, 0);
      return result;
    };
  },
});

export { currentLanguage, ensureLibraryLaunchers, launchLibrary, openMaterials };
