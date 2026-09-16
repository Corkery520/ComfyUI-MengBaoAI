import json
import time
from typing import Any, Dict, List

from ...utils import prompt_store
from ...utils.prompt_store import (
    ACTION_OPTIONS,
    MERGE_OPTIONS,
    _atomic_write_json,
    _clean_text,
    _filter_prompts,
    _find_prompt,
    _format_titles,
    _load_store,
    _merge_prompts,
    _normalize_prompt,
    _now,
    _parse_import_payload,
    _prompt_key,
    _resolve_export_path,
    _save_store,
    _split_tags,
    _static_groups,
    _static_titles,
)


class WANGPromptOrganizer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "action": (ACTION_OPTIONS, {"default": "save_or_update"}),
                "group": ("STRING", {"default": "default", "multiline": False}),
                "title": ("STRING", {"default": "new prompt", "multiline": False}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "query": ("STRING", {"default": "", "multiline": False}),
                "tags": ("STRING", {"default": "", "multiline": False}),
                "note": ("STRING", {"default": "", "multiline": True}),
                "merge_mode": (MERGE_OPTIONS, {"default": "update"}),
                "new_group": ("STRING", {"default": "", "multiline": False}),
                "import_json": ("STRING", {"default": "", "multiline": True}),
                "import_path": ("STRING", {"default": "", "multiline": False}),
                "export_path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("selected_prompt", "results_json", "titles_text", "status")
    FUNCTION = "run"
    CATEGORY = "萌宝AI/提示词"
    DESCRIPTION = "保存、分组、搜索、导入和导出提示词。"
    SEARCH_ALIASES = [
        "MengBao",
        "WANG Prompt Organizer",
        "Prompt Organizer",
        "提示词整理器",
    ]

    def run(
        self,
        action: str,
        group: str,
        title: str,
        prompt: str,
        query: str,
        tags: str,
        note: str,
        merge_mode: str,
        new_group: str,
        import_json: str,
        import_path: str,
        export_path: str,
    ):
        data = _load_store()
        prompts = data.get("prompts", [])
        action = action if action in ACTION_OPTIONS else "list"
        selected_prompt = ""
        status = ""
        results: List[Dict[str, Any]] = []

        if action == "save_or_update":
            clean_title = _clean_text(title) or "Untitled"
            clean_group = _clean_text(group) or "default"
            existing = _find_prompt(prompts, clean_group, clean_title)
            if existing:
                existing.update(
                    {
                        "prompt": str(prompt or ""),
                        "tags": _split_tags(tags),
                        "note": str(note or ""),
                        "updated_at": _now(),
                    }
                )
                status = f"Updated prompt: {clean_group} / {clean_title}"
            else:
                prompts.append(
                    _normalize_prompt(
                        {
                            "title": clean_title,
                            "group": clean_group,
                            "prompt": prompt,
                            "tags": tags,
                            "note": note,
                            "created_at": _now(),
                            "updated_at": _now(),
                        }
                    )
                )
                status = f"Saved prompt: {clean_group} / {clean_title}"
            data["prompts"] = prompts
            _save_store(data)
            selected_prompt = str(prompt or "")
            results = _filter_prompts(prompts, clean_group, clean_title)

        elif action == "get":
            item = _find_prompt(prompts, group, title)
            if not item and " / " in title:
                group_part, title_part = title.split(" / ", 1)
                item = _find_prompt(prompts, group_part, title_part)
            if not item:
                raise ValueError(f"Prompt not found: {group} / {title}")
            selected_prompt = item.get("prompt", "")
            results = [item]
            status = f"Loaded prompt: {item.get('group')} / {item.get('title')}"

        elif action == "search":
            results = _filter_prompts(prompts, group, query)
            if results:
                selected_prompt = results[0].get("prompt", "")
            status = f"Found {len(results)} prompt(s)."

        elif action == "list":
            results = _filter_prompts(prompts, group, "")
            status = f"Listed {len(results)} prompt(s)."

        elif action == "delete":
            before = len(prompts)
            wanted = (_clean_text(group).lower(), _clean_text(title).lower())
            prompts = [item for item in prompts if _prompt_key(item) != wanted]
            data["prompts"] = prompts
            _save_store(data)
            status = f"Deleted {before - len(prompts)} prompt(s)."
            results = _filter_prompts(prompts, group, "")

        elif action == "import_json":
            incoming = _parse_import_payload(import_json, import_path)
            merged, created, updated = _merge_prompts(
                prompts,
                incoming,
                merge_mode,
            )
            data["prompts"] = merged
            _save_store(data)
            results = incoming
            status = (
                f"Imported {len(incoming)} prompt(s). "
                f"Created: {created}. Updated: {updated}."
            )

        elif action == "export_json":
            results = _filter_prompts(prompts, group, query)
            payload = {
                "version": 1,
                "exported_at": _now(),
                "prompts": results,
            }
            path = _resolve_export_path(export_path)
            _atomic_write_json(path, payload)
            status = f"Exported {len(results)} prompt(s) to {path}"

        elif action == "rename_group":
            old_group = _clean_text(group)
            target_group = _clean_text(new_group)
            if not old_group or not target_group:
                raise ValueError(
                    "group and new_group are required for rename_group action."
                )
            changed = 0
            for item in prompts:
                if _clean_text(item.get("group")).lower() == old_group.lower():
                    item["group"] = target_group
                    item["updated_at"] = _now()
                    changed += 1
            data["prompts"] = prompts
            _save_store(data)
            results = _filter_prompts(prompts, target_group, "")
            status = (
                f"Renamed group {old_group} to {target_group}. "
                f"Changed: {changed}."
            )

        results_json = json.dumps(
            {"prompts": results},
            ensure_ascii=False,
            indent=2,
        )
        return (
            selected_prompt,
            results_json,
            _format_titles(results),
            status,
        )

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        try:
            return str(prompt_store.STORE_PATH.stat().st_mtime)
        except OSError:
            return str(time.time())

class WANGPromptReader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group": (_static_groups(), {"default": "all"}),
                "title": (_static_titles(), {"default": "Untitled"}),
                "fallback_prompt": (
                    "STRING",
                    {"default": "", "multiline": True},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "status")
    FUNCTION = "read"
    CATEGORY = "萌宝AI/提示词"
    DESCRIPTION = "按分组和标题读取已保存的提示词。"
    SEARCH_ALIASES = [
        "MengBao",
        "WANG Prompt Reader",
        "Prompt Reader",
        "提示词读取",
    ]

    def read(self, group: str, title: str, fallback_prompt: str):
        data = _load_store()
        prompts = data.get("prompts", [])
        clean_group = _clean_text(group)
        clean_title = _clean_text(title)

        item = {}
        if " / " in clean_title:
            group_part, title_part = clean_title.split(" / ", 1)
            item = _find_prompt(prompts, group_part, title_part)
        if not item and clean_group.lower() != "all":
            item = _find_prompt(prompts, clean_group, clean_title)
        if not item:
            matches = _filter_prompts(prompts, clean_group, clean_title)
            item = matches[0] if matches else {}

        if item:
            return (
                item.get("prompt", ""),
                f"Loaded prompt: {item.get('group')} / {item.get('title')}",
            )
        return (
            fallback_prompt,
            "No saved prompt matched. Returned fallback_prompt.",
        )

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        try:
            return str(prompt_store.STORE_PATH.stat().st_mtime)
        except OSError:
            return str(time.time())
