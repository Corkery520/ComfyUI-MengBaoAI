# ComfyUI-MengBaoAI

萌宝AI ComfyUI 综合节点套件。一次安装，集成 17 个节点：图像生成、图片反推与复刻、电商设置、智能拼图、图像约束、图片加载与保存、提示词库、素材库和历史记录。

MengBaoAI ComfyUI Node Pack: image generation and replication, e-commerce settings, prompt and material libraries, generation history, and image processing. Node labels follow the ComfyUI language setting.

[![Node pack checks](https://github.com/Corkery520/ComfyUI-MengBaoAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Corkery520/ComfyUI-MengBaoAI/actions/workflows/ci.yml)

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
| `MengBaoLoadImage` | 萌宝AI·加载图片 | 原图预览、清除选择、从素材库加载图片，输出图像与遮罩 |
| `MengBaoMaterialLibrary` | 萌宝AI·素材库 | 分类、搜索、收藏与图片导入，输出选中素材的原图与遮罩 |
| `MengBaoSaveImage` | 萌宝AI·保存图片 | 原生 PNG 保存及工作流元数据，固定图片预览及素材库、提示词库入库按钮 |
| `MengBaoPreviewImage` | 萌宝AI·预览图片 | 原生临时图片预览，固定图片预览及素材库、提示词库入库按钮 |
| `WANGPromptOrganizer` | 萌宝AI·提示词整理器 | 保存、分组、搜索、导入和导出提示词 |
| `WANGPromptReader` | 萌宝AI·提示词读取 | 在工作流中读取已保存提示词 |
| `MengBaoEcommerceSettings` | 萌宝AI·电商设置 | 组合产品信息、电商参数、提示词和结构化 JSON |
| `MengBaoImageReverse` | 萌宝AI·图片反推 | 单图元素识别、反推提示词、手动识别与缓存、主备视觉模型 |
| `MengBaoImageReplicaSettings` | 萌宝AI·图片复刻设置 | 可视化校正构图、修改文案、联动替换产品和素材，确认后生成 |
| `MengBaoReplicaAudit` | 萌宝AI·复刻检查 | 逐张检查缺字、改字与旧文案残留，检查失败仍保留成图 |
| `MengBaoSmartCollage` | 萌宝AI·智能拼图 | 默认 4 个图片端口，可添加至 20 个，自动等比无间距拼接 |
| `MengBaoImageConstraint` | 萌宝AI·图像约束 | 保持宽高比限制图片尺寸和单张 PNG 体积，默认不超过 10 MB |
| `MengBaoGlobalAPIKey` | 萌宝AI全局API Key管理 | 通过一个密钥输入框保存或清除全局 API Key |

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

## 图片复刻

连接“加载图片 → 图片反推 → 图片复刻设置”，将设置节点的“提示词”和“复刻设置”两个输出分别连接到现有“图像生成”节点的对应输入。点击“识别图片”只运行反推及必要上游，不运行下游生图；打开设置面板校正元素、替换素材及文字，点击“确认设置”后再生成。可选连接“复刻检查”核对生成图片的文案。

视觉请求共用全局 API Key，主模型为 `gem-3.7-flash`，连接失败、超时、HTTP 429/5xx 或明确模型不可用时最多切换一次 `gem-3.8-flash`。鉴权、余额、参数、安全拒绝、JSON 解析错误和取消不切换。识别缓存与草稿独立存于 ComfyUI 用户目录，源图变更必须重新识别并确认；不保证像素级复原，识别与文字仍需人工核对。主模型超时可能已经计费，备用调用可能产生额外费用。

详见 [图片复刻使用说明](docs/IMAGE_REPLICATION.md)。

## 共享悬浮工具栏

提示词库、素材库和“萌宝AI·历史记录”放在同一个可拖动的悬浮框中。历史记录展示图像生成任务的状态、进度、成图、模型与提示词，支持搜索、筛选及自动刷新；数据保存在本机用户目录。历史图片可加入素材库，失败记录不会触发重新扣费生图。

详见 [历史记录说明](docs/HISTORY.md) 和 [保存与预览图片说明](docs/IMAGE_OUTPUT.md)。

## 图片体积约束

将“萌宝AI·智能拼图”的图像输出连接到“萌宝AI·图像约束”，即可同时限制宽高和图片体积。“最大图片大小（MB）”默认为 10，设为 0 可关闭体积限制。

体积按单张 8 位 PNG 编码计算（1 MB = 1024×1024 字节），同时检查压缩级别 4 和 6。超限时等比缩小并重新编码，直到符合上限，不移除 Alpha 透明通道。批量图像按体积最大的单张统一缩小，保持批次尺寸一致。体积上限优先于最小宽高；保存节点追加的工作流元数据和其他文件格式不在该 PNG 体积保证范围内。

## 全局 API Key

“萌宝AI全局API Key管理”节点提供一个密码输入框，以及“保存全局API Key”和“清除全局API Key”按钮。密钥保存到 `ComfyUI/user/mengbaoai/.env`，不写入工作流或状态输出。

图像节点单独填写的 API Key 优先使用；留空时使用全局密钥。全局密钥保存后，使用它的图像节点会自动刷新余额。清除操作需要确认，保留其他环境配置，并阻止旧安装目录的密钥被再次迁移回来。运行管理节点只读取状态，不会隐式保存或清除密钥。

## 图片加载与素材库

“萌宝AI·加载图片”（原“萌宝图片加载”）支持点击上传、拖拽及 `Ctrl+V` 粘贴，提供并排的“清除图片”和“加载素材”按钮。预览使用完整原图，不裁剪长图；输出标准 `IMAGE` 与 `MASK`，透明图的 Alpha 会转换为遮罩。清除按钮只清空节点选择，不删除文件。

“萌宝AI·素材库”可批量导入图片，并在共享选择窗口中按分类、名称和收藏筛选、重命名、移动分类或删除素材。默认分类为角色、产品、参考、背景、字体、白底、未分类；支持自定义分类，删除分类只将图片移到未分类。单次最多导入 20 张，单张支持 PNG/JPEG/WebP/BMP、最大 32 MB 和 1 亿像素。

素材原图、缩略图与索引独立保存在 `ComfyUI/user/mengbaoai/materials/`，不会读写 AI 画板项目的素材数据。上传到图片加载节点的文件由 ComfyUI 保存在 `input/mengbao/`。工作流只保存图片路径或素材 ID，不嵌入图片数据；跨机器使用时还需一并迁移对应图片。新版内部 ID `MengBaoLoadImage` 保持不变；旧 `WANGLoadImageUploadPaste` 已取消注册，使用旧加载节点的工作流需重新添加新版并接线，其图像解码实现仅作为内部复用工具保留。

## 保存、预览与提示词入库

“萌宝AI·保存图片”和“萌宝AI·预览图片”直接复用 ComfyUI 原生保存与预览：保存节点写入 `output`，预览节点写入 `temp`，原有文件名前缀、批量图片、透明通道和 PNG 工作流元数据行为保持不变，不修改原生节点。

生成后点击“加入提示词库”，会打开现有提示词整理器，预填提示词和图片缩略图。可编辑标题、分组、文本等信息，点击“保存”才会入库。缩略图最长边为 512 像素，仅保留像素，不复制原图的工作流元数据，随提示词记录保存；即使之后清理临时预览图，库中的缩略图仍可显示。批量图片优先使用原生预览中当前选中的图片，未选择时使用第一张。

节点可从本次图片的上游萌宝图像生成节点读取原始提示词，或读取常规采样器的正向 `CLIPTextEncode` 文本，不读取负向提示词和无关参考图。多个来源时需要明确选择；第三方节点、动态拼接或提示词读取器的实际文本可连接到可选“生图提示词”输入端口，该连接优先于自动识别。无法识别时会打开空白提示词草稿，需手动补全，不会猜测内容。中英文切换和列表筛选不会改写正在编辑的图片草稿。

## 安装

### Registry / Manager 搜索安装

正式上架需要 Registry 首版发布成功并完成平台扫描；仅 GitHub 提交成功不代表已经上架。首次发布完成前，请使用下方 Git / URL 安装方式。维护者操作见 [Registry 发布指南](docs/REGISTRY_RELEASE.md)。

上架后，在支持 Comfy Registry 的 ComfyUI-Manager 中打开节点安装列表，搜索 `MengBaoAI`、`mengbaoai` 或 `萌宝AI`，选择 **MengBaoAI · 萌宝AI 综合节点套件** 安装并重启。列表未更新时刷新 Manager 的远程节点数据库，检查筛选条件是否排除了 Registry 节点。

也可在配置好 ComfyUI 路径的 Comfy CLI 中执行：

```bash
comfy node install mengbaoai
```

### Git / Manager URL 安装

Manager 提供 Git URL 安装入口的版本，可输入：

```text
https://github.com/Corkery520/ComfyUI-MengBaoAI.git
```

若该入口因安全策略被禁用，使用 Git 安装，不要为此关闭安全保护。

在 ComfyUI 的 `custom_nodes` 目录执行：

```bash
git clone https://github.com/Corkery520/ComfyUI-MengBaoAI.git
cd ComfyUI-MengBaoAI
python -m pip install -r requirements.txt
```

`python` 必须是 ComfyUI 实际使用的 Python，而不是任意系统环境；例如 Windows 便携版在节点包目录执行 `..\..\..\python_embeded\python.exe -m pip install -r requirements.txt`。Torch 和 aiohttp 由 ComfyUI 提供，不要另行替换其 CUDA 环境。

重启 ComfyUI 后，在画布节点搜索中可搜索“萌宝AI”“萌宝”“Meng”“MengBao”“MengBaoAI”或保留的历史内部名称。此搜索属于本地节点搜索，与 Manager 的公开安装列表是两个不同入口。

English: after the first Registry release becomes Active, search for **MengBaoAI** in ComfyUI-Manager or run `comfy node install mengbaoai`. Until then, install from the Git URL above. Restart ComfyUI and disable the legacy standalone plugins before loading this pack.

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
│   ├── image_tools/material_images.py
│   ├── image_tools/image_output.py
│   ├── prompt/organizer.py
│   ├── ecommerce/settings.py
│   ├── ecommerce/replica.py
│   └── tools/global_api_key.py
├── api/
│   ├── auth.py
│   ├── image_client.py
│   ├── prompt_routes.py
│   ├── material_routes.py
│   ├── history_routes.py
│   ├── replica_routes.py
│   └── vision_client.py
├── utils/
│   ├── image.py
│   ├── prompt_store.py
│   ├── material_store.py
│   ├── history_store.py
│   ├── replica.py
│   └── replica_store.py
├── web/js/
├── locales/en/nodeDefs.json
├── locales/zh/nodeDefs.json
└── tests/
```

## 开发与测试

开发约定见 [`docs/NODE_DEVELOPMENT.md`](docs/NODE_DEVELOPMENT.md)。提交前运行：

```bash
python -m unittest discover -s tests -v
python -m compileall -q __init__.py api nodes utils tests
node --test tests/*.mjs
python tests/check_registry_package.py
```

安装包检查针对 Git 已跟踪文件，新增运行文件需先暂存再执行。JavaScript 语法检查按 ES Module 执行，Bash 示例：`for file in web/js/*.js; do node --input-type=module --check < "$file"; done`。此项目没有 npm 构建或 lint 脚本。

CI 在 Windows / Python 3.10 和 Linux / Python 3.12 验证后端、前端、本地化、敏感信息与过滤后的安装包。测试环境额外安装 `aiohttp`、`tomli` 和 CPU Torch，仅用于测试，不改变用户 ComfyUI 的运行依赖。

## 安全说明

- 不要提交 `.env`、API Key、Token 或用户提示词数据。
- API Key 仅保存在 ComfyUI 用户目录。
- 创建异步图片任务时不会自动重试 POST 请求，以避免重复创建任务和重复扣费。

## License

[MIT](LICENSE)
