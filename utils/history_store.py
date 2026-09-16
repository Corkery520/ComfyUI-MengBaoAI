import io
import json
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .prompt_store import USER_DATA_DIRECTORY


STATES = ("running", "success", "partial", "failed")
_LOCK = threading.RLock()


class HistoryStore:
    def __init__(self, root):
        self.root = Path(root)

    @contextmanager
    def _connection(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.root / "history.sqlite3", timeout=30)
        connection.row_factory = sqlite3.Row
        # SQLite 事务避免同时执行多个生成节点时覆盖记录，不把图片存进数据库。
        try:
            with connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    model TEXT NOT NULL, prompt TEXT NOT NULL, params TEXT NOT NULL,
                    requested_count INTEGER NOT NULL, state TEXT NOT NULL,
                    progress INTEGER NOT NULL, error TEXT NOT NULL, images TEXT NOT NULL)""")
                yield connection
        finally:
            connection.close()

    def _validate_id(self, record_id):
        if not re.fullmatch(r"[0-9a-f]{32}", str(record_id or "")):
            raise ValueError("Invalid history ID")

    def _item(self, row):
        if row is None:
            raise FileNotFoundError("History record does not exist")
        item = dict(row)
        item["params"] = json.loads(item["params"])
        item["images"] = json.loads(item["images"])
        item["image_count"] = len(item["images"])
        return item

    def start(self, model, prompt, params, requested_count):
        record_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with _LOCK, self._connection() as connection:
            connection.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, now, now, str(model), str(prompt), json.dumps(params, ensure_ascii=False),
                 int(requested_count), "running", 1, "", "[]"))
        return record_id

    def progress(self, record_id, percent):
        self._validate_id(record_id)
        with _LOCK, self._connection() as connection:
            connection.execute("UPDATE records SET progress = MAX(progress, ?), updated_at = ? WHERE id = ? AND state = 'running'",
                (max(1, min(99, int(percent))), datetime.now(timezone.utc).isoformat(), record_id))

    def finish(self, record_id, images, error):
        self._validate_id(record_id)
        metadata = []
        written = []
        with _LOCK:
            if self.get_item(record_id)["state"] != "running":
                raise ValueError("History record has already finished")
            try:
                for index, content in enumerate(images):
                    image_path = self._path(record_id, index)
                    thumb_path = self._path(record_id, index, True)
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    thumb_path.parent.mkdir(parents=True, exist_ok=True)
                    written.extend((image_path, thumb_path))
                    with Image.open(io.BytesIO(content)) as image:
                        image.load()
                        metadata.append({"index": index, "width": image.width, "height": image.height})
                        # 保留原始 PNG 字节和 Alpha，缩略图仅用于历史面板预览。
                        image_path.write_bytes(content)
                        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                        image.save(thumb_path, "PNG")
                state = "partial" if metadata and error else "success" if metadata else "failed"
                with self._connection() as connection:
                    connection.execute("UPDATE records SET state = ?, progress = 100, error = ?, images = ?, updated_at = ? WHERE id = ?",
                        (state, str(error or ""), json.dumps(metadata), datetime.now(timezone.utc).isoformat(), record_id))
            except Exception:
                for path in written:
                    path.unlink(missing_ok=True)
                with self._connection() as connection:
                    connection.execute("UPDATE records SET state = 'failed', progress = 100, error = ? WHERE id = ?",
                        ("History image archive failed", record_id))
                raise

    def recover_interrupted(self):
        if not (self.root / "history.sqlite3").is_file():
            return
        with _LOCK, self._connection() as connection:
            connection.execute("UPDATE records SET state = 'failed', progress = 100, error = ? WHERE state = 'running'",
                ("Generation interrupted by a ComfyUI restart",))

    def get_item(self, record_id):
        self._validate_id(record_id)
        with _LOCK, self._connection() as connection:
            return self._item(connection.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone())

    def list_items(self, query="", state="", limit=60, offset=0, oldest=False):
        if state and state not in STATES:
            raise ValueError("Invalid history state")
        limit, offset = max(1, min(100, int(limit))), max(0, int(offset))
        conditions, arguments = [], []
        if query:
            conditions.append("(instr(lower(prompt), lower(?)) > 0 OR instr(lower(model), lower(?)) > 0 OR instr(id, ?) > 0)")
            arguments.extend([str(query).strip()] * 3)
        if state:
            conditions.append("state = ?")
            arguments.append(state)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with _LOCK, self._connection() as connection:
            counts = dict.fromkeys(STATES, 0)
            counts.update({row["state"]: row["count"] for row in connection.execute("SELECT state, COUNT(*) AS count FROM records GROUP BY state")})
            total = connection.execute("SELECT COUNT(*) FROM records" + where, arguments).fetchone()[0]
            order = "ASC" if oldest else "DESC"
            rows = connection.execute("SELECT * FROM records" + where + f" ORDER BY created_at {order}, rowid {order} LIMIT ? OFFSET ?",
                (*arguments, limit, offset)).fetchall()
            return {"items": [self._item(row) for row in rows], "total": total, "counts": counts}

    def _path(self, record_id, index, thumbnail=False):
        self._validate_id(record_id)
        if isinstance(index, bool) or int(index) < 0:
            raise ValueError("Invalid history image index")
        root = self.root.resolve()
        path = (root / ("thumbnails" if thumbnail else "images") / f"{record_id}-{int(index)}.png").resolve()
        if root not in path.parents:
            raise ValueError("History file is outside the history directory")
        return path

    def file_path(self, record_id, index, thumbnail=False):
        path = self._path(record_id, index, thumbnail)
        with _LOCK:
            item = self.get_item(record_id)
            if int(index) >= len(item["images"]) or not path.is_file():
                raise FileNotFoundError("History image file is missing")
        return path


HISTORY_STORE = HistoryStore(USER_DATA_DIRECTORY / "history")
