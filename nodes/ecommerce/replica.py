import json

import torch

from ...api.vision_client import run_vision
from ...utils.image import image_tensor_to_png_bytes
from ...utils.replica import ANALYSIS_PROMPT, PROMPT_VERSION, audit_prompt, compile_settings, parse_analysis, parse_audit
from ...utils.replica_store import REPLICA_STORE, identity


def interrupted():
    try:
        from comfy.model_management import processing_interrupted
        return processing_interrupted()
    except ImportError:
        return False


def status(node_id, detail):
    if node_id is None:
        return
    try:
        from server import PromptServer
        if getattr(PromptServer, "instance", None):
            PromptServer.instance.send_sync("mengbao_replica_status", {"node_id": str(node_id), **detail})
    except ImportError:
        pass


class MengBaoImageReverse:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",), "request_id": ("STRING", {"default": ""})}, "hidden": {"unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("MENGBAO_REPLICA_ANALYSIS", "STRING")
    RETURN_NAMES = ("analysis", "reverse_prompt")
    FUNCTION = "analyze"
    OUTPUT_NODE = True
    CATEGORY = "萌宝AI/电商"
    DESCRIPTION = "识别图片构图与可替换元素；使用 GEM 3.7 flash，连接失败切换 GEM 3.8 flash。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoImageReverse", "萌宝", "萌宝AI", "萌宝AI·图片反推", "图片反推", "图片复刻", "Image Reverse", "Image Replication", "MengBao AI · Image Reverse"]

    def analyze(self, image, request_id, unique_id=None):
        if not request_id:
            raise ValueError("Click Analyze Image in the Image Reverse node first")
        identity(request_id)
        if not isinstance(image, torch.Tensor) or image.dim() != 4 or image.shape[0] != 1:
            raise ValueError("Image Reverse requires exactly one IMAGE, not an image batch")
        source = REPLICA_STORE.put_asset(image_tensor_to_png_bytes(image), "source.png")
        fingerprint = f"analysis:{source['id']}:{PROMPT_VERSION}"
        record = REPLICA_STORE.begin(request_id, fingerprint)
        if record is None:
            try:
                result = run_vision(ANALYSIS_PROMPT, [REPLICA_STORE.asset_bytes(source["id"])], parse_analysis,
                                    on_stage=lambda event: status(unique_id, {**event, "request_id": request_id}), cancelled=interrupted)
                record = {"id": request_id, "source": source, "analysis": result["data"], "model": result["model"], "attempts": result["attempts"]}
                REPLICA_STORE.complete(request_id, record)
            except BaseException as exc:
                REPLICA_STORE.fail(request_id, str(exc) or "Vision request interrupted")
                raise
        prompt = "\n\n".join([record["analysis"]["composition"], *[
            f"{element['name']}: {element['description']}\n{element['text']}\n{element['textStyle']}" for element in record["analysis"]["elements"]]])
        status(unique_id, {"stage": "completed", "model": record["model"]})
        return {"ui": {"mengbao_replica_analysis": [record]}, "result": (record, prompt)}


class MengBaoImageReplicaSettings:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"analysis": ("MENGBAO_REPLICA_ANALYSIS",), "draft_json": ("STRING", {"default": ""}), "draft_id": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING", "MENGBAO_REPLICA_SETTINGS")
    RETURN_NAMES = ("prompt", "replica_settings")
    FUNCTION = "build"
    CATEGORY = "萌宝AI/电商"
    DESCRIPTION = "可视化校正图片元素、修改文字、替换素材，确认后连接萌宝AI·图像生成。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoImageReplicaSettings", "萌宝", "萌宝AI", "萌宝AI·图片复刻设置", "复刻设置", "图片复刻", "元素替换", "Replica Settings", "MengBao AI · Replica Settings"]

    def build(self, analysis, draft_json, draft_id):
        settings = compile_settings(analysis, draft_json, REPLICA_STORE)
        REPLICA_STORE.save_draft(draft_id, json.loads(draft_json))
        return settings["prompt"], settings


class MengBaoReplicaAudit:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "replica_settings": ("MENGBAO_REPLICA_SETTINGS",)}, "hidden": {"unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "report")
    FUNCTION = "audit"
    OUTPUT_NODE = True
    CATEGORY = "萌宝AI/电商"
    DESCRIPTION = "检查复刻成图缺字、改字和旧文案残留；检查失败仍保留生成图片。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoReplicaAudit", "萌宝", "萌宝AI", "萌宝AI·复刻检查", "复刻检查", "文字检查", "Replica Audit", "MengBao AI · Replica Audit"]

    def audit(self, images, replica_settings, unique_id=None):
        reports = []
        for index, image in enumerate(images):
            if interrupted():
                reports.append({"image": index + 1, "error": "Vision request cancelled"})
                break
            try:
                result = run_vision(audit_prompt(replica_settings), [image_tensor_to_png_bytes(image)], parse_audit, max_tokens=3000,
                                    on_stage=lambda event: status(unique_id, {**event, "image": index + 1}), cancelled=interrupted)
                reports.append({"image": index + 1, "model": result["model"], "attempts": result["attempts"], **result["data"]})
            except Exception as exc:
                reports.append({"image": index + 1, "error": str(exc)})
        report = json.dumps(reports, ensure_ascii=False, indent=2)
        return {"ui": {"mengbao_replica_report": [report]}, "result": (images, report)}
