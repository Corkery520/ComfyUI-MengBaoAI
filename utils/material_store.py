import io
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .prompt_store import USER_DATA_DIRECTORY


MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 100_000_000
DEFAULT_CATEGORIES = ["角色", "产品", "参考", "背景", "字体", "白底", "未分类"]
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}
_STORE_LOCK = threading.RLock()


def _category_name(value):
    value = str(value or "").strip()
    if not value or len(value) > 40 or re.search(r'[<>:"/\\|?*\x00-\x1f]', value) or value in {".", ".."}:
        raise ValueError("Invalid material category name")
    return value


def _material_name(value):
    value = str(value or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not value or len(value) > 180 or any(ord(character) < 32 for character in value):
        raise ValueError("Invalid material name")
    return value


class MaterialStore:
    def __init__(self, root):
        self.root = Path(root)
        self.index_path = self.root / "index.json"

    def _read(self):
        if not self.index_path.is_file():
            return {"version": 1, "categories": list(DEFAULT_CATEGORIES), "items": []}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError("Material library index is invalid") from exc
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("categories"), list) or not isinstance(data.get("items"), list):
            raise ValueError("Material library index is invalid")
        return data

    def _write(self, data):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f"index-{uuid.uuid4().hex}.tmp"
        try:
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.index_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _find(self, data, material_id):
        if not re.fullmatch(r"[0-9a-f]{32}", str(material_id or "")):
            raise ValueError("Invalid material ID")
        item = next((item for item in data["items"] if item["id"] == material_id), None)
        if item is None:
            raise FileNotFoundError("Material does not exist")
        return item

    def _path(self, material_id, thumbnail=False):
        if not re.fullmatch(r"[0-9a-f]{32}", str(material_id or "")):
            raise ValueError("Invalid material ID")
        root = self.root.resolve()
        path = (root / ("thumbnails" if thumbnail else "images") / f"{material_id}.png").resolve()
        if root not in path.parents:
            raise ValueError("Material file is outside the library directory")
        return path

    def list_items(self, category="", query="", favorites_only=False):
        with _STORE_LOCK:
            data = self._read()
            query = str(query or "").strip().casefold()
            items = [dict(item) for item in data["items"] if (
                (not category or item["category"] == category)
                and (not favorites_only or item.get("favorite", False))
                and (not query or query in f"{item['name']} {item['category']}".casefold())
            )]
            return {"categories": list(data["categories"]), "items": list(reversed(items))}

    def get_item(self, material_id):
        with _STORE_LOCK:
            return dict(self._find(self._read(), material_id))

    def file_path(self, material_id, thumbnail=False):
        with _STORE_LOCK:
            self._find(self._read(), material_id)
            path = self._path(material_id, thumbnail)
            if not path.is_file():
                raise FileNotFoundError("Material image file is missing")
            return path

    def import_image(self, content, name, category="未分类"):
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Image file must be between 1 byte and 32 MB")
        name = _material_name(name)
        category = _category_name(category)
        try:
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in SUPPORTED_FORMATS:
                    raise ValueError("Supported image formats: PNG, JPEG, WebP, BMP")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image exceeds the 100 megapixel limit")
                # 原图保留 Alpha 通道和比例，缩略图仅用于浏览，不替代实际输出。
                source = ImageOps.exif_transpose(source)
                image = source.convert("RGBA" if "A" in source.getbands() or "transparency" in source.info else "RGB")
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise ValueError("Invalid or unsupported image file") from exc
        with _STORE_LOCK:
            data = self._read()
            if category not in data["categories"]:
                raise ValueError("Material category does not exist")
            material_id = uuid.uuid4().hex
            path = self._path(material_id)
            thumbnail_path = self._path(material_id, thumbnail=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            item = {
                "id": material_id, "name": name, "category": category, "favorite": False,
                "width": image.width, "height": image.height,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            try:
                image.save(path, format="PNG")
                thumbnail = image.copy()
                thumbnail.thumbnail((512, 512), Image.Resampling.LANCZOS)
                thumbnail.save(thumbnail_path, format="PNG")
                data["items"].append(item)
                self._write(data)
            except Exception:
                path.unlink(missing_ok=True)
                thumbnail_path.unlink(missing_ok=True)
                raise
            return dict(item)

    def update_item(self, material_id, **changes):
        if set(changes) - {"name", "category", "favorite"}:
            raise ValueError("Unsupported material update field")
        with _STORE_LOCK:
            data = self._read()
            item = self._find(data, material_id)
            if "name" in changes:
                item["name"] = _material_name(changes["name"])
            if "category" in changes:
                category = _category_name(changes["category"])
                if category not in data["categories"]:
                    raise ValueError("Material category does not exist")
                item["category"] = category
            if "favorite" in changes:
                if not isinstance(changes["favorite"], bool):
                    raise ValueError("favorite must be a boolean")
                item["favorite"] = changes["favorite"]
            self._write(data)
            return dict(item)

    def delete_item(self, material_id):
        with _STORE_LOCK:
            data = self._read()
            self._find(data, material_id)
            paths = [self._path(material_id), self._path(material_id, thumbnail=True)]
            data["items"] = [item for item in data["items"] if item["id"] != material_id]
            self._write(data)
            for path in paths:
                path.unlink(missing_ok=True)

    def add_category(self, name):
        name = _category_name(name)
        with _STORE_LOCK:
            data = self._read()
            if name.casefold() in {category.casefold() for category in data["categories"]}:
                raise ValueError("Material category already exists")
            data["categories"].insert(max(0, len(data["categories"]) - 1), name)
            self._write(data)

    def rename_category(self, current, name):
        name = _category_name(name)
        with _STORE_LOCK:
            data = self._read()
            if current == "未分类" or current not in data["categories"]:
                raise ValueError("Material category cannot be edited")
            if name.casefold() in {category.casefold() for category in data["categories"] if category != current}:
                raise ValueError("Material category already exists")
            data["categories"] = [name if category == current else category for category in data["categories"]]
            for item in data["items"]:
                if item["category"] == current:
                    item["category"] = name
            self._write(data)

    def delete_category(self, name):
        with _STORE_LOCK:
            data = self._read()
            if name == "未分类" or name not in data["categories"]:
                raise ValueError("Material category cannot be deleted")
            # 删除分类只将素材移到未分类，不连带删除用户原图。
            for item in data["items"]:
                if item["category"] == name:
                    item["category"] = "未分类"
            data["categories"].remove(name)
            self._write(data)


MATERIAL_STORE = MaterialStore(USER_DATA_DIRECTORY / "materials")
