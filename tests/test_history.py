import importlib
import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from test_mengbao_image_api_nodes import PACKAGE_NAME, node_module


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGBA", (24, 12), (20, 40, 60, 128)).save(buffer, "PNG")
    return buffer.getvalue()


class HistoryTests(unittest.TestCase):
    def setUp(self):
        module = importlib.import_module(f"{PACKAGE_NAME}.utils.history_store")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = module.HistoryStore(Path(self.directory.name) / "history")

    def png(self):
        return png_bytes()

    def test_persistence_original_alpha_progress_and_filters(self):
        item = self.store.start("gpt-image-2", "产品摄影 Spring", {"size": "auto"}, 2)
        self.store.progress(item, 46)
        self.store.progress(item, 20)
        running = self.store.list_items(state="running")["items"][0]
        self.assertEqual(running["progress"], 46)
        self.store.finish(item, [self.png(), self.png()], "")
        reloaded = type(self.store)(self.store.root)
        payload = reloaded.list_items(query="SPRING", state="success")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["counts"]["success"], 1)
        record = reloaded.get_item(item)
        self.assertEqual(len(record["images"]), 2)
        self.assertEqual(record["progress"], 100)
        with Image.open(reloaded.file_path(item, 0)) as image:
            self.assertEqual(image.size, (24, 12))
            self.assertEqual(image.getpixel((0, 0))[3], 128)
        self.assertTrue(reloaded.file_path(item, 1, thumbnail=True).is_file())
        self.assertEqual(reloaded.list_items(query="not found")["total"], 0)

    def test_failure_partial_pagination_and_safe_paths(self):
        failed = self.store.start("nano-banana-2", "first", {}, 1)
        self.store.finish(failed, [], "HTTP 429: Too Many Requests")
        partial = self.store.start("gpt-image-2.5", "second", {}, 2)
        self.store.finish(partial, [self.png()], "Image download failed")
        self.assertEqual(self.store.get_item(failed)["state"], "failed")
        self.assertEqual(self.store.get_item(failed)["error"], "HTTP 429: Too Many Requests")
        self.assertEqual(self.store.get_item(partial)["state"], "partial")
        self.assertEqual(len(self.store.list_items(limit=1, offset=1)["items"]), 1)
        for record_id, index in (("../index", 0), (partial, -1), (partial, 5)):
            with self.assertRaises((ValueError, FileNotFoundError)):
                self.store.file_path(record_id, index)
        with self.assertRaises(ValueError):
            self.store.list_items(state="invalid")

    def test_concurrent_tasks_do_not_lose_records(self):
        def generate(index):
            item = self.store.start("gpt-image-2", str(index), {}, 1)
            self.store.finish(item, [self.png()], "")
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(generate, range(8)))
        self.assertEqual(self.store.list_items()["counts"]["success"], 8)

    def test_restart_recovery_and_invalid_archive_do_not_stay_running(self):
        interrupted = self.store.start("gpt-image-2", "restart", {}, 1)
        self.store.recover_interrupted()
        self.assertEqual(self.store.get_item(interrupted)["state"], "failed")
        failed_archive = self.store.start("gpt-image-2", "invalid archive", {}, 1)
        with self.assertRaises(Exception):
            self.store.finish(failed_archive, [b"invalid png"], "")
        self.assertEqual(self.store.get_item(failed_archive)["state"], "failed")
        self.assertEqual(self.store.list_items(state="running")["total"], 0)

    def arguments(self):
        return {name: settings[1]["default"] for name, settings in
                node_module.MengBaoImageAPI.INPUT_TYPES()["required"].items()}

    def test_node_records_result_and_never_saves_key_or_error_image(self):
        arguments = self.arguments()
        arguments.update(api_key="history-test-secret", prompt="产品摄影", batch_size=2)
        tensor = node_module._png_bytes_to_image_tensor(self.png())
        payloads = [{"state": "success"}, {"error": {"message": "HTTP 403 history-test-secret"}}]
        with patch.object(node_module, "HISTORY_STORE", self.store), patch.object(
            node_module, "_call_media_api", side_effect=payloads
        ), patch.object(node_module, "_extract_images", side_effect=[([tensor], []), ([], [])]):
            result = node_module.MengBaoImageAPI().generate(**arguments)
        self.assertEqual(len(result["result"]), 3)
        record = self.store.list_items()["items"][0]
        self.assertEqual(record["state"], "partial")
        self.assertEqual(record["image_count"], 1)
        self.assertNotIn("history-test-secret", str(record))
        with patch.object(node_module, "HISTORY_STORE", self.store), patch.object(
            node_module, "_call_media_api", side_effect=OSError("HTTP 500")
        ):
            arguments.update(api_key="test", batch_size=1)
            node_module.MengBaoImageAPI().generate(**arguments)
        record = self.store.list_items()["items"][0]
        self.assertEqual(record["state"], "failed")
        self.assertEqual(record["image_count"], 0)

    def test_history_storage_failure_does_not_break_generation(self):
        arguments = self.arguments()
        arguments.update(api_key="test")
        tensor = node_module._png_bytes_to_image_tensor(self.png())
        with patch.object(node_module, "_call_media_api", return_value={}), patch.object(
            node_module, "_extract_images", return_value=([tensor], [])
        ), patch.object(node_module, "HISTORY_STORE") as store:
            store.start.side_effect = OSError("Disk full")
            result = node_module.MengBaoImageAPI().generate(**arguments)
        self.assertEqual(result["result"][0].shape, tensor.shape)

    def test_extraction_exception_finishes_record_and_keeps_original_error(self):
        arguments = self.arguments()
        arguments.update(api_key="test")
        with patch.object(node_module, "HISTORY_STORE", self.store), patch.object(
            node_module, "_call_media_api", return_value={}
        ), patch.object(node_module, "_extract_images", side_effect=RuntimeError("Image decode failed")):
            with self.assertRaisesRegex(RuntimeError, "Image decode failed"):
                node_module.MengBaoImageAPI().generate(**arguments)
        self.assertEqual(self.store.list_items()["counts"]["failed"], 1)


if __name__ == "__main__":
    unittest.main()
