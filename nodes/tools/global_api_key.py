from ...api.auth import read_saved_api_key


class MengBaoGlobalAPIKey:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"api_key": ("STRING", {"default": "", "multiline": False})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "get_status"
    OUTPUT_NODE = True
    CATEGORY = "萌宝AI/工具"
    DESCRIPTION = "统一保存或清除萌宝AI节点使用的全局API Key。"
    SEARCH_ALIASES = [
        "Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoGlobalAPIKey",
        "Global API Key", "API Key Manager", "萌宝", "萌宝AI", "萌宝全局API Key管理",
        "全局密钥", "密钥管理", "API密钥", "全局API Key",
    ]

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def get_status(self, api_key=""):
        # 执行工作流只读取状态，保存或清除必须由用户主动点击对应按钮。
        saved = bool(read_saved_api_key())
        status = "Global API Key saved" if saved else "Global API Key not set"
        return {"ui": {"saved": [saved]}, "result": (status,)}
