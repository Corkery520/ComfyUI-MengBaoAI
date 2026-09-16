import hashlib
import io
import json
import re
import threading
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from ..api.auth import USER_DATA_DIRECTORY
from .material_store import MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES, SUPPORTED_FORMATS


_LOCK = threading.RLock()


def identity(value, length=32):
    if not re.fullmatch(rf"[0-9a-f]{{{length}}}", str(value or "")):
        raise ValueError("Invalid replica resource ID")
    return value


class ReplicaStore:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, kind, resource_id, extension="json"):
        identity(resource_id, 64 if kind == "assets" else 32)
        root = self.root.resolve()
        path = (root / kind / f"{resource_id}.{extension}").resolve()
        if root not in path.parents:
            raise ValueError("Replica resource is outside the user directory")
        return path

    def _write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        content = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
        temporary.write_bytes(content)
        temporary.replace(path)

    def _read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def put_asset(self, content, name="image.png"):
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Image file must be between 1 byte and 32 MB")
        try:
            with Image.open(io.BytesIO(content)) as original:
                if original.format not in SUPPORTED_FORMATS:
                    raise ValueError("Supported image formats: PNG, JPEG, WebP, BMP")
                if original.width * original.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image exceeds the 100 megapixel limit")
                image = ImageOps.exif_transpose(original).convert("RGBA")
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                canonical = buffer.getvalue()
                width, height = image.size
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Invalid or unsupported image file") from exc
        if len(canonical) > MAX_UPLOAD_BYTES:
            raise ValueError("Decoded PNG exceeds the 32 MB limit")
        asset_id = hashlib.sha256(canonical).hexdigest()
        asset = {"id": asset_id, "name": str(name).replace("\\", "/").rsplit("/", 1)[-1][:180], "width": width, "height": height,
                 "url": f"/mengbao_replica/assets/{asset_id}/file"}
        with _LOCK:
            if not self._path("assets", asset_id).exists():
                self._write(self._path("assets", asset_id, "png"), canonical)
                self._write(self._path("assets", asset_id), asset)
            return self.asset(asset_id)

    def asset(self, asset_id):
        with _LOCK:
            return self._read(self._path("assets", asset_id))

    def asset_path(self, asset_id):
        self.asset(asset_id)
        path = self._path("assets", asset_id, "png")
        if not path.is_file():
            raise FileNotFoundError("Replica image file is missing")
        return path

    def asset_bytes(self, asset_id):
        return self.asset_path(asset_id).read_bytes()

    def begin(self, request_id, fingerprint):
        with _LOCK:
            path = self._path("requests", request_id)
            if path.exists():
                request = self._read(path)
                if request["fingerprint"] != fingerprint:
                    raise ValueError("Source changed. Click Analyze Image again before generating")
                if request["status"] == "completed":
                    return request["result"]
                if request["status"] == "failed":
                    raise ValueError(request["error"])
                raise ValueError("Replica request is already running. Re-analyze with a new request if it was interrupted")
            self._write(path, {"fingerprint": fingerprint, "status": "running"})
            return None

    def complete(self, request_id, result):
        with _LOCK:
            path = self._path("requests", request_id)
            record = self._read(path)
            self._write(path, {**record, "status": "completed", "result": result})

    def fail(self, request_id, error):
        with _LOCK:
            path = self._path("requests", request_id)
            record = self._read(path)
            self._write(path, {**record, "status": "failed", "error": str(error)})

    def analysis(self, request_id):
        request = self._read(self._path("requests", request_id))
        if request.get("status") != "completed" or "analysis" not in request.get("result", {}):
            raise ValueError(request.get("error") or "Replica analysis is not ready")
        return request["result"]

    def save_draft(self, draft_id, draft):
        if not isinstance(draft, dict) or len(json.dumps(draft).encode("utf-8")) > 1024 * 1024:
            raise ValueError("Replica draft must be a JSON object under 1 MB")
        with _LOCK:
            self._write(self._path("drafts", draft_id), draft)

    def draft(self, draft_id):
        path = self._path("drafts", draft_id)
        with _LOCK:
            return self._read(path) if path.exists() else {}


REPLICA_STORE = ReplicaStore(USER_DATA_DIRECTORY / "replication")
