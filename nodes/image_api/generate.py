from typing import Any, Dict, List, Optional

import torch

from ...api import image_client
from ...api.auth import (
    connection_key as _connection_key,
    mask_key as _mask_key,
    provided_connection_key as _provided_connection_key,
    read_saved_api_key as _read_saved_api_key,
    save_api_key as _save_api_key,
)
from ...api.image_client import (
    FIXED_API_BASE,
    MODEL_CONFIGS,
    MODEL_TYPES,
    call_media_api as _call_media_api,
    collect_image_sources as _collect_image_sources,
    extract_images as _extract_images,
    extract_task_id as _extract_task_id,
    fetch_balance as _fetch_balance,
    task_progress_percent as _task_progress_percent,
)
from ...utils.image import (
    _message_image_title,
    cat_images as _cat_images,
    image_tensor_to_png_bytes as _image_tensor_to_png_bytes,
    json_text as _json_text,
    normalize_ui_language as _normalize_ui_language,
    optional_images as _optional_images,
    png_bytes_to_image_tensor as _png_bytes_to_image_tensor,
)

try:
    from comfy.utils import ProgressBar as ComfyProgressBar
except ImportError:
    ComfyProgressBar = None


# 保留这些模块级名称，兼容现有测试与外部调试脚本。
requests = image_client.requests
DEFAULT_REFERENCE_IMAGE_COUNT = 3
NAMED_REFERENCE_IMAGE_COUNT = 5
MAX_REFERENCE_IMAGE_COUNT = max(
    int(config["max_images"]) for config in MODEL_CONFIGS.values()
)

DEFAULT_PROMPTS = {
    "en": "Generate a cinematic image",
    "zh": "生成一张电影感图片",
}
TRANSPARENT_BACKGROUND_PROMPTS = {
    "en": (
        "Precisely isolate the current image subject and remove only the background "
        "outside the subject. Output a transparent PNG with a real Alpha channel. "
        "Do not draw a checkerboard, mosaic, white background, or any other "
        "simulated transparency."
    ),
    "zh": (
        "精确提取当前图片主体，仅移除主体外背景，输出带真实 Alpha 通道的透明 PNG。"
        "禁止绘制棋盘格、马赛克、白底或其他模拟透明背景。"
    ),
}

TT_IMAGE_2_SIZES = {
    "auto": "auto",
    "1K 1:1 1024x1024": "1024x1024",
    "1K 2:3 1024x1536": "1024x1536",
    "1K 3:2 1536x1024": "1536x1024",
    "1K 3:4 960x1280": "960x1280",
    "1K 4:3 1280x960": "1280x960",
    "1K 9:16 1088x1920": "1088x1920",
    "1K 16:9 1920x1088": "1920x1088",
    "1K 4:5 1024x1280": "1024x1280",
    "1K 5:4 1280x1024": "1280x1024",
    "1K 1:2 960x1920": "960x1920",
    "1K 2:1 1920x960": "1920x960",
    "2K 1:1 2048x2048": "2048x2048",
    "2K 2:3 2048x3072": "2048x3072",
    "2K 3:2 3072x2048": "3072x2048",
    "2K 3:4 1920x2560": "1920x2560",
    "2K 4:3 2560x1920": "2560x1920",
    "2K 9:16 1440x2560": "1440x2560",
    "2K 16:9 2560x1440": "2560x1440",
    "2K 4:5 2048x2560": "2048x2560",
    "2K 5:4 2560x2048": "2560x2048",
    "2K 1:2 1280x2560": "1280x2560",
    "2K 2:1 2560x1280": "2560x1280",
    "4K 1:1 2880x2880": "2880x2880",
    "4K 2:3 2304x3456": "2304x3456",
    "4K 3:2 3456x2304": "3456x2304",
    "4K 3:4 2400x3200": "2400x3200",
    "4K 4:3 3200x2400": "3200x2400",
    "4K 9:16 2160x3840": "2160x3840",
    "4K 16:9 3840x2160": "3840x2160",
    "4K 4:5 2560x3200": "2560x3200",
    "4K 5:4 3200x2560": "3200x2560",
    "4K 1:2 1920x3840": "1920x3840",
    "4K 2:1 3840x1920": "3840x1920",
}
TT_IMAGE_2_ASPECT_RATIOS = [
    "auto", "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9",
    "4:5", "5:4", "1:2", "2:1",
]
TT_IMAGE_2_RESOLUTIONS = ["auto", "1K", "2K", "4K"]
TT_IMAGE_2_SIZE_BY_SELECTION = {
    tuple(label.split(" ", 2)[:2]): size
    for label, size in TT_IMAGE_2_SIZES.items()
    if label != "auto"
}
TT_IMAGE_25_ASPECT_RATIOS = [
    "auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
    "5:4", "4:5", "2:1", "1:2", "21:9", "9:21",
]
BANANA_2_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16",
    "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
]
BANANA_PRO_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16",
    "16:9", "21:9",
]


def _resolve_tt_image_2_size(value: str) -> str:
    # 兼容旧工作流保存的中文值，新工作流统一保存 API 标准值。
    if value == "自动":
        return "auto"
    return TT_IMAGE_2_SIZES[value]


def _resolve_tt_image_2_selection(
    legacy_size: str,
    aspect_ratio: Optional[str],
    resolution: Optional[str],
) -> str:
    if aspect_ratio is None or resolution is None:
        return _resolve_tt_image_2_size(legacy_size)
    if aspect_ratio == "auto" or resolution == "auto":
        return "auto"
    try:
        return TT_IMAGE_2_SIZE_BY_SELECTION[(resolution, aspect_ratio)]
    except KeyError as exc:
        raise ValueError(
            "Unsupported gpt-image-2 resolution/aspect ratio: "
            f"{resolution} {aspect_ratio}"
        ) from exc


def _augment_prompt_for_transparency(
    prompt: str,
    model_type: str,
    tt2_background: str,
    tt25_background: str,
    ui_language: str,
) -> str:
    selected_background = {
        "gpt-image-2": tt2_background,
        "gpt-image-2.5": tt25_background,
    }.get(model_type)
    if selected_background != "transparent":
        return prompt
    if any(
        instruction in prompt
        for instruction in TRANSPARENT_BACKGROUND_PROMPTS.values()
    ):
        return prompt

    instruction = TRANSPARENT_BACKGROUND_PROMPTS[
        _normalize_ui_language(ui_language)
    ]
    return f"{prompt.rstrip()}\n{instruction}" if prompt.strip() else instruction


def _build_model_params(
    model_type: str,
    tt2_size: str,
    tt2_quality: str,
    tt25_version: str,
    tt25_aspect_ratio: str,
    tt25_resolution: str,
    tt25_quality: str,
    tt25_background: str,
    banana2_aspect_ratio: str,
    banana2_image_size: str,
    banana2_thinking_level: str,
    banana_pro_aspect_ratio: str,
    banana_pro_image_size: str,
    tt2_aspect_ratio: Optional[str] = None,
    tt2_resolution: Optional[str] = None,
    tt2_background: str = "opaque",
) -> Dict[str, Any]:
    family = MODEL_CONFIGS[model_type]["family"]
    if family == "tt-image-2":
        return {
            "size": _resolve_tt_image_2_selection(
                tt2_size,
                tt2_aspect_ratio,
                tt2_resolution,
            ),
            "quality": tt2_quality,
            "n": 1,
        }
    if family == "tt-image-2.5":
        # 任一项为 auto 时，比例和分辨率必须同时为 auto。
        if tt25_aspect_ratio == "auto" or tt25_resolution == "auto":
            tt25_aspect_ratio = "auto"
            tt25_resolution = "auto"
        return {
            "version": tt25_version,
            "aspect_ratio": tt25_aspect_ratio,
            "resolution": tt25_resolution,
            "quality": tt25_quality,
            "background": tt25_background,
            "n": 1,
        }
    if family == "banana-2":
        return {
            "aspectRatio": banana2_aspect_ratio,
            "imageSize": banana2_image_size,
            "thinkingLevel": banana2_thinking_level,
            "n": 1,
        }
    return {
        "aspectRatio": banana_pro_aspect_ratio,
        "imageSize": banana_pro_image_size,
        "n": 1,
    }


class MengBaoImageAPI:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {"multiline": True, "default": DEFAULT_PROMPTS["en"]},
                ),
                "connection_json": (
                    "STRING",
                    {"default": "", "multiline": True},
                ),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "model_type": (MODEL_TYPES, {"default": "gpt-image-2"}),
                "batch_size": (
                    "INT",
                    {"default": 1, "min": 1, "max": 10, "step": 1},
                ),
                "tt2_size": (list(TT_IMAGE_2_SIZES), {"default": "auto"}),
                "tt2_aspect_ratio": (
                    TT_IMAGE_2_ASPECT_RATIOS,
                    {"default": "auto"},
                ),
                "tt2_resolution": (
                    TT_IMAGE_2_RESOLUTIONS,
                    {"default": "auto"},
                ),
                "tt2_background": (
                    ["opaque", "transparent", "auto"],
                    {"default": "opaque"},
                ),
                "tt2_quality": (
                    ["auto", "high", "medium", "low"],
                    {"default": "auto"},
                ),
                "tt25_version": (
                    ["flare", "sunburst"],
                    {"default": "flare"},
                ),
                "tt25_aspect_ratio": (
                    TT_IMAGE_25_ASPECT_RATIOS,
                    {"default": "auto"},
                ),
                "tt25_resolution": (
                    ["auto", "1K", "2K", "4K"],
                    {"default": "auto"},
                ),
                "tt25_quality": (
                    ["auto", "low", "medium", "high", "xhigh", "max"],
                    {"default": "auto"},
                ),
                "tt25_background": (
                    ["opaque", "transparent", "auto"],
                    {"default": "opaque"},
                ),
                "banana2_aspect_ratio": (
                    BANANA_2_ASPECT_RATIOS,
                    {"default": "1:1"},
                ),
                "banana2_image_size": (
                    ["0.5K", "1K", "2K", "4K"],
                    {"default": "1K"},
                ),
                "banana2_thinking_level": (
                    ["minimal", "high"],
                    {"default": "minimal"},
                ),
                "banana_pro_aspect_ratio": (
                    BANANA_PRO_ASPECT_RATIOS,
                    {"default": "1:1"},
                ),
                "banana_pro_image_size": (
                    ["1K", "2K", "4K"],
                    {"default": "1K"},
                ),
                "timeout": (
                    "INT",
                    {"default": 600, "min": 30, "max": 1800, "step": 10},
                ),
                "retries": (
                    "INT",
                    {"default": 2, "min": 0, "max": 5, "step": 1},
                ),
                "ui_language": (["en", "zh"], {"default": "en"}),
            },
            "optional": {
                f"image_{index}": ("IMAGE",)
                for index in range(1, MAX_REFERENCE_IMAGE_COUNT + 1)
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "text", "failed_urls")
    FUNCTION = "generate"
    CATEGORY = "萌宝AI/图像API"
    DESCRIPTION = (
        "萌宝AI 图像生成节点：使用 TT Image 与 Nano Banana 模型生成和编辑图像。"
    )
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "WANGImageAPI",
        "MengBao Image API",
        "MengBao-Image-API",
        "MengBao AI Image Generation",
        "MengBaoAI Image Generation",
        "WANG Image API",
        "萌宝",
        "萌宝AI",
        "萌宝AI 图像生成",
        "萌宝AI·图像生成",
        "萌宝图像",
        "萌宝图像 API",
    ]

    def generate(
        self,
        prompt: str,
        connection_json: str,
        api_key: str,
        model_type: str,
        batch_size: int,
        tt2_size: str,
        tt2_aspect_ratio: str,
        tt2_resolution: str,
        tt2_background: str,
        tt2_quality: str,
        tt25_version: str,
        tt25_aspect_ratio: str,
        tt25_resolution: str,
        tt25_quality: str,
        tt25_background: str,
        banana2_aspect_ratio: str,
        banana2_image_size: str,
        banana2_thinking_level: str,
        banana_pro_aspect_ratio: str,
        banana_pro_image_size: str,
        timeout: int,
        retries: int,
        ui_language: str,
        image_1: Optional[torch.Tensor] = None,
        image_2: Optional[torch.Tensor] = None,
        image_3: Optional[torch.Tensor] = None,
        image_4: Optional[torch.Tensor] = None,
        image_5: Optional[torch.Tensor] = None,
        **additional_images: Optional[torch.Tensor],
    ):
        api_key = _connection_key(connection_json, api_key)
        if not api_key:
            raise ValueError("api_key is empty")
        if model_type not in MODEL_CONFIGS:
            raise ValueError(f"Unsupported model_type: {model_type}")

        config = MODEL_CONFIGS[model_type]
        image_inputs = [image_1, image_2, image_3, image_4, image_5]
        image_inputs.extend(
            additional_images.get(f"image_{index}")
            for index in range(
                NAMED_REFERENCE_IMAGE_COUNT + 1,
                MAX_REFERENCE_IMAGE_COUNT + 1,
            )
        )
        reference_images = _optional_images(
            image_inputs,
            limit=int(config["max_images"]),
        )
        model_params = _build_model_params(
            model_type,
            tt2_size,
            tt2_quality,
            tt25_version,
            tt25_aspect_ratio,
            tt25_resolution,
            tt25_quality,
            tt25_background,
            banana2_aspect_ratio,
            banana2_image_size,
            banana2_thinking_level,
            banana_pro_aspect_ratio,
            banana_pro_image_size,
            tt2_aspect_ratio=tt2_aspect_ratio,
            tt2_resolution=tt2_resolution,
            tt2_background=tt2_background,
        )
        request_prompt = _augment_prompt_for_transparency(
            prompt,
            model_type,
            tt2_background,
            tt25_background,
            ui_language,
        )

        all_images: List[torch.Tensor] = []
        payloads: List[Dict[str, Any]] = []
        failed_urls: List[str] = []
        batch_count = int(batch_size)
        progress_total = max(1, batch_count) * 100
        progress_bar = (
            ComfyProgressBar(progress_total)
            if ComfyProgressBar is not None
            else None
        )
        for batch_index in range(batch_count):
            def update_batch_progress(percent: int) -> None:
                if progress_bar is None:
                    return
                absolute = batch_index * 100 + max(0, min(100, int(percent)))
                progress_bar.update_absolute(absolute, progress_total)

            update_batch_progress(1)
            try:
                payload = _call_media_api(
                    api_key=api_key,
                    model_type=model_type,
                    prompt=request_prompt,
                    params=model_params,
                    reference_images=reference_images,
                    timeout=int(timeout),
                    retries=int(retries),
                    progress_callback=update_batch_progress,
                )
            except Exception as exc:
                payload = {
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                        "api_base": FIXED_API_BASE,
                        "display_model": model_type,
                        "model": config["api_model"],
                        "api_key": _mask_key(api_key),
                    }
                }

            payloads.append(payload)
            images, failed = _extract_images(
                payload,
                int(timeout),
                int(retries),
            )
            all_images.extend(images)
            failed_urls.extend(failed)
            if not images:
                print(f"[MengBao AI] No image returned. {_json_text(payload)}")
            update_batch_progress(100)

        text = "\n\n".join(_json_text(payload) for payload in payloads)
        return {
            "ui": {"mengbao_balance_refresh": [True]},
            "result": (
                _cat_images(
                    all_images,
                    text,
                    _normalize_ui_language(ui_language),
                ),
                text,
                "\n".join(failed_urls),
            ),
        }
