import importlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
import torch
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
NAME = "mengbao_replica_test"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
pack = importlib.util.module_from_spec(spec)
sys.modules[NAME] = pack
spec.loader.exec_module(pack)
vision = importlib.import_module(f"{NAME}.api.vision_client")
replica = importlib.import_module(f"{NAME}.utils.replica")
storage = importlib.import_module(f"{NAME}.utils.replica_store")
nodes = importlib.import_module(f"{NAME}.nodes.ecommerce.replica")
generate = importlib.import_module(f"{NAME}.nodes.image_api.generate")


def png(width=80, height=60, color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()


def response(status=200, body=None):
    body = body if body is not None else {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]}
    result = Mock(status_code=status, reason="Service Unavailable" if status == 503 else "Error", ok=status < 400)
    result.json.return_value = body
    result.text = json.dumps(body)
    return result


def analysis():
    return {"composition": "Centered product and headline", "elements": [
        {"id": "p1", "kind": "product", "name": "Product", "box": {"x": .1, "y": .2, "w": .4, "h": .6}, "description": "Old bottle", "productGroup": "g1"},
        {"id": "label", "kind": "text", "name": "Label", "box": {"x": .2, "y": .4, "w": .2, "h": .1}, "text": "OLD BRAND", "parentId": "p1"},
        {"id": "title", "kind": "text", "name": "Headline", "box": {"x": .1, "y": .01, "w": .8, "h": .15}, "text": "Original", "textStyle": "Red bold"},
    ]}


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.key = patch.object(vision, "read_saved_api_key", return_value="private-test-key")
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_primary_success(self):
        with patch.object(vision.requests, "post", return_value=response()) as post:
            result = vision.run_vision("Analyze", [png()], json.loads)
        self.assertEqual(result["model"], "gem-3.7-flash")
        self.assertEqual(post.call_count, 1)
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 180)
        self.assertEqual(kwargs["json"]["contents"][0]["parts"][1]["inlineData"]["mimeType"], "image/png")

    def test_connection_timeout_rate_limit_and_server_failure_switch_once(self):
        for error in (requests.ConnectionError("Connection refused"), requests.Timeout("Read timed out"), response(429), response(503), response(404, {"error": {"code": "model_not_found"}})):
            with self.subTest(error=str(error)), patch.object(vision.requests, "post", side_effect=[error, response()]) as post:
                result = vision.run_vision("Analyze", [png()], json.loads)
                self.assertEqual(result["model"], "gem-3.8-flash")
                self.assertEqual(post.call_count, 2)
                self.assertEqual(post.call_args_list[0].kwargs["json"], post.call_args_list[1].kwargs["json"])

    def test_fatal_errors_do_not_fallback(self):
        for error in (response(401), response(403), response(400), response(429, {"error": {"code": "insufficient_balance"}}), response(502, {"error": {"status": "INVALID_ARGUMENT"}}), response(503, {"error": {"code": "content_policy_violation"}}), response(200, {"promptFeedback": {"blockReason": "SAFETY"}}), response(200, {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]})):
            with self.subTest(error=str(error)), patch.object(vision.requests, "post", return_value=error) as post:
                with self.assertRaises(Exception):
                    vision.run_vision("Analyze", [png()], json.loads)
                self.assertEqual(post.call_count, 1)

    def test_both_errors_are_preserved_and_key_is_redacted(self):
        with patch.object(vision.requests, "post", side_effect=[requests.ConnectionError("Primary private-test-key"), requests.Timeout("Backup timeout")]) as post:
            with self.assertRaises(vision.VisionError) as caught:
                vision.run_vision("Analyze", [png()], json.loads)
        self.assertEqual(post.call_count, 2)
        self.assertIn("gem-3.7-flash", str(caught.exception))
        self.assertIn("gem-3.8-flash", str(caught.exception))
        self.assertNotIn("private-test-key", str(caught.exception))

    def test_missing_key_and_cancel_do_not_call_api(self):
        with patch.object(vision, "read_saved_api_key", return_value=""), patch.object(vision.requests, "post") as post:
            with self.assertRaises(ValueError):
                vision.run_vision("Analyze", [png()], json.loads)
            post.assert_not_called()

    def test_cancel_after_primary_response_prevents_backup(self):
        cancelled = Mock(side_effect=[False, False, True])
        with patch.object(vision.requests, "post", return_value=response(503)) as post:
            with self.assertRaises(InterruptedError):
                vision.run_vision("Analyze", [png()], json.loads, cancelled=cancelled)
            self.assertEqual(post.call_count, 1)
        with patch.object(vision.requests, "post") as post:
            with self.assertRaises(InterruptedError):
                vision.run_vision("Analyze", [png()], json.loads, cancelled=lambda: True)
            post.assert_not_called()


class ReplicaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = storage.ReplicaStore(Path(self.directory.name))
        self.asset = self.store.put_asset(png(), "source.png")
        self.record = {"id": "a" * 32, "source": self.asset, "analysis": replica.parse_analysis(analysis()), "model": "gem-3.7-flash"}

    def draft(self):
        return {"analysis_id": self.record["id"], "analysis": self.record["analysis"], "replacements": {}, "confirmed": True}

    def test_parser_clips_boundary_but_does_not_guess_pixel_units(self):
        value = analysis()
        value["elements"][0]["box"] = {"x": .8, "y": .2, "w": .4, "h": .6}
        parsed = replica.parse_analysis(value)
        self.assertEqual(parsed["elements"][0]["boxStatus"], "clipped")
        value["elements"][0]["box"] = {"x": 80, "y": 20, "w": 40, "h": 60}
        self.assertIsNone(replica.parse_analysis(value)["elements"][0]["box"])

    def test_duplicate_ids_invalid_parent_and_truncated_json_are_rejected(self):
        for change in (lambda a: a["elements"][1].update(id="p1"), lambda a: a["elements"][1].update(parentId="missing")):
            value = analysis()
            change(value)
            with self.assertRaises(ValueError):
                replica.parse_analysis(value)
        with self.assertRaises(ValueError):
            replica.parse_analysis('{"elements":[')
        self.assertEqual(len(replica.parse_analysis("```json\n" + json.dumps(analysis()) + "\n```" )["elements"]), 3)

    def test_references_order_parent_inheritance_and_proportions(self):
        product = self.store.put_asset(png(31, 93, "blue"), "product.png")
        draft = self.draft()
        draft["replacements"] = {"p1": {"mode": "replace", "images": [product["id"], product["id"]], "description": "Blue bottle"}, "title": {"mode": "replace", "text": "NEW"}}
        result = replica.compile_settings(self.record, draft, self.store)
        self.assertEqual(result["references"], [self.asset["id"], product["id"]])
        self.assertIn("OLD BRAND", result["forbiddenCopy"])
        self.assertEqual(result["expectedCopy"], [{"id": "title", "text": "NEW"}])
        self.assertIn("@图片2", result["prompt"])
        self.assertIn("禁止横向拉宽", result["prompt"])
        self.assertEqual((self.store.asset(product["id"])["width"], self.store.asset(product["id"])["height"]), (31, 93))

    def test_unconfirmed_stale_pending_text_and_empty_replacement_are_rejected(self):
        for change in (lambda d: d.update(confirmed=False), lambda d: d.update(analysis_id="b" * 32), lambda d: d["analysis"]["elements"][2].update(text=""), lambda d: d["replacements"].update(p1={"mode": "replace"})):
            draft = self.draft()
            change(draft)
            with self.assertRaises(ValueError):
                replica.compile_settings(self.record, draft, self.store)

    def test_store_rejects_traversal_and_restores_drafts(self):
        with self.assertRaises(ValueError):
            self.store.asset("../../outside")
        self.store.save_draft("b" * 32, self.draft())
        self.assertEqual(storage.ReplicaStore(Path(self.directory.name)).draft("b" * 32)["analysis_id"], self.record["id"])

    def test_analysis_is_manual_cached_and_binds_token_to_source(self):
        node = nodes.MengBaoImageReverse()
        tensor = torch.zeros((1, 60, 80, 3))
        with patch.object(nodes, "REPLICA_STORE", self.store), patch.object(nodes, "run_vision", return_value={"data": replica.parse_analysis(analysis()), "model": "gem-3.8-flash", "attempts": []}) as call:
            with self.assertRaises(ValueError):
                node.analyze(tensor, "")
            first = node.analyze(tensor, "c" * 32)
            second = node.analyze(tensor, "c" * 32)
            self.assertEqual(first["result"][0], second["result"][0])
            self.assertEqual(first["result"][0]["model"], "gem-3.8-flash")
            self.assertEqual(call.call_count, 1)
            with self.assertRaises(ValueError):
                node.analyze(torch.ones_like(tensor), "c" * 32)
            with self.assertRaises(ValueError):
                node.analyze(torch.zeros((2, 60, 80, 3)), "d" * 32)
            self.assertEqual(call.call_count, 1)

    def test_audit_failure_keeps_image(self):
        tensor = torch.zeros((1, 4, 8, 3))
        with patch.object(nodes, "run_vision", side_effect=RuntimeError("HTTP 503 Service Unavailable")):
            result = nodes.MengBaoReplicaAudit().audit(tensor, {"expectedCopy": [], "forbiddenCopy": []})
        self.assertIs(result["result"][0], tensor)
        self.assertIn("HTTP 503 Service Unavailable", result["result"][1])

    def test_audit_checks_each_image_and_reports_mismatches_without_regeneration(self):
        tensor = torch.zeros((2, 4, 8, 3))
        report = {"matches": False, "missingTexts": ["NEW"], "changedTexts": [], "residualTexts": ["OLD"], "note": ""}
        with patch.object(nodes, "run_vision", return_value={"data": report, "model": "gem-3.7-flash", "attempts": []}) as call:
            result = nodes.MengBaoReplicaAudit().audit(tensor, {"expectedCopy": [], "forbiddenCopy": []})
        self.assertIs(result["result"][0], tensor)
        self.assertEqual(call.call_count, 2)
        self.assertEqual([item["image"] for item in json.loads(result["result"][1])], [1, 2])

    def test_deleted_elements_are_removed_from_generation_and_audit_old_copy(self):
        draft = self.draft()
        draft["analysis"] = replica.parse_analysis(analysis())
        draft["analysis"]["elements"] = [item for item in draft["analysis"]["elements"] if item["id"] != "title"]
        result = replica.compile_settings(self.record, draft, self.store)
        self.assertIn('"action":"remove"', result["prompt"])
        self.assertIn("Original", result["forbiddenCopy"])

    def test_new_nodes_and_locales_are_registered(self):
        for name in ("MengBaoImageReverse", "MengBaoImageReplicaSettings", "MengBaoReplicaAudit"):
            self.assertIn(name, pack.NODE_CLASS_MAPPINGS)
            for language in ("en", "zh"):
                data = json.loads((ROOT / "locales" / language / "nodeDefs.json").read_text(encoding="utf-8"))
                self.assertIn(name, data)
        self.assertEqual(pack.NODE_CLASS_MAPPINGS["WANGImageAPI"].INPUT_TYPES()["optional"]["replica_settings"][0], "MENGBAO_REPLICA_SETTINGS")

    def test_generation_uses_original_references_and_source_ratio_for_all_models(self):
        product = self.store.put_asset(png(31, 93, "blue"))
        draft = self.draft()
        draft["replacements"] = {"p1": {"mode": "replace", "images": [product["id"]]}}
        settings = replica.compile_settings(self.record, draft, self.store)
        for model in generate.MODEL_TYPES:
            cls = pack.NODE_CLASS_MAPPINGS["WANGImageAPI"]
            arguments = {name: definition[1]["default"] for name, definition in cls.INPUT_TYPES()["required"].items()}
            arguments.update(api_key="private-test-key", model_type=model, prompt=settings["prompt"], replica_settings=settings)
            with self.subTest(model=model), patch.object(generate, "REPLICA_STORE", self.store), patch.object(generate, "HISTORY_STORE") as history, patch.object(generate, "_call_media_api", return_value={}) as call, patch.object(generate, "_extract_images", return_value=([torch.zeros(1, 4, 8, 3)], [])):
                history.start.return_value = None
                cls().generate(**arguments)
                sent = call.call_args.kwargs
                sizes = [Image.open(io.BytesIO(content)).size for content in sent["reference_images"]]
                self.assertEqual(sizes, [(80, 60), (31, 93)])
                ratio = sent["params"].get("aspect_ratio") or sent["params"].get("aspectRatio")
                if model == "gpt-image-2":
                    self.assertEqual(sent["params"]["size"], "1280x960")
                else:
                    self.assertEqual(ratio, "4:3")
                    if model == "gpt-image-2.5":
                        self.assertEqual(sent["params"]["resolution"], "1K")
                with self.assertRaises(ValueError):
                    cls().generate(**arguments, image_1=torch.zeros(1, 4, 8, 3))
                too_many = {**settings, "references": [self.asset["id"]] * 17}
                arguments["replica_settings"] = too_many
                with self.assertRaises(ValueError):
                    cls().generate(**arguments)

    def test_edited_position_requires_explicit_confirmation(self):
        draft = self.draft()
        draft["analysis"]["elements"][0]["boxStatus"] = "pending"
        with self.assertRaises(ValueError):
            replica.compile_settings(self.record, draft, self.store)

    def test_failed_analysis_is_not_automatically_retried(self):
        with patch.object(nodes, "REPLICA_STORE", self.store), patch.object(nodes, "run_vision", side_effect=RuntimeError("HTTP 503 Service Unavailable")) as call:
            for _ in range(2):
                with self.assertRaises(Exception):
                    nodes.MengBaoImageReverse().analyze(torch.zeros((1, 60, 80, 3)), "f" * 32)
            self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
