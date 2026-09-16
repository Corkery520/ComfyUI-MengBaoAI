import sys
from copy import deepcopy


def _native_type(preview=False, required=True):
    name = "PreviewImage" if preview else "SaveImage"
    native = getattr(sys.modules.get("nodes"), name, None)
    if native is None and required:
        raise RuntimeError(f"ComfyUI native {name} is unavailable")
    return native


def _linked_node(value):
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], (str, int)) and type(value[1]) is int:
        return str(value[0])
    return None


def _text_value(value, graph, visited=None):
    if isinstance(value, str):
        return value if value.strip() else ""
    node_id = _linked_node(value)
    visited = set() if visited is None else visited
    if node_id is None or node_id in visited or len(visited) >= 64 or value[1] != 0:
        return ""
    visited.add(node_id)
    node = graph.get(node_id, {})
    inputs = node.get("inputs", {})
    if node.get("class_type") == "CLIPTextEncode":
        return _text_value(inputs.get("text"), graph, visited)
    if node.get("class_type") == "WANGPromptOrganizer" and inputs.get("action") == "save_or_update":
        return _text_value(inputs.get("prompt"), graph, visited)
    return ""


def _positive_candidates(graph, connection):
    pending = [_linked_node(connection)]
    visited = set()
    candidates = []
    while pending and len(visited) < 1024:
        node_id = pending.pop()
        if node_id is None or node_id in visited:
            continue
        visited.add(node_id)
        node = graph.get(node_id, {})
        inputs = node.get("inputs", {})
        if node.get("class_type") == "CLIPTextEncode":
            text = _text_value(inputs.get("text"), graph)
            if text:
                candidates.append({"node_id": node_id, "class_type": "CLIPTextEncode", "text": text})
            continue
        pending.extend(_linked_node(value) for name, value in inputs.items() if name != "negative")
    return candidates


def _prompt_candidates(graph, unique_id, explicit_prompt=""):
    if isinstance(explicit_prompt, str) and explicit_prompt.strip():
        return [{"node_id": str(unique_id or ""), "class_type": "explicit", "text": explicit_prompt}]
    if not isinstance(graph, dict):
        return []
    owner = graph.get(str(unique_id), {})
    pending = [_linked_node(owner.get("inputs", {}).get("images"))]
    visited = set()
    candidates = []
    while pending and len(visited) < 1024:
        node_id = pending.pop()
        if node_id is None or node_id in visited:
            continue
        visited.add(node_id)
        node = graph.get(node_id, {})
        inputs = node.get("inputs", {})
        if node.get("class_type") == "WANGImageAPI":
            text = _text_value(inputs.get("prompt"), graph)
            if text:
                candidates.append({"node_id": node_id, "class_type": "WANGImageAPI", "text": text})
            # 找到生图节点后停止回溯，不把参考图的旧提示词当成本次提示词。
            continue
        if node.get("class_type") in {"KSampler", "KSamplerAdvanced", "SamplerCustom"}:
            candidates.extend(_positive_candidates(graph, inputs.get("positive")))
            continue
        pending.extend(_linked_node(value) for name, value in inputs.items() if name not in {"negative", "api_key", "connection_json"})
    unique = {}
    for candidate in reversed(candidates):
        unique.setdefault(candidate["text"], candidate)
    return list(unique.values())


class MengBaoSaveImage:
    PREVIEW = False

    @classmethod
    def INPUT_TYPES(cls):
        native = _native_type(cls.PREVIEW, required=False)
        if native is not None:
            schema = deepcopy(native.INPUT_TYPES())
        else:
            schema = {"required": {"images": ("IMAGE",)}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}
            if not cls.PREVIEW:
                schema["required"]["filename_prefix"] = ("STRING", {"default": "ComfyUI"})
        schema.setdefault("optional", {})["generation_prompt"] = ("STRING", {"default": "", "forceInput": True})
        schema.setdefault("hidden", {})["unique_id"] = "UNIQUE_ID"
        return schema

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "使用 ComfyUI 原生保存图像功能，可将生图提示词和图片缩略图加入提示词库。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoSaveImage", "MengBao Save Image", "萌宝", "萌宝AI", "萌宝AI保存图像", "萌宝AI·保存图片", "保存图片", "保存图像", "Save Image"]

    def save_images(self, images, filename_prefix="ComfyUI", generation_prompt="", prompt=None, extra_pnginfo=None, unique_id=None):
        native = _native_type(self.PREVIEW)()
        kwargs = {"images": images, "prompt": prompt, "extra_pnginfo": extra_pnginfo}
        if not self.PREVIEW:
            kwargs["filename_prefix"] = filename_prefix
        result = native.save_images(**kwargs)
        result = dict(result)
        result["ui"] = dict(result.get("ui", {}))
        # UI 仅传递必要的提示词，不传整张执行图，避免额外暴露密钥和连接配置。
        result["ui"]["mengbao_prompt_candidates"] = _prompt_candidates(prompt, unique_id, generation_prompt)
        return result


class MengBaoPreviewImage(MengBaoSaveImage):
    PREVIEW = True
    DESCRIPTION = "使用 ComfyUI 原生预览图像功能，可将生图提示词和图片缩略图加入提示词库。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoPreviewImage", "MengBao Preview Image", "萌宝", "萌宝AI", "萌宝AI预览图像", "萌宝AI·预览图片", "预览图片", "预览图像", "Preview Image"]
