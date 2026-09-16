import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


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
STORE_PATH = USER_DATA_DIRECTORY / "prompts.json"
DEFAULT_STORE_PATH = PLUGIN_ROOT / "data" / "default_prompts.json"
LEGACY_STORE_PATHS = (
    PLUGIN_ROOT / "data" / "prompts.json",
    PLUGIN_ROOT.parent / "WANG_prompt_organizer_nodes" / "data" / "prompts.json",
    PLUGIN_ROOT.parent.parent
    / "disabled_custom_nodes"
    / "WANG_prompt_organizer_nodes"
    / "data"
    / "prompts.json",
)


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "groups": ["default"], "prompts": []}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _ensure_store() -> None:
    if STORE_PATH.exists():
        return

    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    for candidate in (*LEGACY_STORE_PATHS, DEFAULT_STORE_PATH):
        if candidate.is_file() and candidate.resolve() != STORE_PATH.resolve():
            shutil.copy2(candidate, STORE_PATH)
            return
    _atomic_write_json(STORE_PATH, _empty_store())


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_groups(
    groups: Iterable[Any],
    prompts: Iterable[Dict[str, Any]] = (),
) -> List[str]:
    results: List[str] = []
    seen = set()
    for group in list(groups) + [item.get("group") for item in prompts]:
        clean = _clean_text(group) or "default"
        key = clean.lower()
        if key not in seen:
            seen.add(key)
            results.append(clean)
    if "default" not in seen:
        results.insert(0, "default")
    return results


def _split_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        raw_tags = value
    else:
        raw_tags = str(value or "").replace("，", ",").replace(";", ",").split(",")
    tags = []
    seen = set()
    for tag in raw_tags:
        clean = _clean_text(tag)
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            tags.append(clean)
    return tags


def _normalize_prompt(item: Dict[str, Any]) -> Dict[str, Any]:
    created_at = _clean_text(item.get("created_at")) or _now()
    updated_at = _clean_text(item.get("updated_at")) or created_at
    return {
        "id": _clean_text(item.get("id")) or uuid.uuid4().hex,
        "title": _clean_text(item.get("title")) or "Untitled",
        "group": _clean_text(item.get("group")) or "default",
        "prompt": str(item.get("prompt") or ""),
        "tags": _split_tags(item.get("tags")),
        "note": str(item.get("note") or ""),
        "color": _clean_text(item.get("color")) or "#e25545",
        "preview_image": str(item.get("preview_image") or ""),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _prompt_key(item: Dict[str, Any]) -> Tuple[str, str]:
    return (
        _clean_text(item.get("group")).lower(),
        _clean_text(item.get("title")).lower(),
    )


def _load_store() -> Dict[str, Any]:
    _ensure_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_path = STORE_PATH.with_name(
            f"{STORE_PATH.name}.broken-{int(time.time())}.bak"
        )
        shutil.copy2(STORE_PATH, backup_path)
        data = _empty_store()
        _atomic_write_json(STORE_PATH, data)

    prompts = data.get("prompts", [])
    if not isinstance(prompts, list):
        prompts = []
    groups = data.get("groups", [])
    if not isinstance(groups, list):
        groups = []
    data["version"] = int(data.get("version", 1) or 1)
    data["prompts"] = [
        _normalize_prompt(item)
        for item in prompts
        if isinstance(item, dict)
    ]
    data["groups"] = _normalize_groups(groups, data["prompts"])
    return data


def _save_store(data: Dict[str, Any]) -> None:
    data["version"] = 1
    data["prompts"] = [
        _normalize_prompt(item)
        for item in data.get("prompts", [])
        if isinstance(item, dict)
    ]
    data["groups"] = _normalize_groups(
        data.get("groups", []),
        data["prompts"],
    )
    _atomic_write_json(STORE_PATH, data)


def _find_prompt(
    prompts: Iterable[Dict[str, Any]],
    group: str,
    title: str,
) -> Dict[str, Any]:
    wanted = (_clean_text(group).lower(), _clean_text(title).lower())
    for item in prompts:
        if _prompt_key(item) == wanted:
            return item
    return {}


def _filter_prompts(
    prompts: Iterable[Dict[str, Any]],
    group: str = "",
    query: str = "",
) -> List[Dict[str, Any]]:
    clean_group = _clean_text(group).lower()
    terms = [
        _clean_text(term).lower()
        for term in _clean_text(query).replace("，", " ").split()
        if _clean_text(term)
    ]
    results = []
    for item in prompts:
        if (
            clean_group
            and clean_group != "all"
            and _clean_text(item.get("group")).lower() != clean_group
        ):
            continue
        haystack = " ".join(
            [
                _clean_text(item.get("title")),
                _clean_text(item.get("group")),
                str(item.get("prompt") or ""),
                " ".join(item.get("tags", [])),
                str(item.get("note") or ""),
            ]
        ).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        results.append(item)
    return sorted(
        results,
        key=lambda value: (
            _clean_text(value.get("group")).lower(),
            _clean_text(value.get("title")).lower(),
        ),
    )


def _format_titles(prompts: Iterable[Dict[str, Any]]) -> str:
    lines = []
    for item in prompts:
        tags = ", ".join(item.get("tags", []))
        suffix = f" [{tags}]" if tags else ""
        lines.append(
            f"{item.get('group', 'default')} / "
            f"{item.get('title', 'Untitled')}{suffix}"
        )
    return "\n".join(lines)


def _parse_import_payload(import_json: str, import_path: str) -> List[Dict[str, Any]]:
    source = _clean_text(import_json)
    path = _clean_text(import_path)
    if path:
        source = Path(path).read_text(encoding="utf-8")
    if not source:
        raise ValueError("import_json or import_path is required for import_json action.")

    data = json.loads(source)
    if isinstance(data, dict):
        if isinstance(data.get("prompts"), list):
            raw_items = data["prompts"]
        elif {"title", "prompt"} & set(data):
            raw_items = [data]
        else:
            raw_items = []
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []
    return [
        _normalize_prompt(item)
        for item in raw_items
        if isinstance(item, dict)
    ]


def _merge_prompts(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
    merge_mode: str,
) -> Tuple[List[Dict[str, Any]], int, int]:
    mode = merge_mode if merge_mode in MERGE_OPTIONS else "update"
    if mode == "replace_all":
        return incoming, len(incoming), 0

    results = list(existing)
    created = 0
    updated = 0
    for item in incoming:
        index = next(
            (
                i
                for i, prompt in enumerate(results)
                if _prompt_key(prompt) == _prompt_key(item)
            ),
            -1,
        )
        if index < 0 or mode == "append":
            if mode == "append" and index >= 0:
                item["title"] = (
                    f"{item['title']} ({datetime.now().strftime('%Y%m%d%H%M%S')})"
                )
            results.append(item)
            created += 1
            continue
        if mode == "skip_existing":
            continue
        item["id"] = results[index].get("id") or item["id"]
        item["created_at"] = results[index].get("created_at") or item["created_at"]
        item["updated_at"] = _now()
        results[index] = item
        updated += 1
    return results, created, updated


def _resolve_export_path(export_path: str) -> Path:
    clean = _clean_text(export_path)
    if clean:
        path = Path(clean)
        if path.is_dir():
            filename = f"MengBao_prompts_export_{datetime.now():%Y%m%d_%H%M%S}.json"
            return path / filename
        return path
    filename = f"MengBao_prompts_export_{datetime.now():%Y%m%d_%H%M%S}.json"
    return USER_DATA_DIRECTORY / filename


def _groups_from_store(data: Dict[str, Any]) -> List[str]:
    return _normalize_groups(data.get("groups", []), data.get("prompts", []))


def _get_prompt_by_id(
    prompts: Iterable[Dict[str, Any]],
    prompt_id: str,
) -> Dict[str, Any]:
    wanted = _clean_text(prompt_id)
    for item in prompts:
        if _clean_text(item.get("id")) == wanted:
            return item
    return {}


def _delete_prompt_by_id(prompt_id: str) -> Dict[str, Any]:
    data = _load_store()
    prompts = data.get("prompts", [])
    before = len(prompts)
    data["prompts"] = [
        item
        for item in prompts
        if _clean_text(item.get("id")) != _clean_text(prompt_id)
    ]
    _save_store(data)
    return {"deleted": before - len(data["prompts"])}


def _add_group(group: str) -> Dict[str, Any]:
    clean = _clean_text(group)
    if not clean:
        raise ValueError("group is required.")
    data = _load_store()
    groups = _normalize_groups(data.get("groups", []), data.get("prompts", []))
    exists = any(item.lower() == clean.lower() for item in groups)
    if not exists:
        groups.append(clean)
    data["groups"] = groups
    _save_store(data)
    return {"created": 0 if exists else 1, "group": clean}


def _delete_group(group: str) -> Dict[str, Any]:
    clean = _clean_text(group)
    if not clean or clean.lower() == "default":
        raise ValueError("default group cannot be deleted.")
    data = _load_store()
    if any(
        _clean_text(item.get("group")).lower() == clean.lower()
        for item in data.get("prompts", [])
    ):
        raise ValueError("group is not empty. Move or delete prompts first.")
    groups = [
        item
        for item in _normalize_groups(data.get("groups", []), [])
        if item.lower() != clean.lower()
    ]
    data["groups"] = groups
    _save_store(data)
    return {"deleted": 1}


def _move_prompts(prompt_ids: Iterable[Any], target_group: str) -> Dict[str, Any]:
    target = _clean_text(target_group) or "default"
    wanted = {
        _clean_text(prompt_id)
        for prompt_id in prompt_ids
        if _clean_text(prompt_id)
    }
    if not wanted:
        raise ValueError("prompt_ids is required.")
    data = _load_store()
    moved = 0
    for item in data.get("prompts", []):
        if _clean_text(item.get("id")) in wanted:
            item["group"] = target
            item["updated_at"] = _now()
            moved += 1
    data["groups"] = _normalize_groups(
        data.get("groups", []),
        data.get("prompts", []),
    )
    _save_store(data)
    return {"moved": moved, "target_group": target}


def _upsert_prompt(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = _load_store()
    prompts = data.get("prompts", [])
    prompt_id = _clean_text(payload.get("id"))
    now = _now()
    item = _get_prompt_by_id(prompts, prompt_id) if prompt_id else {}
    if not item:
        item = _find_prompt(
            prompts,
            payload.get("group", ""),
            payload.get("title", ""),
        )

    if item:
        item.update(
            {
                "title": _clean_text(payload.get("title")) or item.get("title") or "Untitled",
                "group": _clean_text(payload.get("group")) or item.get("group") or "default",
                "prompt": str(payload.get("prompt") or ""),
                "tags": _split_tags(payload.get("tags")),
                "note": str(payload.get("note") or ""),
                "color": _clean_text(payload.get("color")) or item.get("color") or "#e25545",
                "preview_image": str(payload.get("preview_image") or ""),
                "updated_at": now,
            }
        )
        saved = item
        status = "updated"
    else:
        saved = _normalize_prompt(
            {
                **payload,
                "title": _clean_text(payload.get("title")) or "Untitled",
                "group": _clean_text(payload.get("group")) or "default",
                "created_at": now,
                "updated_at": now,
            }
        )
        prompts.append(saved)
        status = "created"

    data["prompts"] = prompts
    _save_store(data)
    return {"status": status, "prompt": saved}


def _rename_group(old_group: str, new_group: str) -> Dict[str, Any]:
    old_group = _clean_text(old_group)
    new_group = _clean_text(new_group)
    if not old_group or not new_group:
        raise ValueError("old_group and new_group are required.")

    data = _load_store()
    changed = 0
    for item in data.get("prompts", []):
        if _clean_text(item.get("group")).lower() == old_group.lower():
            item["group"] = new_group
            item["updated_at"] = _now()
            changed += 1
    groups = [
        new_group if item.lower() == old_group.lower() else item
        for item in _normalize_groups(
            data.get("groups", []),
            data.get("prompts", []),
        )
    ]
    data["groups"] = _normalize_groups(groups, data.get("prompts", []))
    _save_store(data)
    return {"changed": changed}


def _api_payload(
    prompts: List[Dict[str, Any]],
    status: str = "ok",
) -> Dict[str, Any]:
    data = _load_store()
    return {
        "status": status,
        "count": len(prompts),
        "groups": _groups_from_store(data),
        "prompts": prompts,
        "store_path": str(STORE_PATH),
    }


def _static_groups() -> List[str]:
    groups = ["all", "default"]
    try:
        for item in _load_store().get("prompts", []):
            group = _clean_text(item.get("group"))
            if group and group not in groups:
                groups.append(group)
    except Exception:
        pass
    return groups


def _static_titles() -> List[str]:
    titles = ["Untitled"]
    try:
        for item in _load_store().get("prompts", []):
            label = f"{item.get('group', 'default')} / {item.get('title', 'Untitled')}"
            if label not in titles:
                titles.append(label)
    except Exception:
        pass
    return titles


ACTION_OPTIONS = [
    "save_or_update",
    "get",
    "search",
    "list",
    "delete",
    "import_json",
    "export_json",
    "rename_group",
]
MERGE_OPTIONS = ["update", "append", "skip_existing", "replace_all"]
