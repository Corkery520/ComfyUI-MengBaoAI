# ComfyUI-MengBaoAI

萌宝AI ComfyUI 综合节点包。一站式集成图像生成、电商设置、智能拼图、尺寸约束、图片拆分与裁剪、图片加载、提示词管理，并为后续视频和多模态节点提供统一扩展结构。

- GitHub：<https://github.com/Corkery520/ComfyUI-MengBaoAI>
- Comfy Registry ID：`mengbaoai`
- 当前版本：`1.0.0`
- 节点分类：`萌宝AI/*`

## 已包含节点

| 内部 ID | 中文显示名 | 功能 |
| --- | --- | --- |
| `WANGImageAPI` | 萌宝AI·图像生成 | 文生图、图生图、多参考图生成、余额与 API Key 管理 |
| `ImageGridSplit` | 萌宝AI·图片拆分 | 2x2、3x3、4x4 及自定义网格拆分 |
| `ImageFreeCrop` | 萌宝AI·自由裁剪 | 按像素坐标和尺寸裁剪 |
| `ImageGridTilePicker` | 萌宝AI·网格选图 | 从网格中选择指定行列 |
| `WANGLoadImageUploadPaste` | 萌宝AI·加载图片 | 文件选择或 `Ctrl+V` 粘贴图片 |
| `WANGPromptOrganizer` | 萌宝AI·提示词整理器 | 保存、分组、搜索、导入和导出提示词 |
| `WANGPromptReader` | 萌宝AI·提示词读取 | 在工作流中读取已保存提示词 |
| `MengBaoEcommerceSettings` | MengBao AI电商设置 | 组合产品信息、电商参数、提示词和结构化 JSON |
| `MengBaoSmartCollage` | 萌宝AI智能拼图 | 一至四张图片自动纵向或 2x2 无间距拼接 |
| `MengBaoImageConstraint` | 萌宝图像约束 | 保持宽高比限制图片尺寸，必要时居中裁剪 |

带有 `WANG` 的历史内部 ID 为兼容旧工作流而保留。中英文显示名会跟随 ComfyUI 的 `Comfy.Locale` 实时切换。

## 图像模型

前端模型与实际请求模型映射如下：

| 前端模型 | API 模型 | 最大参考图 |
| --- | --- | ---: |
| `gpt-image-2` | `tt-image-2` | 14 |
| `gpt-image-2.5` | `tt-image-2.5` | 16 |
| `nano-banana-2` | `banana-2` | 14 |
| `nano-banana-2-pro` | `banana-pro` | 14 |

图像 API 使用固定服务地址 `https://api.lk888.ai`。默认模型为 `gpt-image-2`，比例与分辨率默认为自动，超时时间为 600 秒。节点支持任务进度、动态参考图、透明 PNG 提示词、余额自动刷新及 API Key 本地保存。

## 安装

### ComfyUI Registry

```bash
comfy node install mengbaoai
```

### Git 安装

在 ComfyUI 的 `custom_nodes` 目录执行：

```bash
git clone https://github.com/Corkery520/ComfyUI-MengBaoAI.git
cd ComfyUI-MengBaoAI
python -m pip install -r requirements.txt
```

重启 ComfyUI 后，可搜索“萌宝AI”“MengBao”或历史内部名称。

## 从旧插件迁移

安装总包前，请停用以下旧独立插件，避免重复节点 ID 或重复 HTTP 路由：

```text
ComfyUI-MengBao-Image-API
WANG_image_split_crop_nodes
WANG_load_image_nodes
WANG_prompt_organizer_nodes
```

首次加载时会尝试迁移旧数据。用户数据不写入 Git 仓库：

```text
ComfyUI/user/mengbaoai/.env
ComfyUI/user/mengbaoai/prompts.json
```

- API Key 从旧 Image API 安装目录的 `.env` 迁移。
- 提示词从旧 Prompt Organizer 的 `data/prompts.json` 迁移。
- 已存在的新数据不会被旧文件覆盖。
- 历史提示词接口 `/wang_prompt_organizer/*` 保持兼容。

## 上传与粘贴

- 加载图片节点支持文件选择和 `Ctrl+V` 粘贴。
- 提示词面板的预览图与 JSON 导入同时支持文件选择和 `Ctrl+V`。
- 存在多个上传目标时，仅悬停或聚焦的区域接收粘贴。
- 文本输入框继续使用系统原生文本粘贴，不会被文件上传逻辑拦截。

## 项目结构

```text
ComfyUI-MengBaoAI/
├── __init__.py
├── nodes/
│   ├── image_api/generate.py
│   ├── image_tools/split_crop.py
│   ├── image_tools/load_image.py
│   ├── image_tools/collage.py
│   ├── image_tools/constraint.py
│   ├── prompt/organizer.py
│   └── ecommerce/settings.py
├── api/
│   ├── auth.py
│   ├── image_client.py
│   └── prompt_routes.py
├── utils/
│   ├── image.py
│   └── prompt_store.py
├── web/js/
├── locales/en/nodeDefs.json
├── locales/zh/nodeDefs.json
└── tests/
```

## 开发与测试

开发约定见 [`docs/NODE_DEVELOPMENT.md`](docs/NODE_DEVELOPMENT.md)。提交前运行：

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
node --test tests/*.mjs
node --check web/js/image_api.js
node --check web/js/load_image.js
node --check web/js/node_localization.js
node --check web/js/prompt_organizer.js
```

## 安全说明

- 不要提交 `.env`、API Key、Token 或用户提示词数据。
- API Key 仅保存在 ComfyUI 用户目录。
- 创建异步图片任务时不会自动重试 POST 请求，以避免重复创建任务和重复扣费。

## License

[MIT](LICENSE)
