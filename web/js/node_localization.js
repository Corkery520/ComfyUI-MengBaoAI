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
    MengBaoEcommerceSettings: {
      title: "MengBao AI · E-commerce Settings",
      widgets: {
        product_name: "Product Name",
        copy_information: "Copy Information",
        special_requirements: "Special Requirements",
        product_size: "Product Size",
        language: "Language",
        quantity: "Quantity",
        aspect_ratio: "Aspect Ratio",
        usage: "Usage",
        page_content: "Page Content",
        font_style: "Font Style",
        reverse_pages: "Reverse Pages",
        model_setting: "Model Settings",
        model_appearance_count: "Model Appearance Count",
      },
      inputs: {},
      outputs: ["User Prompt", "Aspect Ratio", "Quantity", "Settings JSON"],
      options: {
        "中文": "Chinese",
        "英语": "English",
        "德语": "German",
        "法语": "French",
        "日语": "Japanese",
        "韩语": "Korean",
        "葡萄牙语": "Portuguese",
        "主图": "Main Images",
        "主图+详情页": "Main Images + Detail Pages",
        "详情页": "Detail Pages",
        "海报": "Poster",
        "种草图": "Social Recommendation",
        "其它": "Other",
        "精简": "Concise",
        "中等": "Standard",
        "丰富": "Rich",
        "自动判断": "Auto",
        "现代极简无衬线字体": "Modern Minimal Sans",
        "人文温柔无衬线字体": "Humanist Soft Sans",
        "高级时尚衬线字体": "Premium Fashion Serif",
        "东方雅致宋体字体": "Elegant Chinese Song",
        "新中式书法展示字体": "New Chinese Calligraphy",
        "圆润亲和字体": "Rounded Friendly",
        "潮流个性展示字体": "Trendy Display",
        "几何科技字体": "Geometric Tech",
        "自然手作字体": "Natural Handmade",
        "奢华品牌字体": "Luxury Brand",
        "复古艺术字体": "Vintage Artistic",
        "不插入": "None",
        "插入1张": "Insert 1",
        "插入2张": "Insert 2",
        "插入3张": "Insert 3",
        "不使用模特": "No Model",
        "女性模特": "Female Model",
        "男性模特": "Male Model",
      },
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
    MengBaoEcommerceSettings: {
      title: "MengBao AI电商设置",
      widgets: {
        product_name: "产品名称",
        copy_information: "文案信息",
        special_requirements: "特殊要求",
        product_size: "产品尺寸",
        language: "语言",
        quantity: "数量",
        aspect_ratio: "比例",
        usage: "用途",
        page_content: "页面内容",
        font_style: "字体风格",
        reverse_pages: "插入反转页",
        model_setting: "模特设置",
        model_appearance_count: "模特出现率",
      },
      inputs: {},
      outputs: ["用户提示词", "比例", "数量", "设置 JSON"],
      options: {
        "现代极简无衬线字体": "现代极简无衬线",
        "人文温柔无衬线字体": "人文温柔无衬线",
        "高级时尚衬线字体": "高级时尚衬线",
        "东方雅致宋体字体": "东方雅致宋体",
        "新中式书法展示字体": "新中式书法展示",
        "圆润亲和字体": "圆润亲和",
        "潮流个性展示字体": "潮流个性展示",
        "几何科技字体": "几何科技",
        "自然手作字体": "自然手作",
        "奢华品牌字体": "奢华品牌",
        "复古艺术字体": "复古艺术",
      },
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

function findWidget(node, name) {
  return (node.widgets || []).find((widget) => widget.name === name);
}

function updateEcommerceWidgetOptions(node) {
  const quantity = Math.min(
    25,
    Math.max(1, Number.parseInt(findWidget(node, "quantity")?.value, 10) || 1),
  );
  const reverseWidget = findWidget(node, "reverse_pages");
  const reverseMaximum = Math.min(3, Math.floor(quantity / 4));
  const reverseValues = [
    "自动判断",
    "不插入",
    ...Array.from({ length: reverseMaximum }, (_, index) => `插入${index + 1}张`),
  ];
  if (reverseWidget) {
    reverseWidget.options ||= {};
    reverseWidget.options.values = reverseValues;
    if (!reverseValues.includes(reverseWidget.value)) {
      reverseWidget.value = reverseMaximum > 0 ? `插入${reverseMaximum}张` : "不插入";
    }
  }

  const modelSetting = findWidget(node, "model_setting")?.value;
  const appearanceWidget = findWidget(node, "model_appearance_count");
  if (appearanceWidget) {
    appearanceWidget.options ||= {};
    appearanceWidget.options.values =
      modelSetting === "不使用模特"
        ? ["自动判断"]
        : [
            "自动判断",
            ...Array.from({ length: quantity }, (_, index) => String(index + 1)),
          ];
    if (modelSetting === "不使用模特") {
      appearanceWidget.value = "自动判断";
    } else if (
      appearanceWidget.value !== "自动判断" &&
      Number(appearanceWidget.value) > quantity
    ) {
      appearanceWidget.value = String(quantity);
    }
  }
}

function wrapEcommerceCallback(node, widget) {
  if (!widget || widget._mengBaoEcommerceCallbackWrapped) {
    return;
  }
  widget._mengBaoEcommerceCallbackWrapped = true;
  const originalCallback = widget.callback;
  widget.callback = function (...args) {
    const result = originalCallback?.apply(this, args);
    updateEcommerceWidgetOptions(node);
    node.setDirtyCanvas?.(true, true);
    return result;
  };
}

function configureEcommerceWidgets(node) {
  if (nodeClass(node) !== "MengBaoEcommerceSettings") {
    return;
  }
  wrapEcommerceCallback(node, findWidget(node, "quantity"));
  wrapEcommerceCallback(node, findWidget(node, "model_setting"));
  updateEcommerceWidgetOptions(node);
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
      configureEcommerceWidgets(this);
      return result;
    };
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      setTimeout(() => {
        applyNodeLocalization(this);
        configureEcommerceWidgets(this);
      }, 0);
      return result;
    };
  },
});

export { applyNodeLocalization, configureEcommerceWidgets, normalizeLanguage };
