import asyncio

from ..utils.material_store import MATERIAL_STORE, MAX_UPLOAD_BYTES


_ROUTES_REGISTERED = False


def register_material_routes():
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

    def error_response(exc):
        status = 404 if isinstance(exc, FileNotFoundError) else 400 if isinstance(exc, ValueError) else 500
        return web.json_response({"error": {"type": type(exc).__name__, "message": str(exc)}}, status=status)

    @routes.get("/mengbao_materials/items")
    async def list_materials(request):
        try:
            payload = await asyncio.to_thread(MATERIAL_STORE.list_items,
                request.query.get("category", ""), request.query.get("query", ""), request.query.get("favorites") == "1")
            return web.json_response(payload)
        except Exception as exc:
            return error_response(exc)

    @routes.get("/mengbao_materials/item/{material_id}")
    async def get_material(request):
        try:
            return web.json_response(await asyncio.to_thread(MATERIAL_STORE.get_item, request.match_info["material_id"]))
        except Exception as exc:
            return error_response(exc)

    @routes.get("/mengbao_materials/file/{material_id}")
    async def material_file(request):
        try:
            path = await asyncio.to_thread(MATERIAL_STORE.file_path, request.match_info["material_id"], request.query.get("thumbnail") == "1")
            return web.FileResponse(path, headers={"Content-Type": "image/png", "X-Content-Type-Options": "nosniff"})
        except Exception as exc:
            return error_response(exc)

    @routes.post("/mengbao_materials/import")
    async def import_material(request):
        try:
            reader = await request.multipart()
            content = bytearray()
            name = ""
            category = "未分类"
            async for part in reader:
                if part.name == "category":
                    category_bytes = await part.read_chunk()
                    if len(category_bytes) > 160 or not part.at_eof():
                        raise ValueError("Invalid material category name")
                    category = category_bytes.decode("utf-8")
                elif part.name == "image":
                    if name:
                        raise ValueError("Import one image per request")
                    name = part.filename or "clipboard_image.png"
                    while chunk := await part.read_chunk():
                        if len(content) + len(chunk) > MAX_UPLOAD_BYTES:
                            raise ValueError("Image file exceeds the 32 MB limit")
                        content.extend(chunk)
            item = await asyncio.to_thread(MATERIAL_STORE.import_image, bytes(content), name, category)
            return web.json_response(item)
        except Exception as exc:
            return error_response(exc)

    @routes.post("/mengbao_materials/item/{material_id}")
    async def update_material(request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Material update must be a JSON object")
            item = await asyncio.to_thread(MATERIAL_STORE.update_item, request.match_info["material_id"], **body)
            return web.json_response(item)
        except Exception as exc:
            return error_response(exc)

    @routes.delete("/mengbao_materials/item/{material_id}")
    async def delete_material(request):
        try:
            await asyncio.to_thread(MATERIAL_STORE.delete_item, request.match_info["material_id"])
            return web.json_response({"deleted": True})
        except Exception as exc:
            return error_response(exc)

    @routes.post("/mengbao_materials/category")
    async def change_category(request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Category update must be a JSON object")
            action = body.get("action", "add")
            if action == "add":
                await asyncio.to_thread(MATERIAL_STORE.add_category, body.get("name"))
            elif action == "rename":
                await asyncio.to_thread(MATERIAL_STORE.rename_category, body.get("current"), body.get("name"))
            elif action == "delete":
                await asyncio.to_thread(MATERIAL_STORE.delete_category, body.get("name"))
            else:
                raise ValueError("Unsupported category action")
            return web.json_response({"saved": True})
        except Exception as exc:
            return error_response(exc)

    _ROUTES_REGISTERED = True
