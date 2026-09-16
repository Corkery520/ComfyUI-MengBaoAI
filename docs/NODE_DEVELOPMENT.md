# 萌宝AI 节点开发规范

本仓库是一个统一的 ComfyUI Node Pack。所有萌宝AI节点必须在当前仓库中开发和注册，不得为单个节点创建新的 `custom_nodes` 插件目录。

## 内部 ID

- 已发布节点的内部 ID 不得修改。`WANGImageAPI` 是历史兼容 ID，必须保留。
- 新节点统一使用稳定、唯一的英文 ID：`MengBao_xxx`。
- 显示名称与内部 ID 分离，中文显示名称统一使用 `萌宝AI·功能名称`。

## 分类

一级分类固定为 `萌宝AI`，允许的标准子分类如下：

- `萌宝AI/基础`
- `萌宝AI/提示词`
- `萌宝AI/图像生成`
- `萌宝AI/图像处理`
- `萌宝AI/电商`
- `萌宝AI/视频`
- `萌宝AI/工具`

## 新增节点

1. 根据真实用途在 `nodes/` 下选择或新建子目录，例如 `nodes/image/`、`nodes/prompt/`。
2. 新建节点类，并设置 `INPUT_TYPES`、`RETURN_TYPES`、`FUNCTION` 和标准 `CATEGORY`。
3. 在所属子模块维护 `NODE_CLASS_MAPPINGS` 与 `NODE_DISPLAY_NAME_MAPPINGS`。
4. 在 `nodes/__init__.py` 汇总该子模块的 mappings。
5. 输入输出需要多语言时，同步修改 `locales/en/nodeDefs.json`、`locales/zh/nodeDefs.json` 和前端本地化脚本。
6. 新增依赖时更新 `requirements.txt`；只有多个节点真正复用时才抽离到 `api/` 或 `utils/`。
7. 运行测试与编译检查，然后重启 ComfyUI。
8. 在 `/object_info/{内部ID}` 验证内部 ID、显示名、分类和 `python_module`。

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

    def run(self, text):
        return (text,)


NODE_CLASS_MAPPINGS = {
    "MengBao_Example": MengBaoExample,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MengBao_Example": "萌宝AI·示例工具",
}
```

## 提交前检查

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q .
node --check web/MengBao_image_api_nodes_v4.js
node tests/test_frontend_localization.mjs
```

确认新内部 ID 不重复、两个 mappings 键完全对应、所有节点的一级 `CATEGORY` 都是 `萌宝AI`，并且没有提交 `.env`、API Key 或本机缓存。
