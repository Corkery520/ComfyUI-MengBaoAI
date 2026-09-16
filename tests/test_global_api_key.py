import asyncio
import importlib
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mengbao_global_key_test"
spec = importlib.util.spec_from_file_location(
    PACKAGE_NAME, PLUGIN_ROOT / "__init__.py",
    submodule_search_locations=[str(PLUGIN_ROOT)],
)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load MengBaoAI package from {PLUGIN_ROOT}")
node_pack = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE_NAME] = node_pack
spec.loader.exec_module(node_pack)
auth = importlib.import_module(f"{PACKAGE_NAME}.api.auth")


class GlobalAPIKeyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = self.root / "user" / ".env"
        for name, value in (
            ("ENV_PATH", self.env),
            ("USER_DATA_DIRECTORY", self.env.parent),
            ("LEGACY_ENV_PATHS", (self.root / "legacy.env",)),
        ):
            patcher = patch.object(auth, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_global_node_has_only_one_key_field_and_safe_status_output(self):
        node_class = node_pack.NODE_CLASS_MAPPINGS["MengBaoGlobalAPIKey"]
        self.assertEqual(node_pack.NODE_DISPLAY_NAME_MAPPINGS["MengBaoGlobalAPIKey"], "萌宝AI全局API Key管理")
        self.assertEqual(list(node_class.INPUT_TYPES()["required"]), ["api_key"])
        self.assertEqual(node_class.RETURN_TYPES, ("STRING",))
        self.assertEqual(node_class.RETURN_NAMES, ("status",))
        self.assertEqual(node_class.CATEGORY, "萌宝AI/工具")
        node = node_class()
        self.assertEqual(node.get_status("not-saved-input")["ui"]["saved"], [False])
        self.assertFalse(self.env.exists())
        auth.save_api_key("test-global-secret")
        result = node.get_status("")
        self.assertEqual(result["ui"]["saved"], [True])
        self.assertNotIn("test-global-secret", str(result))
        self.assertEqual(auth.connection_key("", ""), "test-global-secret")
        self.assertEqual(auth.connection_key("", "node-override"), "node-override")

    def test_clear_does_not_delete_other_env_settings_or_resurrect_legacy_key(self):
        self.env.parent.mkdir(parents=True)
        self.env.write_text("OTHER_SETTING=keep\nMENGBAO_API_KEY=test-global-secret\n", encoding="utf-8")
        (self.root / "legacy.env").write_text("MENGBAO_API_KEY=legacy-secret\n", encoding="utf-8")
        auth.clear_api_key()
        self.assertEqual(auth.read_saved_api_key(), "")
        self.assertEqual(auth.connection_key("", ""), "")
        self.assertEqual(auth.connection_key("", "node-override"), "node-override")
        self.assertEqual(self.env.read_text(encoding="utf-8"), "OTHER_SETTING=keep\nMENGBAO_API_KEY=\n")
        auth.clear_api_key()
        self.assertEqual(auth.read_saved_api_key(), "")

    def test_save_replaces_duplicate_key_entries_and_clear_removes_the_secrets(self):
        self.env.parent.mkdir(parents=True)
        self.env.write_text("MENGBAO_API_KEY=old-secret\n# Keep this comment\nMENGBAO_API_KEY=duplicate-secret\n", encoding="utf-8")
        auth.save_api_key("replacement-secret")
        content = self.env.read_text(encoding="utf-8")
        self.assertEqual(content.count("MENGBAO_API_KEY="), 1)
        self.assertNotIn("old-secret", content)
        self.assertNotIn("duplicate-secret", content)
        auth.clear_api_key()
        self.assertNotIn("replacement-secret", self.env.read_text(encoding="utf-8"))

    def test_empty_store_still_migrates_if_it_does_not_have_a_key_entry(self):
        self.env.parent.mkdir(parents=True)
        self.env.write_text("OTHER_SETTING=keep\n", encoding="utf-8")
        (self.root / "legacy.env").write_text("MENGBAO_API_KEY=legacy-secret\n", encoding="utf-8")
        self.assertEqual(auth.read_saved_api_key(), "legacy-secret")
        self.assertIn("OTHER_SETTING=keep", self.env.read_text(encoding="utf-8"))

    def test_failed_clear_keeps_the_previously_saved_key(self):
        auth.save_api_key("original-test-secret")
        with patch.object(Path, "replace", side_effect=OSError("Disk write failed")):
            with self.assertRaisesRegex(OSError, "Disk write failed"):
                auth.clear_api_key()
        self.assertEqual(auth.read_saved_api_key(), "original-test-secret")

    def test_routes_support_save_status_and_delete_without_returning_the_key(self):
        handlers = {}

        class Routes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)
            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)
            def delete(self, path):
                return lambda handler: handlers.setdefault(("DELETE", path), handler)

        class Request:
            async def json(self):
                return {"api_key": "route-test-secret"}

        def json_response(payload, status=200):
            return {"payload": payload, "status": status}

        modules = {
            "aiohttp": types.SimpleNamespace(web=types.SimpleNamespace(json_response=json_response)),
            "server": types.SimpleNamespace(PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=Routes()))),
        }
        with patch.dict(sys.modules, modules), patch.object(auth, "_ROUTES_REGISTERED", False):
            auth.register_image_routes()
        path = "/mengbao_image_api/api_key"
        saved = asyncio.run(handlers[("POST", path)](Request()))
        self.assertEqual(saved, {"payload": {"saved": True}, "status": 200})
        status = asyncio.run(handlers[("GET", path)](None))
        self.assertEqual(status["payload"], {"saved": True})
        cleared = asyncio.run(handlers[("DELETE", path)](None))
        self.assertEqual(cleared, {"payload": {"saved": False}, "status": 200})
        self.assertEqual(auth.read_saved_api_key(), "")
        with patch.object(auth, "clear_api_key", side_effect=OSError("Disk write failed")):
            failed = asyncio.run(handlers[("DELETE", path)](None))
        self.assertEqual(failed["status"], 500)
        self.assertEqual(failed["payload"]["error"]["message"], "Disk write failed")


if __name__ == "__main__":
    unittest.main()
