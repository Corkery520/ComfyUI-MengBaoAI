import base64
import asyncio
import io
import json
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import requests
import torch
from PIL import Image, ImageDraw

try:
    from aiohttp import web
    from server import PromptServer
except ImportError:
    web = None
    PromptServer = None


MODEL_CONFIGS = {
    "gpt-image-2": {"api_model": "tt-image-2", "family": "tt-image-2", "max_images": 14},
    "gpt-image-2.5": {"api_model": "tt-image-2.5", "family": "tt-image-2.5", "max_images": 16},
    "nano-banana-2": {"api_model": "banana-2", "family": "banana-2", "max_images": 14},
    "nano-banana-2-pro": {"api_model": "banana-pro", "family": "banana-pro", "max_images": 14},
}
MODEL_TYPES = list(MODEL_CONFIGS.keys())

FIXED_API_BASE = "https://api.lk888.ai"
BALANCE_URL = f"{FIXED_API_BASE}/api/v1/skills/balance"
MEDIA_GENERATE_PATH = "/v1/media/generate"
MEDIA_STATUS_PATH = "/v1/media/status"
POLL_INTERVAL_SECONDS = 3.0
DEFAULT_PROMPTS = {
    "en": "Generate a cinematic image",
    "zh": "生成一张电影感图片",
}
TRANSPARENT_BACKGROUND_PROMPTS = {
    "en": (
        "Precisely isolate the current image subject and remove only the background outside "
        "the subject. Output a transparent PNG with a real Alpha channel. Do not draw a "
        "checkerboard, mosaic, white background, or any other simulated transparency."
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
            f"Unsupported gpt-image-2 resolution/aspect ratio: {resolution} {aspect_ratio}"
        ) from exc


def _normalize_ui_language(value: str) -> str:
    return "zh" if str(value or "").lower().startswith("zh") else "en"


def _message_image_title(ui_language: str) -> str:
    if _normalize_ui_language(ui_language) == "zh":
        return "萌宝图像 API 未收到图片"
    return "MengBao-Image-API did not receive an image"


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
    if any(instruction in prompt for instruction in TRANSPARENT_BACKGROUND_PROMPTS.values()):
        return prompt

    instruction = TRANSPARENT_BACKGROUND_PROMPTS[_normalize_ui_language(ui_language)]
    return f"{prompt.rstrip()}\n{instruction}" if prompt.strip() else instruction

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


def _connection_key(connection_json: str, api_key: str) -> str:
    connection_json = (connection_json or "").strip()
    if connection_json.startswith("{"):
        try:
            data = json.loads(connection_json)
            return str(data.get("key") or api_key or "").strip()
        except json.JSONDecodeError:
            pass
    return (api_key or "").strip()


def _mask_key(value: str) -> str:
    if len(value or "") <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def _json_text(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return str(payload)


def _image_tensor_to_png_bytes(image: torch.Tensor) -> bytes:
    if image.dim() == 4:
        image = image[0]
    if image.dim() != 3:
        raise ValueError("IMAGE input must be [height, width, channels] or [batch, height, width, channels]")

    array = image.detach().cpu().numpy()
    array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
    pil_image = Image.fromarray(array)
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return buffer.getvalue()


def _png_bytes_to_image_tensor(data: bytes) -> torch.Tensor:
    source = Image.open(io.BytesIO(data))
    output_mode = "RGBA" if "A" in source.getbands() else "RGB"
    pil_image = source.convert(output_mode)
    array = np.array(pil_image, dtype=np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def _optional_images(images: Iterable[Optional[torch.Tensor]], limit: int) -> List[bytes]:
    encoded: List[bytes] = []
    for image in images:
        if image is None:
            continue
        batches = image if image.dim() == 4 else image.unsqueeze(0)
        for batch_image in batches:
            encoded.append(_image_tensor_to_png_bytes(batch_image))
            if len(encoded) >= limit:
                return encoded
    return encoded


def _to_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _message_image(
    message: str,
    ui_language: str = "en",
    width: int = 1024,
    height: int = 768,
) -> torch.Tensor:
    pil_image = Image.new("RGB", (width, height), (28, 28, 28))
    draw = ImageDraw.Draw(pil_image)
    lines = [_message_image_title(ui_language), ""]
    clean = (message or "").replace("\r", "\n")
    for raw_line in clean.split("\n"):
        raw_line = raw_line.strip()
        while len(raw_line) > 72:
            lines.append(raw_line[:72])
            raw_line = raw_line[72:]
        if raw_line:
            lines.append(raw_line)
        if len(lines) >= 28:
            lines.append("...")
            break

    y = 28
    for index, line in enumerate(lines):
        color = (255, 120, 120) if index == 0 else (235, 235, 235)
        draw.text((28, y), line, fill=color)
        y += 24

    array = np.asarray(pil_image).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def _cat_images(images: List[torch.Tensor], fallback_text: str, ui_language: str = "en") -> torch.Tensor:
    if not images:
        return _message_image(fallback_text, ui_language)

    target_height = images[0].shape[1]
    target_width = images[0].shape[2]
    target_channels = images[0].shape[3]
    normalized: List[torch.Tensor] = []
    for image in images:
        normalized_image = image
        if normalized_image.shape[3] != target_channels:
            if target_channels == 4 and normalized_image.shape[3] == 3:
                alpha = torch.ones((*normalized_image.shape[:3], 1), dtype=normalized_image.dtype)
                normalized_image = torch.cat([normalized_image, alpha], dim=3)
            else:
                normalized_image = normalized_image[:, :, :, :target_channels]
        if normalized_image.shape[1:3] != (target_height, target_width):
            channels_first = normalized_image.movedim(-1, 1)
            resized = torch.nn.functional.interpolate(
                channels_first,
                size=(target_height, target_width),
                mode="bilinear",
                align_corners=False,
            )
            normalized_image = resized.movedim(1, -1)
        normalized.append(normalized_image)
    return torch.cat(normalized, dim=0).contiguous()


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
        # 文档规定任一项为 auto 时，比例和分辨率必须同时为 auto。
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


def _response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text


def _fetch_balance(api_key: str, timeout: int = 30) -> Any:
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError("api_key is empty")

    response = requests.get(
        BALANCE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )
    payload = _response_body(response)
    if response.ok:
        return payload
    return _http_error(response, {"url": BALANCE_URL})


def _http_error(response: requests.Response, request_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": {
            "type": "http_error",
            "status_code": response.status_code,
            "reason": response.reason,
            "url": response.url,
            "response": _response_body(response),
            "request": request_info,
        }
    }


def _task_error(message: str, task_id: Any, task_payload: Any) -> Dict[str, Any]:
    return {
        "error": {
            "type": "media_task_error",
            "message": message,
            "task_id": task_id,
            "task": task_payload,
        }
    }


def _get_with_retries(url: str, headers: Dict[str, str], params: Dict[str, Any], timeout: int, retries: int):
    last_response = None
    last_exception: Optional[Exception] = None
    for attempt in range(max(1, retries + 1)):
        try:
            last_response = requests.get(url, headers=headers, params=params, timeout=timeout)
            if last_response.status_code not in (429, 500, 502, 503, 504):
                return last_response
        except requests.RequestException as exc:
            last_exception = exc
        if attempt < retries:
            time.sleep(min(1.0 + attempt, 3.0))
    if last_response is not None:
        return last_response
    raise last_exception or RuntimeError("GET request failed without a response")


def _extract_task_id(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and data.get("task_id") is not None:
        return data["task_id"]
    return payload.get("task_id")


def _call_media_api(
    api_key: str,
    model_type: str,
    prompt: str,
    params: Dict[str, Any],
    reference_images: List[bytes],
    timeout: int,
    retries: int,
) -> Dict[str, Any]:
    config = MODEL_CONFIGS[model_type]
    api_model = config["api_model"]
    request_params = dict(params)
    if reference_images:
        request_params["images"] = [_to_data_url(image) for image in reference_images]

    payload = {"model": api_model, "prompt": prompt, "params": request_params}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    generate_url = f"{FIXED_API_BASE}{MEDIA_GENERATE_PATH}"
    request_info = {
        "url": generate_url,
        "display_model": model_type,
        "model": api_model,
        "params": {key: value for key, value in request_params.items() if key != "images"},
        "reference_image_count": len(reference_images),
    }

    # 创建任务不自动重试，防止网络断开但任务已创建时发生重复扣费。
    response = requests.post(generate_url, headers=headers, json=payload, timeout=timeout)
    if not response.ok:
        return _http_error(response, request_info)

    create_payload = _response_body(response)
    task_id = _extract_task_id(create_payload)
    if task_id is None:
        return _task_error("Create response did not contain task_id", None, create_payload)

    status_url = f"{FIXED_API_BASE}{MEDIA_STATUS_PATH}"
    deadline = time.monotonic() + timeout
    latest_payload: Any = create_payload
    while time.monotonic() < deadline:
        remaining = max(1, int(deadline - time.monotonic()))
        status_response = _get_with_retries(
            status_url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"task_id": task_id},
            timeout=min(remaining, 60),
            retries=retries,
        )
        if not status_response.ok:
            return _http_error(
                status_response,
                {"url": status_url, "task_id": task_id, "display_model": model_type, "model": api_model},
            )

        latest_payload = _response_body(status_response)
        if isinstance(latest_payload, dict) and latest_payload.get("is_final") is True:
            if latest_payload.get("state") == "success":
                latest_payload.setdefault("request", request_info)
                return latest_payload
            error_message = str(latest_payload.get("error") or "Media task failed")
            return _task_error(error_message, task_id, latest_payload)

        time.sleep(min(POLL_INTERVAL_SECONDS, max(0.0, deadline - time.monotonic())))

    return _task_error(
        f"Polling timed out after {timeout} seconds; query the task_id instead of submitting again",
        task_id,
        latest_payload,
    )


def _decode_base64_image(value: str) -> bytes:
    value = value.strip()
    if value.startswith("data:image/") and "," in value:
        value = value.split(",", 1)[1]
    return base64.b64decode(re.sub(r"\s+", "", value))


def _collect_image_sources(payload: Any) -> Tuple[List[str], List[str]]:
    base64_values: List[str] = []
    urls: List[str] = []
    url_keys = {"image_url", "output_url", "image_output_url", "result_url", "fileuri", "file_uri"}
    base64_keys = {"b64_json", "base64", "image_base64"}

    def visit(value: Any, parent_key: str = ""):
        if isinstance(value, dict):
            inline_data = value.get("inlineData") or value.get("inline_data")
            if isinstance(inline_data, dict) and isinstance(inline_data.get("data"), str):
                base64_values.append(inline_data["data"])
            for key, child in value.items():
                lowered = str(key).lower()
                if lowered in base64_keys and isinstance(child, str):
                    base64_values.append(child)
                elif lowered == "url" and parent_key in {"data", "image_url", "images", "result_url"}:
                    visit(child, "result_url")
                elif lowered in url_keys:
                    visit(child, lowered)
                elif lowered not in {"inlinedata", "inline_data"}:
                    visit(child, lowered)
        elif isinstance(value, list):
            for child in value:
                visit(child, parent_key)
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("data:image/"):
                base64_values.append(stripped)
            elif parent_key in url_keys:
                if stripped.startswith("[") or stripped.startswith("{"):
                    try:
                        visit(json.loads(stripped), parent_key)
                        return
                    except json.JSONDecodeError:
                        pass
                urls.extend(re.findall(r"https?://[^\s\"'<>]+", stripped))

    visit(payload)
    return list(dict.fromkeys(base64_values)), list(dict.fromkeys(urls))


def _extract_images(payload: Any, timeout: int, retries: int) -> Tuple[List[torch.Tensor], List[str]]:
    images: List[torch.Tensor] = []
    failed_urls: List[str] = []
    base64_values, urls = _collect_image_sources(payload)

    for encoded in base64_values:
        try:
            images.append(_png_bytes_to_image_tensor(_decode_base64_image(encoded)))
        except Exception:
            continue

    for url in urls:
        try:
            response = _get_with_retries(url, headers={}, params={}, timeout=timeout, retries=retries)
            response.raise_for_status()
            images.append(_png_bytes_to_image_tensor(response.content))
        except Exception:
            failed_urls.append(url)
    return images, failed_urls


class MengBaoImageAPI:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": DEFAULT_PROMPTS["en"]}),
                "connection_json": ("STRING", {"default": "", "multiline": True}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "model_type": (MODEL_TYPES, {"default": "gpt-image-2"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "tt2_size": (list(TT_IMAGE_2_SIZES.keys()), {"default": "auto"}),
                "tt2_aspect_ratio": (TT_IMAGE_2_ASPECT_RATIOS, {"default": "1:1"}),
                "tt2_resolution": (TT_IMAGE_2_RESOLUTIONS, {"default": "1K"}),
                "tt2_background": (["opaque", "transparent", "auto"], {"default": "opaque"}),
                "tt2_quality": (["auto", "high", "medium", "low"], {"default": "auto"}),
                "tt25_version": (["flare", "sunburst"], {"default": "flare"}),
                "tt25_aspect_ratio": (TT_IMAGE_25_ASPECT_RATIOS, {"default": "1:1"}),
                "tt25_resolution": (["auto", "1K", "2K", "4K"], {"default": "1K"}),
                "tt25_quality": (["auto", "low", "medium", "high", "xhigh", "max"], {"default": "auto"}),
                "tt25_background": (["opaque", "transparent", "auto"], {"default": "opaque"}),
                "banana2_aspect_ratio": (BANANA_2_ASPECT_RATIOS, {"default": "1:1"}),
                "banana2_image_size": (["0.5K", "1K", "2K", "4K"], {"default": "1K"}),
                "banana2_thinking_level": (["minimal", "high"], {"default": "minimal"}),
                "banana_pro_aspect_ratio": (BANANA_PRO_ASPECT_RATIOS, {"default": "1:1"}),
                "banana_pro_image_size": (["1K", "2K", "4K"], {"default": "1K"}),
                "timeout": ("INT", {"default": 300, "min": 30, "max": 1800, "step": 10}),
                "retries": ("INT", {"default": 2, "min": 0, "max": 5, "step": 1}),
                "ui_language": (["en", "zh"], {"default": "en"}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "image_5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "text", "failed_urls")
    FUNCTION = "generate"
    CATEGORY = "MengBao/Image API"
    DESCRIPTION = "MengBao-Image-API：TT Image 与 Nano Banana 图片生成节点。"

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
    ):
        api_key = _connection_key(connection_json, api_key)
        if not api_key:
            raise ValueError("api_key is empty")
        if model_type not in MODEL_CONFIGS:
            raise ValueError(f"Unsupported model_type: {model_type}")

        config = MODEL_CONFIGS[model_type]
        reference_images = _optional_images(
            [image_1, image_2, image_3, image_4, image_5],
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
        for _ in range(int(batch_size)):
            try:
                payload = _call_media_api(
                    api_key=api_key,
                    model_type=model_type,
                    prompt=request_prompt,
                    params=model_params,
                    reference_images=reference_images,
                    timeout=int(timeout),
                    retries=int(retries),
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
            images, failed = _extract_images(payload, int(timeout), int(retries))
            all_images.extend(images)
            failed_urls.extend(failed)
            if not images:
                print(f"[MengBao-Image-API] No image returned. {_json_text(payload)}")

        text = "\n\n".join(_json_text(payload) for payload in payloads)
        return (
            _cat_images(all_images, text, _normalize_ui_language(ui_language)),
            text,
            "\n".join(failed_urls),
        )


if (
    PromptServer is not None
    and web is not None
    and getattr(PromptServer, "instance", None) is not None
):
    @PromptServer.instance.routes.post("/mengbao_image_api/balance")
    async def mengbao_image_api_balance(request):
        try:
            body = await request.json()
            api_key = _connection_key(
                str(body.get("connection_json") or ""),
                str(body.get("api_key") or ""),
            )
            payload = await asyncio.to_thread(_fetch_balance, api_key)
            status = 200
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    status = int(error.get("status_code") or 200)
            return web.json_response(payload, status=status)
        except Exception as exc:
            return web.json_response(
                {
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                },
                status=400 if isinstance(exc, ValueError) else 500,
            )


NODE_CLASS_MAPPINGS = {
    "WANGImageAPI": MengBaoImageAPI,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WANGImageAPI": "MengBao-Image-API",
}
