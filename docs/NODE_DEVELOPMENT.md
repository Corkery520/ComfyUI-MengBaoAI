# 萌宝AI 节点开发规范

本仓库是唯一的萌宝AI ComfyUI Node Pack。所有新节点均在当前仓库开发和注册，不为单个功能新建独立 `custom_nodes` 插件。

## 稳定接口

- 已发布节点的内部 ID 不得修改。
- 历史 ID 即使包含 `WANG` 前缀也必须保留，以兼容已有工作流。
- 新节点使用稳定且唯一的英文 ID，建议格式为 `MengBao功能名称`。
- 显示名称与内部 ID 分离：中文为 `萌宝AI·功能名称`，英文为 `MengBao AI · Feature`。
- 已发布输入名、输出顺序与序列化字段不得直接更改；需要演进时提供兼容迁移。

## 目录职责

- `nodes/`：ComfyUI 节点类及模块级 mappings。
- `api/`：鉴权、外部 API 客户端和 HTTP 路由。
- `utils/`：可复用的纯工具和用户数据存储。
- `web/js/`：节点交互、上传、动态控件与本地化。
- `locales/`：中英文节点定义。
- `tests/`：后端、前端、迁移和兼容性测试。

只有两个以上节点确实复用的逻辑才放入 `api/` 或 `utils/`。不要创建没有实现的占位模块。

## 分类

一级分类固定为 `萌宝AI`，允许的分类由 `nodes/__init__.py` 集中校验：

- `萌宝AI/基础`
- `萌宝AI/图像API`
- `萌宝AI/图像处理`
- `萌宝AI/提示词`
- `萌宝AI/电商`
- `萌宝AI/视频`
- `萌宝AI/工具`

## 新增节点流程

1. 在 `nodes/` 中选择真实业务模块并实现节点类。
2. 设置 `INPUT_TYPES`、`RETURN_TYPES`、`RETURN_NAMES`、`FUNCTION`、`CATEGORY` 和 `DESCRIPTION`。
3. 在所属模块维护 `NODE_CLASS_MAPPINGS` 与 `NODE_DISPLAY_NAME_MAPPINGS`。
4. 在 `nodes/__init__.py` 聚合新模块。
5. 同步补齐 `locales/en/nodeDefs.json`、`locales/zh/nodeDefs.json` 和前端动态本地化。
6. 上传入口必须同时支持文件选择与 `Ctrl+V`；多目标按悬停或焦点路由，文本输入保持原生粘贴。
7. 新增依赖前先确认现有依赖或标准库不能解决，并更新 `requirements.txt`。
8. 先补测试，再实现功能，最后运行完整检查并重启 ComfyUI 冒烟验证。

## 标准模板

```python
class MengBaoExample:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    CATEGORY = "萌宝AI/工具"
    DESCRIPTION = "处理输入文本。"

    def run(self, text):
        return (text,)


NODE_CLASS_MAPPINGS = {"MengBaoExample": MengBaoExample}
NODE_DISPLAY_NAME_MAPPINGS = {"MengBaoExample": "萌宝AI·示例工具"}
```

## 用户数据与安全

- API Key 和提示词数据保存到 `ComfyUI/user/mengbaoai/`。
- 仓库中只保留空白默认模板，不提交用户数据。
- `.env`、API Key、Token、日志、缓存和构建产物不得提交。
- API 地址、模型映射和环境变量名集中管理，不在多个节点重复写死。
- 外部请求必须设置超时并返回清晰的原始英文错误。

## 提交前检查

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
node --test tests/*.mjs
node --check web/js/image_api.js
node --check web/js/load_image.js
node --check web/js/node_localization.js
node --check web/js/prompt_organizer.js
```

最后检查：

- `NODE_CLASS_MAPPINGS` 与 `NODE_DISPLAY_NAME_MAPPINGS` 键完全一致。
- 内部 ID 不重复，分类合法，中英文 locale 覆盖完整。
- `/object_info/{内部ID}` 中的 `python_module` 来自 `custom_nodes.ComfyUI-MengBaoAI`。
- `git status` 不包含 `.env`、API Key、用户提示词或无关文件。
