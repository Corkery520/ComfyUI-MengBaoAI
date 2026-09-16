from ..utils.prompt_store import (
    _add_group,
    _api_payload,
    _delete_group,
    _delete_prompt_by_id,
    _filter_prompts,
    _load_store,
    _merge_prompts,
    _move_prompts,
    _now,
    _parse_import_payload,
    _rename_group,
    _save_store,
    _upsert_prompt,
)


_ROUTES_REGISTERED = False


def register_prompt_routes() -> None:
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

    @routes.get("/wang_prompt_organizer/prompts")
    async def wang_prompt_list(request):
        data = _load_store()
        prompts = _filter_prompts(
            data.get("prompts", []),
            request.query.get("group", "all"),
            request.query.get("query", ""),
        )
        return web.json_response(_api_payload(prompts))

    @routes.post("/wang_prompt_organizer/prompt")
    async def wang_prompt_save(request):
        result = _upsert_prompt(await request.json())
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            result["status"],
        )
        response["prompt"] = result["prompt"]
        return web.json_response(response)

    @routes.delete("/wang_prompt_organizer/prompt/{prompt_id}")
    async def wang_prompt_delete(request):
        result = _delete_prompt_by_id(request.match_info["prompt_id"])
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            "deleted",
        )
        response.update(result)
        return web.json_response(response)

    @routes.post("/wang_prompt_organizer/group")
    async def wang_prompt_add_group(request):
        result = _add_group((await request.json()).get("group", ""))
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            "group_saved",
        )
        response.update(result)
        return web.json_response(response)

    @routes.delete("/wang_prompt_organizer/group/{group}")
    async def wang_prompt_delete_group(request):
        result = _delete_group(request.match_info["group"])
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            "group_deleted",
        )
        response.update(result)
        return web.json_response(response)

    @routes.post("/wang_prompt_organizer/prompts/move")
    async def wang_prompt_move_prompts(request):
        payload = await request.json()
        result = _move_prompts(
            payload.get("prompt_ids", []),
            payload.get("target_group", ""),
        )
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            "moved",
        )
        response.update(result)
        return web.json_response(response)

    @routes.post("/wang_prompt_organizer/import")
    async def wang_prompt_import(request):
        payload = await request.json()
        incoming = _parse_import_payload(
            payload.get("import_json", ""),
            payload.get("import_path", ""),
        )
        data = _load_store()
        merged, created, updated = _merge_prompts(
            data.get("prompts", []),
            incoming,
            payload.get("merge_mode", "update"),
        )
        data["prompts"] = merged
        _save_store(data)
        response = _api_payload(_filter_prompts(merged), "imported")
        response.update(
            {
                "imported": len(incoming),
                "created": created,
                "updated": updated,
            }
        )
        return web.json_response(response)

    @routes.get("/wang_prompt_organizer/export")
    async def wang_prompt_export(request):
        data = _load_store()
        prompts = _filter_prompts(
            data.get("prompts", []),
            request.query.get("group", "all"),
            request.query.get("query", ""),
        )
        return web.json_response(
            {"version": 1, "exported_at": _now(), "prompts": prompts}
        )

    @routes.post("/wang_prompt_organizer/group/rename")
    async def wang_prompt_rename_group(request):
        payload = await request.json()
        result = _rename_group(
            payload.get("old_group", ""),
            payload.get("new_group", ""),
        )
        data = _load_store()
        response = _api_payload(
            _filter_prompts(data.get("prompts", [])),
            "renamed",
        )
        response.update(result)
        return web.json_response(response)

    _ROUTES_REGISTERED = True
