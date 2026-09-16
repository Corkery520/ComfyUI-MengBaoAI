import asyncio
import hashlib
import json

from .vision_client import run_vision
from .image_client import MODEL_CONFIGS
from ..utils.replica import compile_settings, description_prompt, parse_description
from ..utils.replica_store import REPLICA_STORE, identity
from ..utils.material_store import MAX_UPLOAD_BYTES


_REGISTERED = False


def register_replica_routes():
    global _REGISTERED
    if _REGISTERED:
        return
    try:
        from aiohttp import web
        from server import PromptServer
    except ImportError:
        return
    if not getattr(PromptServer, "instance", None):
        return
    routes = PromptServer.instance.routes

    def error(exc):
        return web.json_response({"error": {"type": type(exc).__name__, "message": str(exc)}}, status=400 if isinstance(exc, ValueError) else 404 if isinstance(exc, FileNotFoundError) else 502)

    @routes.get("/mengbao_replica/capabilities")
    async def capabilities(_request):
        return web.json_response({name: config["max_images"] for name, config in MODEL_CONFIGS.items()})

    @routes.get("/mengbao_replica/analysis/{id}")
    async def analysis(request):
        try:
            return web.json_response(await asyncio.to_thread(REPLICA_STORE.analysis, request.match_info["id"]))
        except Exception as exc:
            return error(exc)

    @routes.get("/mengbao_replica/assets/{id}/file")
    async def asset_file(request):
        try:
            path = await asyncio.to_thread(REPLICA_STORE.asset_path, request.match_info["id"])
            return web.FileResponse(path)
        except Exception as exc:
            return error(exc)

    @routes.post("/mengbao_replica/assets")
    async def upload_asset(request):
        try:
            reader = await request.multipart()
            async for part in reader:
                if part.name != "image":
                    continue
                content = bytearray()
                while chunk := await part.read_chunk():
                    content.extend(chunk)
                    if len(content) > MAX_UPLOAD_BYTES:
                        raise ValueError("Image file must be between 1 byte and 32 MB")
                asset = await asyncio.to_thread(REPLICA_STORE.put_asset, bytes(content), part.filename or "clipboard.png")
                return web.json_response(asset)
            raise ValueError("No image file provided")
        except Exception as exc:
            return error(exc)

    @routes.get("/mengbao_replica/drafts/{id}")
    async def get_draft(request):
        try:
            return web.json_response(await asyncio.to_thread(REPLICA_STORE.draft, request.match_info["id"]))
        except Exception as exc:
            return error(exc)

    @routes.post("/mengbao_replica/drafts/{id}")
    async def save_draft(request):
        try:
            draft = await request.json()
            if not isinstance(draft, dict):
                raise ValueError("Replica draft must be a JSON object")
            if draft.get("confirmed"):
                record = await asyncio.to_thread(REPLICA_STORE.analysis, draft.get("analysis_id"))
                await asyncio.to_thread(compile_settings, record, draft, REPLICA_STORE)
            await asyncio.to_thread(REPLICA_STORE.save_draft, request.match_info["id"], draft)
            return web.json_response({"saved": True})
        except Exception as exc:
            return error(exc)

    @routes.post("/mengbao_replica/describe")
    async def describe(request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Product description request must be a JSON object")
            request_id = identity(body.get("request_id"))
            element = body.get("element")
            images = body.get("images")
            if not isinstance(element, dict) or element.get("kind") != "product" or not isinstance(images, list) or not 1 <= len(images) <= 16:
                raise ValueError("AI Product Description requires a product element and 1 to 16 reference images")
            image_bytes = [await asyncio.to_thread(REPLICA_STORE.asset_bytes, image) for image in images]
            prompt = description_prompt(element, str(body.get("description") or ""))
            fingerprint = "description:" + hashlib.sha256((prompt + json.dumps(images)).encode()).hexdigest()
            result = await asyncio.to_thread(REPLICA_STORE.begin, request_id, fingerprint)
            if result is None:
                try:
                    client_id = body.get("client_id")

                    def stage(detail):
                        if isinstance(client_id, str) and 0 < len(client_id) <= 128:
                            PromptServer.instance.send_sync("mengbao_replica_description_status", {"request_id": request_id, **detail}, client_id)

                    result = await asyncio.to_thread(run_vision, prompt, image_bytes, parse_description, max_tokens=1500, on_stage=stage)
                    await asyncio.to_thread(REPLICA_STORE.complete, request_id, result)
                except BaseException as exc:
                    await asyncio.to_thread(REPLICA_STORE.fail, request_id, str(exc) or "Vision request interrupted")
                    raise
            return web.json_response(result)
        except Exception as exc:
            return error(exc)

    _REGISTERED = True
