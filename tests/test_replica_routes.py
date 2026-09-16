import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

from test_replica import NAME, analysis, png, replica, storage


class ReplicaRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.module = importlib.import_module(f"{NAME}.api.replica_routes")
        self.store = storage.ReplicaStore(Path(self.directory.name))
        self.asset = self.store.put_asset(png(), "source.png")
        self.record = {"id": "a" * 32, "source": self.asset, "analysis": replica.parse_analysis(analysis()), "model": "gem-3.8-flash"}
        self.store.begin(self.record["id"], "source")
        self.store.complete(self.record["id"], self.record)
        routes = web.RouteTableDef()
        self.events = Mock()
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes, send_sync=self.events))
        with patch.dict(sys.modules, server=fake_server), patch.object(self.module, "_REGISTERED", False):
            self.module.register_replica_routes()
            self.module.register_replica_routes()
            self.assertEqual(len(routes), 7)
        storage_patch = patch.object(self.module, "REPLICA_STORE", self.store)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        app = web.Application()
        app.add_routes(routes)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_cached_analysis_assets_and_capabilities(self):
        result = await self.client.get(f"/mengbao_replica/analysis/{self.record['id']}")
        self.assertEqual((await result.json())["model"], "gem-3.8-flash")
        result = await self.client.get(f"/mengbao_replica/assets/{self.asset['id']}/file")
        self.assertEqual(result.status, 200)
        self.assertTrue((await result.read()).startswith(b"\x89PNG"))
        result = await self.client.get("/mengbao_replica/capabilities")
        self.assertEqual((await result.json())["gpt-image-2.5"], 16)
        for path in ("/mengbao_replica/analysis/invalid", "/mengbao_replica/assets/invalid/file"):
            result = await self.client.get(path)
            self.assertEqual(result.status, 400)
            self.assertIn("message", (await result.json())["error"])

    async def test_upload_preserves_dimensions_and_validates_type(self):
        form = FormData()
        form.add_field("image", png(31, 93, "blue"), filename="product.png", content_type="image/png")
        result = await self.client.post("/mengbao_replica/assets", data=form)
        asset = await result.json()
        self.assertEqual(result.status, 200)
        self.assertEqual((asset["width"], asset["height"]), (31, 93))
        form = FormData()
        form.add_field("image", b"not an image", filename="image.png", content_type="image/png")
        result = await self.client.post("/mengbao_replica/assets", data=form)
        self.assertEqual(result.status, 400)

    async def test_draft_confirmation_rejects_pending_position_and_restores(self):
        draft_id = "b" * 32
        draft = {"analysis_id": self.record["id"], "analysis": self.record["analysis"], "replacements": {}, "confirmed": True}
        draft["analysis"]["elements"][0]["boxStatus"] = "pending"
        result = await self.client.post(f"/mengbao_replica/drafts/{draft_id}", json=draft)
        self.assertEqual(result.status, 400)
        self.assertIn("Confirm the position", (await result.json())["error"]["message"])
        self.assertEqual(self.store.draft(draft_id), {})
        draft["analysis"]["elements"][0]["boxStatus"] = "valid"
        result = await self.client.post(f"/mengbao_replica/drafts/{draft_id}", json=draft)
        self.assertEqual(result.status, 200)
        result = await self.client.get(f"/mengbao_replica/drafts/{draft_id}")
        self.assertEqual(await result.json(), draft)

    async def test_description_is_cached_and_reports_backup_status(self):
        body = {"request_id": "c" * 32, "client_id": "replica-test", "element": {"kind": "product", "name": "Bottle"}, "images": [self.asset["id"]]}

        def fake_vision(_prompt, _images, _parse, **options):
            options["on_stage"]({"stage": "requesting", "model": "gem-3.8-flash", "previous_error": "HTTP 503 Service Unavailable"})
            return {"data": "Blue bottle", "model": "gem-3.8-flash", "attempts": [{"model": "gem-3.8-flash", "success": True}]}

        with patch.object(self.module, "run_vision", side_effect=fake_vision) as vision:
            for _ in range(2):
                result = await self.client.post("/mengbao_replica/describe", json=body)
                self.assertEqual(result.status, 200)
                self.assertEqual((await result.json())["model"], "gem-3.8-flash")
            self.assertEqual(vision.call_count, 1)
            self.events.assert_called_once()
            self.assertEqual(self.events.call_args.args[1]["request_id"], body["request_id"])
            body["description"] = "Changed request"
            result = await self.client.post("/mengbao_replica/describe", json=body)
            self.assertEqual(result.status, 400)
            self.assertEqual(vision.call_count, 1)
            body["element"]["kind"] = "text"
            result = await self.client.post("/mengbao_replica/describe", json=body)
            self.assertEqual(result.status, 400)
        result = await self.client.post("/mengbao_replica/describe", json=[])
        self.assertEqual(result.status, 400)


if __name__ == "__main__":
    unittest.main()
