import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from test_history import png_bytes
from test_mengbao_image_api_nodes import PACKAGE_NAME

try:
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
except ImportError:
    web = None


@unittest.skipIf(web is None, "aiohttp is supplied by ComfyUI")
class HistoryRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        module = importlib.import_module(f"{PACKAGE_NAME}.api.history_routes")
        store_module = importlib.import_module(f"{PACKAGE_NAME}.utils.history_store")
        self.store = store_module.HistoryStore(Path(self.directory.name) / "history")
        self.record_id = self.store.start("gpt-image-2", "测试产品", {"size": "auto"}, 1)
        self.store.finish(self.record_id, [png_bytes()], "")
        routes = web.RouteTableDef()
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes))
        with patch.dict(sys.modules, server=fake_server), patch.object(module, "_ROUTES_REGISTERED", False), patch.object(module, "HISTORY_STORE", self.store):
            module.register_history_routes()
            module.register_history_routes()
            self.assertEqual(len(routes), 3)
        storage_patch = patch.object(module, "HISTORY_STORE", self.store)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        application = web.Application()
        application.add_routes(routes)
        self.client = TestClient(TestServer(application))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_list_detail_original_thumbnail_download_and_errors(self):
        response = await self.client.get("/mengbao_history/items?query=产品&state=success")
        payload = await response.json()
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["total"], 1)
        response = await self.client.get(f"/mengbao_history/item/{self.record_id}")
        self.assertEqual((await response.json())["image_count"], 1)
        for suffix in ("", "?thumbnail=1", "?download=1"):
            response = await self.client.get(f"/mengbao_history/file/{self.record_id}/0{suffix}")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "image/png")
            self.assertTrue((await response.read()).startswith(b"\x89PNG"))
            if "download" in suffix:
                self.assertIn("attachment", response.headers["Content-Disposition"])
        for path in ("/mengbao_history/items?state=invalid", "/mengbao_history/items?limit=x",
                     "/mengbao_history/file/invalid/0", f"/mengbao_history/file/{self.record_id}/-1"):
            response = await self.client.get(path)
            self.assertEqual(response.status, 400)
            self.assertIn("message", (await response.json())["error"])
        response = await self.client.get(f"/mengbao_history/file/{self.record_id}/999")
        self.assertEqual(response.status, 404)


if __name__ == "__main__":
    unittest.main()
