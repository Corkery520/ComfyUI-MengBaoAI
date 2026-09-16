import asyncio
import json
import os
from pathlib import Path
from typing import List

from .image_client import fetch_balance


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ENV_API_KEY_NAME = "MENGBAO_API_KEY"


def _user_data_directory() -> Path:
    override = os.environ.get("MENGBAOAI_USER_DIRECTORY", "").strip()
    if override:
        return Path(override)
    try:
        import folder_paths

        return Path(folder_paths.get_user_directory()) / "mengbaoai"
    except Exception:
        return PLUGIN_ROOT / ".mengbaoai"


USER_DATA_DIRECTORY = _user_data_directory()
ENV_PATH = USER_DATA_DIRECTORY / ".env"
LEGACY_ENV_PATHS = (
    PLUGIN_ROOT / ".env",
    PLUGIN_ROOT.parent / "ComfyUI-MengBao-Image-API" / ".env",
    PLUGIN_ROOT.parent.parent
    / "disabled_custom_nodes"
    / "ComfyUI-MengBao-Image-API"
    / ".env",
)


def json_connection_key(value: str) -> str:
    value = (value or "").strip()
    if not value.startswith("{"):
        return ""
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("key") or "").strip()


def provided_connection_key(connection_json: str, api_key: str) -> str:
    # 旧工作流仍可通过 connection_json 提供密钥。
    api_key = (api_key or "").strip()
    if api_key:
        return json_connection_key(api_key) or api_key
    return json_connection_key(connection_json)


def _read_key_from_path(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == ENV_API_KEY_NAME:
                return value.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def read_saved_api_key() -> str:
    saved = _read_key_from_path(ENV_PATH)
    if saved:
        return saved

    for legacy_path in LEGACY_ENV_PATHS:
        saved = _read_key_from_path(legacy_path)
        if saved:
            save_api_key(saved)
            return saved
    return ""


def save_api_key(api_key: str) -> None:
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError("api_key is empty")
    if "\n" in api_key or "\r" in api_key:
        raise ValueError("api_key contains an invalid newline")

    USER_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if ENV_PATH.is_file():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    replacement = f"{ENV_API_KEY_NAME}={api_key}"
    replaced = False
    for index, line in enumerate(lines):
        if line.partition("=")[0].strip() == ENV_API_KEY_NAME:
            lines[index] = replacement
            replaced = True
            break
    if not replaced:
        lines.append(replacement)

    temporary_path = ENV_PATH.with_name(f"{ENV_PATH.name}.tmp")
    temporary_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    temporary_path.replace(ENV_PATH)


def connection_key(connection_json: str, api_key: str) -> str:
    return provided_connection_key(connection_json, api_key) or read_saved_api_key()


def mask_key(value: str) -> str:
    if len(value or "") <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


_ROUTES_REGISTERED = False


def register_image_routes() -> None:
    global _ROUTES_REGISTERED
    if _ROUTES_REGISTERED:
        return

    try:
        from aiohttp import web
        from server import PromptServer
    except ImportError:
        return
    if getattr(PromptServer, "instance", None) is None:
        return

    routes = PromptServer.instance.routes

    @routes.get("/mengbao_image_api/api_key")
    async def mengbao_image_api_key_status(_request):
        return web.json_response({"saved": bool(read_saved_api_key())})

    @routes.post("/mengbao_image_api/api_key")
    async def mengbao_image_api_save_key(request):
        try:
            body = await request.json()
            api_key = provided_connection_key(
                str(body.get("connection_json") or ""),
                str(body.get("api_key") or ""),
            )
            await asyncio.to_thread(save_api_key, api_key)
            return web.json_response({"saved": True})
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

    @routes.post("/mengbao_image_api/balance")
    async def mengbao_image_api_balance(request):
        try:
            body = await request.json()
            api_key = connection_key(
                str(body.get("connection_json") or ""),
                str(body.get("api_key") or ""),
            )
            payload = await asyncio.to_thread(fetch_balance, api_key)
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

    _ROUTES_REGISTERED = True
