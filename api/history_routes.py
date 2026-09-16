import asyncio

from ..utils.history_store import HISTORY_STORE


_ROUTES_REGISTERED = False


def register_history_routes():
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
    try:
        HISTORY_STORE.recover_interrupted()
    except Exception as exc:
        print(f"[MengBao AI] History recovery failed: {exc}")
    routes = PromptServer.instance.routes

    def error_response(exc):
        status = 404 if isinstance(exc, FileNotFoundError) else 400 if isinstance(exc, (ValueError, TypeError)) else 500
        return web.json_response({"error": {"type": type(exc).__name__, "message": str(exc)}}, status=status)

    @routes.get("/mengbao_history/items")
    async def list_history(request):
        try:
            payload = await asyncio.to_thread(HISTORY_STORE.list_items,
                query=request.query.get("query", ""), state=request.query.get("state", ""),
                limit=request.query.get("limit", "60"), offset=request.query.get("offset", "0"),
                oldest=request.query.get("oldest") == "1")
            return web.json_response(payload)
        except Exception as exc:
            return error_response(exc)

    @routes.get("/mengbao_history/item/{record_id}")
    async def get_history(request):
        try:
            return web.json_response(await asyncio.to_thread(HISTORY_STORE.get_item, request.match_info["record_id"]))
        except Exception as exc:
            return error_response(exc)

    @routes.get("/mengbao_history/file/{record_id}/{index}")
    async def history_file(request):
        try:
            path = await asyncio.to_thread(HISTORY_STORE.file_path, request.match_info["record_id"],
                int(request.match_info["index"]), request.query.get("thumbnail") == "1")
            headers = {"Content-Type": "image/png", "X-Content-Type-Options": "nosniff"}
            if request.query.get("download") == "1":
                headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
            return web.FileResponse(path, headers=headers)
        except Exception as exc:
            return error_response(exc)

    _ROUTES_REGISTERED = True
