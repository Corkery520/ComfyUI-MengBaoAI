import { app } from "../../../scripts/app.js";

const NODE_LABELS = {
  en: {
    ImageGridSplit: {
      title: "MengBao AI · Image Split",
      widgets: {
        grid: "Grid",
        custom_rows: "Custom Rows",
        custom_cols: "Custom Columns",
        trim_to_even_tiles: "Trim to Even Tiles",
      },
      inputs: { image: "Image" },
      outputs: ["Tiles", "Rows", "Columns", "Tile Count"],
      options: { custom: "Custom" },
    },
    ImageFreeCrop: {
      title: "MengBao AI · Free Crop",
      widgets: { x: "X", y: "Y", width: "Width", height: "Height" },
      inputs: { image: "Image" },
      outputs: ["Cropped Image", "X", "Y", "Width", "Height"],
    },
    ImageGridTilePicker: {
      title: "MengBao AI · Grid Tile Picker",
      widgets: {
        grid: "Grid",
        custom_rows: "Custom Rows",
        custom_cols: "Custom Columns",
        row: "Row",
        column: "Column",
      },
      inputs: { image: "Image" },
      outputs: ["Tile", "Row", "Column"],
      options: { custom: "Custom" },
    },
    WANGLoadImageUploadPaste: {
      title: "MengBao AI · Load Image",
      widgets: {},
      inputs: {},
      outputs: ["Image", "Mask", "Filename", "Width", "Height"],
    },
    WANGPromptOrganizer: {
      title: "MengBao AI · Prompt Organizer",
      widgets: {
        action: "Action",
        group: "Group",
        title: "Title",
        prompt: "Prompt",
        query: "Search Query",
        tags: "Tags",
        note: "Note",
        merge_mode: "Merge Mode",
        new_group: "New Group",
        import_json: "Import JSON",
        import_path: "Import Path",
        export_path: "Export Path",
      },
      inputs: {},
      outputs: ["Selected Prompt", "Results JSON", "Titles", "Status"],
    },
    WANGPromptReader: {
      title: "MengBao AI · Prompt Reader",
      widgets: {
        group: "Group",
        title: "Title",
        fallback_prompt: "Fallback Prompt",
      },
      inputs: {},
      outputs: ["Prompt", "Status"],
    },
  },
  zh: {
    ImageGridSplit: {
      title: "萌宝AI·图片拆分",
      widgets: {
        grid: "网格",
        custom_rows: "自定义行数",
        custom_cols: "自定义列数",
        trim_to_even_tiles: "裁齐网格",
      },
      inputs: { image: "图像" },
      outputs: ["图片块", "行数", "列数", "图片块数量"],
      options: { custom: "自定义" },
    },
    ImageFreeCrop: {
      title: "萌宝AI·自由裁剪",
      widgets: { x: "X 坐标", y: "Y 坐标", width: "宽度", height: "高度" },
      inputs: { image: "图像" },
      outputs: ["裁剪图像", "X 坐标", "Y 坐标", "宽度", "高度"],
    },
    ImageGridTilePicker: {
      title: "萌宝AI·网格选图",
      widgets: {
        grid: "网格",
        custom_rows: "自定义行数",
        custom_cols: "自定义列数",
        row: "行",
        column: "列",
      },
      inputs: { image: "图像" },
      outputs: ["图片块", "行", "列"],
      options: { custom: "自定义" },
    },
    WANGLoadImageUploadPaste: {
      title: "萌宝AI·加载图片",
      widgets: {},
      inputs: {},
      outputs: ["图像", "遮罩", "文件名", "宽度", "高度"],
    },
    WANGPromptOrganizer: {
      title: "萌宝AI·提示词整理器",
      widgets: {
        action: "操作",
        group: "分组",
        title: "标题",
        prompt: "提示词",
        query: "搜索内容",
        tags: "标签",
        note: "备注",
        merge_mode: "合并方式",
        new_group: "新分组",
        import_json: "导入 JSON",
        import_path: "导入路径",
        export_path: "导出路径",
      },
      inputs: {},
      outputs: ["选中提示词", "结果 JSON", "标题列表", "状态"],
    },
    WANGPromptReader: {
      title: "萌宝AI·提示词读取",
      widgets: {
        group: "分组",
        title: "标题",
        fallback_prompt: "备用提示词",
      },
      inputs: {},
      outputs: ["提示词", "状态"],
    },
  },
};

const NODE_CLASSES = new Set(Object.keys(NODE_LABELS.en));

function normalizeLanguage(locale) {
  return String(locale || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function currentLanguage() {
  return normalizeLanguage(app.ui?.settings?.getSettingValue?.("Comfy.Locale"));
}

function nodeClass(node) {
  return node?.comfyClass || node?.type || node?.constructor?.comfyClass || "";
}

function applyNodeLocalization(node, language = currentLanguage()) {
  const labels = NODE_LABELS[normalizeLanguage(language)]?.[nodeClass(node)];
  if (!labels) {
    return;
  }

  node.title = labels.title;
  for (const widget of node.widgets || []) {
    widget.label = labels.widgets?.[widget.name] ?? widget.label ?? widget.name;
    if (labels.options && widget.options) {
      widget.options.getOptionLabel = (value) => labels.options[value] ?? value;
    }
  }
  for (const input of node.inputs || []) {
    const label = labels.inputs?.[input.name];
    if (label) {
      input.localized_name = label;
      input.label = label;
    }
  }
  for (const [index, output] of (node.outputs || []).entries()) {
    const label = labels.outputs?.[index];
    if (label) {
      output.localized_name = label;
      output.label = label;
    }
  }
  node.setDirtyCanvas?.(true, true);
}

function localizeExistingNodes() {
  const language = currentLanguage();
  for (const node of app.graph?._nodes || []) {
    applyNodeLocalization(node, language);
  }
  app.graph?.setDirtyCanvas?.(true, true);
}

function installLocaleListener() {
  const setting = app.ui?.settings?.settingsLookup?.["Comfy.Locale"];
  if (!setting || setting._mengBaoPackListenerInstalled) {
    return;
  }
  setting._mengBaoPackListenerInstalled = true;
  const originalOnChange = setting.onChange;
  setting.onChange = function (...args) {
    const result = originalOnChange?.apply(this, args);
    setTimeout(localizeExistingNodes, 0);
    return result;
  };
}

app.registerExtension({
  name: "MengBaoAI.node_localization",
  async setup() {
    installLocaleListener();
    setTimeout(localizeExistingNodes, 0);
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!NODE_CLASSES.has(nodeData.name)) {
      return;
    }
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      applyNodeLocalization(this);
      return result;
    };
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      setTimeout(() => applyNodeLocalization(this), 0);
      return result;
    };
  },
});

export { applyNodeLocalization, normalizeLanguage };
