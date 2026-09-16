import base64
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
import torch

from ..utils.image import png_bytes_to_image_tensor


MODEL_CONFIGS = {
    "gpt-image-2": {
        "api_model": "tt-image-2",
        "family": "tt-image-2",
        "max_images": 14,
    },
    "gpt-image-2.5": {
        "api_model": "tt-image-2.5",
        "family": "tt-image-2.5",
        "max_images": 16,
    },
    "nano-banana-2": {
        "api_model": "banana-2",
        "family": "banana-2",
        "max_images": 14,
    },
    "nano-banana-2-pro": {
        "api_model": "banana-pro",
        "family": "banana-pro",
        "max_images": 14,
    },
}
MODEL_TYPES = list(MODEL_CONFIGS)

FIXED_API_BASE = "https://api.lk888.ai"
BALANCE_URL = f"{FIXED_API_BASE}/api/v1/skills/balance"
MEDIA_GENERATE_PATH = "/v1/media/generate"
MEDIA_STATUS_PATH = "/v1/media/status"
POLL_INTERVAL_SECONDS = 3.0


def response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text


def http_error(
    response: requests.Response,
    request_info: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "error": {
            "type": "http_error",
            "status_code": response.status_code,
            "reason": response.reason,
            "url": response.url,
            "response": response_body(response),
            "request": request_info,
        }
    }


def fetch_balance(api_key: str, timeout: int = 30) -> Any:
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError("api_key is empty")

    response = requests.get(
        BALANCE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )
    payload = response_body(response)
    if response.ok:
        return payload
    return http_error(response, {"url": BALANCE_URL})


def task_error(message: str, task_id: Any, task_payload: Any) -> Dict[str, Any]:
    return {
        "error": {
            "type": "media_task_error",
            "message": message,
            "task_id": task_id,
            "task": task_payload,
        }
    }


def get_with_retries(
    url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
    timeout: int,
    retries: int,
):
    last_response = None
    last_exception: Optional[Exception] = None
    for attempt in range(max(1, retries + 1)):
        try:
            last_response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            if last_response.status_code not in (429, 500, 502, 503, 504):
                return last_response
        except requests.RequestException as exc:
            last_exception = exc
        if attempt < retries:
            time.sleep(min(1.0 + attempt, 3.0))
    if last_response is not None:
        return last_response
    raise last_exception or RuntimeError("GET request failed without a response")


def extract_task_id(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and data.get("task_id") is not None:
        return data["task_id"]
    return payload.get("task_id")


def task_progress_percent(payload: Any) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    value = payload.get("progress")
    if value is None and isinstance(payload.get("data"), dict):
        value = payload["data"].get("progress")
    if value is None or isinstance(value, bool):
        return None

    try:
        if isinstance(value, str):
            cleaned = value.strip().rstrip("%").strip()
            if not cleaned:
                return None
            number = float(cleaned)
        else:
            number = float(value)
    except (TypeError, ValueError):
        return None

    if 0.0 <= number <= 1.0 and not isinstance(value, str):
        number *= 100.0
    return max(0, min(100, int(round(number))))


def _to_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def call_media_api(
    api_key: str,
    model_type: str,
    prompt: str,
    params: Dict[str, Any],
    reference_images: List[bytes],
    timeout: int,
    retries: int,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Dict[str, Any]:
    config = MODEL_CONFIGS[model_type]
    api_model = config["api_model"]
    request_params = dict(params)
    if reference_images:
        request_params["images"] = [_to_data_url(image) for image in reference_images]

    payload = {"model": api_model, "prompt": prompt, "params": request_params}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    generate_url = f"{FIXED_API_BASE}{MEDIA_GENERATE_PATH}"
    request_info = {
        "url": generate_url,
        "display_model": model_type,
        "model": api_model,
        "params": {
            key: value
            for key, value in request_params.items()
            if key != "images"
        },
        "reference_image_count": len(reference_images),
    }

    # 创建任务不自动重试，避免网络中断后重复创建任务并扣费。
    response = requests.post(
        generate_url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    if not response.ok:
        return http_error(response, request_info)

    create_payload = response_body(response)
    task_id = extract_task_id(create_payload)
    if task_id is None:
        return task_error(
            "Create response did not contain task_id",
            None,
            create_payload,
        )
    if progress_callback is not None:
        progress_callback(2)

    status_url = f"{FIXED_API_BASE}{MEDIA_STATUS_PATH}"
    deadline = time.monotonic() + timeout
    latest_payload: Any = create_payload
    while time.monotonic() < deadline:
        remaining = max(1, int(deadline - time.monotonic()))
        status_response = get_with_retries(
            status_url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"task_id": task_id},
            timeout=min(remaining, 60),
            retries=retries,
        )
        if not status_response.ok:
            return http_error(
                status_response,
                {
                    "url": status_url,
                    "task_id": task_id,
                    "display_model": model_type,
                    "model": api_model,
                },
            )

        latest_payload = response_body(status_response)
        progress = task_progress_percent(latest_payload)
        if progress is not None and progress_callback is not None:
            progress_callback(progress)
        if isinstance(latest_payload, dict) and latest_payload.get("is_final") is True:
            if latest_payload.get("state") == "success":
                latest_payload.setdefault("request", request_info)
                return latest_payload
            error_message = str(latest_payload.get("error") or "Media task failed")
            return task_error(error_message, task_id, latest_payload)

        time.sleep(
            min(POLL_INTERVAL_SECONDS, max(0.0, deadline - time.monotonic()))
        )

    return task_error(
        f"Polling timed out after {timeout} seconds; "
        "query the task_id instead of submitting again",
        task_id,
        latest_payload,
    )


def _decode_base64_image(value: str) -> bytes:
    value = value.strip()
    if value.startswith("data:image/") and "," in value:
        value = value.split(",", 1)[1]
    return base64.b64decode(re.sub(r"\s+", "", value))


def collect_image_sources(payload: Any) -> Tuple[List[str], List[str]]:
    base64_values: List[str] = []
    urls: List[str] = []
    url_keys = {
        "image_url",
        "output_url",
        "image_output_url",
        "result_url",
        "fileuri",
        "file_uri",
    }
    base64_keys = {"b64_json", "base64", "image_base64"}

    def visit(value: Any, parent_key: str = ""):
        if isinstance(value, dict):
            inline_data = value.get("inlineData") or value.get("inline_data")
            if isinstance(inline_data, dict) and isinstance(
                inline_data.get("data"),
                str,
            ):
                base64_values.append(inline_data["data"])
            for key, child in value.items():
                lowered = str(key).lower()
                if lowered in base64_keys and isinstance(child, str):
                    base64_values.append(child)
                elif (
                    lowered == "url"
                    and parent_key in {"data", "image_url", "images", "result_url"}
                ):
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


def extract_images(
    payload: Any,
    timeout: int,
    retries: int,
) -> Tuple[List[torch.Tensor], List[str]]:
    images: List[torch.Tensor] = []
    failed_urls: List[str] = []
    base64_values, urls = collect_image_sources(payload)

    for encoded in base64_values:
        try:
            images.append(png_bytes_to_image_tensor(_decode_base64_image(encoded)))
        except Exception:
            continue

    for url in urls:
        try:
            response = get_with_retries(
                url,
                headers={},
                params={},
                timeout=timeout,
                retries=retries,
            )
            response.raise_for_status()
            images.append(png_bytes_to_image_tensor(response.content))
        except Exception:
            failed_urls.append(url)
    return images, failed_urls
