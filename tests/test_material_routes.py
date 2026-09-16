import importlib
import sys
import types
import unittest
from unittest.mock import patch

from test_material_library import PACKAGE, image_bytes

try:
    from aiohttp import FormData, web
    from aiohttp.test_utils import TestClient, TestServer
except ImportError:
    web = None


@unittest.skipIf(web is None, "aiohttp is supplied by ComfyUI")
class MaterialRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import tempfile
        from pathlib import Path

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        store_module = importlib.import_module(f"{PACKAGE}.utils.material_store")
        self.store = store_module.MaterialStore(Path(self.directory.name) / "materials")
        module = importlib.import_module(f"{PACKAGE}.api.material_routes")
        routes = web.RouteTableDef()
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes))
        with patch.dict(sys.modules, server=fake_server), patch.object(module, "MATERIAL_STORE", self.store), patch.object(module, "_ROUTES_REGISTERED", False):
            module.register_material_routes()
            self.assertEqual(len(routes), 7)
            module.register_material_routes()
            self.assertEqual(len(routes), 7)
        # 路由闭包读取模块中的存储对象，测试只绑定临时目录，不接触用户素材。
        self.storage_patch = patch.object(module, "MATERIAL_STORE", self.store)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        application = web.Application(client_max_size=34 * 1024 * 1024)
        application.add_routes(routes)
        self.client = TestClient(TestServer(application))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def import_image(self, content=None):
        form = FormData()
        form.add_field("category", "产品")
        form.add_field("image", content or image_bytes(), filename="reference.png", content_type="image/png")
        response = await self.client.post("/mengbao_materials/import", data=form)
        return response, await response.json()

    async def test_import_list_preview_update_and_delete(self):
        response, item = await self.import_image()
        self.assertEqual(response.status, 200)
        material_id = item["id"]
        response = await self.client.get("/mengbao_materials/items")
        self.assertEqual((await response.json())["items"][0]["id"], material_id)
        response = await self.client.get(f"/mengbao_materials/item/{material_id}")
        self.assertEqual((await response.json())["width"], 8)
        response = await self.client.get(f"/mengbao_materials/file/{material_id}?thumbnail=1")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Content-Type"], "image/png")
        self.assertTrue((await response.read()).startswith(b"\x89PNG"))
        response = await self.client.post(f"/mengbao_materials/item/{material_id}", json={"name": "updated", "favorite": True})
        self.assertTrue((await response.json())["favorite"])
        response = await self.client.get("/mengbao_materials/items?favorites=1&query=UPDATED")
        self.assertEqual(len((await response.json())["items"]), 1)
        response = await self.client.delete(f"/mengbao_materials/item/{material_id}")
        self.assertTrue((await response.json())["deleted"])
        response = await self.client.get(f"/mengbao_materials/file/{material_id}")
        self.assertEqual(response.status, 404)

    async def test_category_actions_and_validation(self):
        for body in ({"action": "add", "name": "新品"}, {"action": "rename", "current": "新品", "name": "春季"}, {"action": "delete", "name": "春季"}):
            response = await self.client.post("/mengbao_materials/category", json=body)
            self.assertEqual(response.status, 200)
        for body in ([], {"action": "unsupported"}, {"action": "delete", "name": "未分类"}):
            response = await self.client.post("/mengbao_materials/category", json=body)
            self.assertEqual(response.status, 400)
        response = await self.client.get("/mengbao_materials/file/invalid")
        self.assertEqual(response.status, 400)

    async def test_invalid_uploads_do_not_create_materials(self):
        response, payload = await self.import_image(b"invalid image")
        self.assertEqual(response.status, 400)
        self.assertIn("message", payload["error"])
        self.assertEqual(self.store.list_items()["items"], [])
        form = FormData()
        form.add_field("category", "x" * 200)
        form.add_field("image", image_bytes(), filename="test.png")
        response = await self.client.post("/mengbao_materials/import", data=form)
        self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
