# MengBao Image API for ComfyUI

ComfyUI custom nodes for MengBao Image API. 这是一个用于在 ComfyUI 工作流中调用萌宝图像 API 的第三方自定义节点插件。

## 功能特性

- 支持文生图、图生图和多参考图生成。
- 提供 5 个 `IMAGE` 输入口，并支持图片批次；按模型最多使用 14 或 16 张参考图。
- 支持 4 个前端模型选项，并自动映射到对应 API 模型。
- 支持尺寸、比例、分辨率、质量、背景、思考等级等模型专属参数。
- `gpt-image-2.5` 支持 `opaque`、`transparent`、`auto` 背景参数。
- GPT 模型选择透明背景时会追加透明 PNG 提示词；`gpt-image-2` 上游不原生支持背景参数，透明效果不保证一定生成真实 Alpha 通道。
- 支持中文和英文界面，并跟随 ComfyUI 的 `Comfy.Locale` 设置切换。
- 提供原始响应文本、失败 URL 和错误说明图，便于排查 API 问题。
- 提供余额显示及“注册 API / 刷新余额 / 问题反馈”按钮；API Key 仅随本次余额请求使用，不写入插件文件。

## 节点列表

| 节点 ID | 显示名称 | 作用 |
| --- | --- | --- |
| `WANGImageAPI` | 中文：`萌宝图像 API` / 英文：`MengBao-Image-API` | 调用 TT Image 与 Nano Banana 系列模型生成或编辑图片 |

节点分类固定为：`MengBao/Image API`。

## 模型映射

| 前端显示 | API 实际模型 | 参考图上限 |
| --- | --- | ---: |
| `gpt-image-2` | `tt-image-2` | 14 |
| `gpt-image-2.5` | `tt-image-2.5` | 16 |
| `nano-banana-2` | `banana-2` | 14 |
| `nano-banana-2-pro` | `banana-pro` | 14 |

API 基础地址固定为 `https://api.lk888.ai`。创建任务使用 `POST /v1/media/generate`，状态查询使用 `GET /v1/media/status?task_id=...`。

## 安装

### 方法一：Git 安装

进入 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Corkery520/ComfyUI-MengBao-Image-API.git
cd ComfyUI-MengBao-Image-API
pip install -r requirements.txt
```

完全退出并重新启动 ComfyUI，然后在浏览器中执行强制刷新。

### 方法二：手动安装

下载本仓库 ZIP 并解压到：

```text
ComfyUI/custom_nodes/ComfyUI-MengBao-Image-API
```

在该目录执行 `pip install -r requirements.txt`，随后重启 ComfyUI。

## 更新

```bash
cd ComfyUI/custom_nodes/ComfyUI-MengBao-Image-API
git pull
pip install -r requirements.txt
```

更新后请重启 ComfyUI 并强制刷新浏览器缓存。

## API Key 配置

可以直接在节点的 `API Key` 输入框中填写密钥，也可以把连接 JSON 粘贴到 `Connection JSON`：

```json
{"key":"your_api_key_here"}
```

当两项同时存在时，`connection_json.key` 优先。请勿把真实 API Key 写入源码、README、工作流示例或提交到 GitHub。

API Key 可在以下页面创建：

https://corkery.ai/api/console/keys

## 基础使用流程

1. 安装插件并重启 ComfyUI。
2. 在节点菜单的 `MengBao/Image API` 分类中添加节点。
3. 填写 API Key 或连接 JSON。
4. 选择模型并设置该模型对应的参数。
5. 输入提示词；图生图或多图参考时连接一个或多个参考图。
6. 连接 `Images` 输出到预览或保存图像节点，然后执行工作流。

## 输出

- `Images`：生成结果图片批次；没有收到图片时返回错误说明图。
- `Response`：API 创建任务、状态或错误的原始 JSON 文本。
- `Failed URLs`：下载失败的结果图片 URL。

## 超时与重试

- `timeout`：整个任务允许等待的最长秒数，默认 300 秒。
- `retries`：状态查询和结果图片下载的重试次数。
- 创建任务不会自动重试，避免服务端已经接收任务后重复提交和计费。

如果任务超时，`Response` 会尽量保留 `task_id`。建议先使用该 ID 查询原任务，不要立即重复生成。

## 项目结构

```text
ComfyUI-MengBao-Image-API/
├── __init__.py
├── MengBao_image_api_nodes.py
├── web/
│   └── MengBao_image_api_nodes_v4.js
├── locales/
│   ├── en/nodeDefs.json
│   └── zh/nodeDefs.json
├── tests/
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

## 常见问题

### 安装后找不到节点

确认插件目录位于 `ComfyUI/custom_nodes/`，检查 ComfyUI 启动终端是否有 Python 导入错误，然后完全重启 ComfyUI 并强制刷新浏览器。

### 依赖安装失败

请使用 ComfyUI 实际运行的 Python 环境执行 `pip install -r requirements.txt`。便携版 ComfyUI 通常需要使用其自带的 Python 解释器。

### API 请求失败

检查 API Key、网络连接和账户状态，并查看节点的 `Response` 输出。HTTP 状态码和 API 原始英文错误会保留，便于搜索和反馈。

### ComfyUI 更新后节点异常

先执行 `git pull` 更新插件并重启 ComfyUI。如果问题仍然存在，请保留启动日志、节点 `Response` 输出和复现步骤。

## License

本项目使用 [MIT License](LICENSE)。

## Disclaimer

本项目是 ComfyUI 第三方自定义节点扩展，与 ComfyUI 官方项目无隶属关系。ComfyUI 及相关商标归其原作者或权利人所有。用户应自行确保 API 使用行为符合对应服务条款及当地法律法规，并自行承担生成内容与 API 费用相关责任。
