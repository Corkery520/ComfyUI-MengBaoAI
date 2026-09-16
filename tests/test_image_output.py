import ast
import importlib
import importlib.util
import json
import os
import random
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
from PIL import Image
from PIL.PngImagePlugin import PngInfo


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "mengbao_image_output_test"
spec = importlib.util.spec_from_file_location(PACKAGE, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
pack = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = pack
spec.loader.exec_module(pack)
module = importlib.import_module(f"{PACKAGE}.nodes.image_tools.image_output")


class NativeSaveSpy:
    calls = []

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "filename_prefix": ("STRING", {"default": "ComfyUI"})},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}

    def save_images(self, **kwargs):
        self.calls.append(kwargs)
        return {"ui": {"images": [{"filename": "saved.png", "subfolder": "", "type": "output"}]}}


class NativePreviewSpy(NativeSaveSpy):
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",)}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}

    def save_images(self, **kwargs):
        result = super().save_images(**kwargs)
        result["ui"]["images"][0]["type"] = "temp"
        return result


class ImageOutputTests(unittest.TestCase):
    def setUp(self):
        NativeSaveSpy.calls.clear()
        self.native = types.SimpleNamespace(SaveImage=NativeSaveSpy, PreviewImage=NativePreviewSpy)
        self.patch = patch.dict(sys.modules, nodes=self.native)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_nodes_keep_native_inputs_and_add_optional_prompt_input(self):
        for node_id, title in (("MengBaoSaveImage", "萌宝AI·保存图片"), ("MengBaoPreviewImage", "萌宝AI·预览图片")):
            node = pack.NODE_CLASS_MAPPINGS[node_id]
            self.assertEqual(pack.NODE_DISPLAY_NAME_MAPPINGS[node_id], title)
            self.assertTrue(node.OUTPUT_NODE)
            self.assertEqual(node.RETURN_TYPES, ())
            self.assertTrue(node.INPUT_TYPES()["optional"]["generation_prompt"][1]["forceInput"])
            self.assertEqual(node.INPUT_TYPES()["hidden"]["unique_id"], "UNIQUE_ID")
        self.assertEqual(set(module.MengBaoSaveImage.INPUT_TYPES()["required"]), {"images", "filename_prefix"})
        self.assertEqual(set(module.MengBaoPreviewImage.INPUT_TYPES()["required"]), {"images"})
        self.assertNotIn("generation_prompt", NativeSaveSpy.INPUT_TYPES().get("optional", {}))

    def test_save_and_preview_delegate_without_rewriting_images_or_metadata(self):
        images = torch.zeros((1, 2, 4, 4))
        graph = {"9": {"class_type": "MengBaoSaveImage", "inputs": {"images": ["1", 0]}},
                 "1": {"class_type": "WANGImageAPI", "inputs": {"prompt": "actual prompt", "api_key": "private-value"}}}
        metadata = {"workflow": {"nodes": []}}
        result = module.MengBaoSaveImage().save_images(images, "prefix", prompt=graph, extra_pnginfo=metadata, unique_id="9")
        self.assertIs(NativeSaveSpy.calls[0]["images"], images)
        self.assertIs(NativeSaveSpy.calls[0]["prompt"], graph)
        self.assertIs(NativeSaveSpy.calls[0]["extra_pnginfo"], metadata)
        self.assertEqual(NativeSaveSpy.calls[0]["filename_prefix"], "prefix")
        self.assertEqual(result["ui"]["images"][0]["type"], "output")
        self.assertEqual(result["ui"]["mengbao_prompt_candidates"][0]["text"], "actual prompt")
        self.assertNotIn("private-value", json.dumps(result))
        result = module.MengBaoPreviewImage().save_images(images, generation_prompt="explicit prompt")
        self.assertEqual(result["ui"]["images"][0]["type"], "temp")
        self.assertNotIn("filename_prefix", NativeSaveSpy.calls[-1])

    def test_explicit_executed_prompt_has_priority_and_preserves_text(self):
        text = "  connected text\nsecond line  "
        self.assertEqual(module._prompt_candidates({}, "9", text)[0]["text"], text)

    def test_traces_image_ancestors_but_stops_before_generator_references(self):
        graph = {
            "9": {"class_type": "MengBaoPreviewImage", "inputs": {"images": ["8", 0]}},
            "8": {"class_type": "MengBaoImageConstraint", "inputs": {"image": ["1", 0]}},
            "1": {"class_type": "WANGImageAPI", "inputs": {"prompt": "correct prompt", "image_1": ["2", 0]}},
            "2": {"class_type": "WANGImageAPI", "inputs": {"prompt": "reference prompt"}},
            "3": {"class_type": "WANGImageAPI", "inputs": {"prompt": "unrelated prompt"}},
        }
        candidates = module._prompt_candidates(graph, "9", "")
        self.assertEqual([item["text"] for item in candidates], ["correct prompt"])
        self.assertEqual(module._prompt_candidates(graph, "missing", ""), [])

    def test_extracts_positive_clip_text_but_not_negative_text(self):
        graph = {
            "9": {"class_type": "MengBaoSaveImage", "inputs": {"images": ["8", 0]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0]}},
            "7": {"class_type": "KSampler", "inputs": {"positive": ["4", 0], "negative": ["5", 0]}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "positive image prompt"}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "negative text"}},
        }
        self.assertEqual([item["text"] for item in module._prompt_candidates(graph, "9", "")], ["positive image prompt"])

    def test_ambiguous_sources_stay_separate_and_cycles_are_bounded(self):
        graph = {
            "9": {"class_type": "MengBaoSaveImage", "inputs": {"images": ["8", 0]}},
            "8": {"class_type": "MengBaoSmartCollage", "inputs": {"image_1": ["1", 0], "image_2": ["2", 0], "image_3": ["8", 0]}},
            "1": {"class_type": "WANGImageAPI", "inputs": {"prompt": "first"}},
            "2": {"class_type": "WANGImageAPI", "inputs": {"prompt": "second"}},
        }
        self.assertEqual({item["text"] for item in module._prompt_candidates(graph, "9", "")}, {"first", "second"})
        graph["1"]["inputs"]["prompt"] = ["3", 1]
        graph["3"] = {"class_type": "WANGPromptOrganizer", "inputs": {"action": "save_or_update", "prompt": "wrong output slot"}}
        self.assertEqual([item["text"] for item in module._prompt_candidates(graph, "9", "")], ["second"])

    def test_actual_comfyui_classes_preserve_alpha_files_and_png_metadata(self):
        comfy_root = Path(os.environ.get("COMFYUI_ROOT", Path(sys.executable).resolve().parents[1]))
        source_path = comfy_root / "nodes.py"
        if not source_path.is_file():
            self.skipTest("Actual ComfyUI nodes.py is not available")
        parsed = ast.parse(source_path.read_text(encoding="utf-8"))
        definitions = [node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name in {"SaveImage", "PreviewImage"}]
        with tempfile.TemporaryDirectory(prefix="mengbao-output-test-") as directory:
            output = Path(directory) / "output"
            temporary = Path(directory) / "temp"
            output.mkdir(); temporary.mkdir()
            paths = types.SimpleNamespace(get_output_directory=lambda: str(output), get_temp_directory=lambda: str(temporary),
                get_save_image_path=lambda prefix, folder, width, height: (folder, prefix, 1, "", prefix))
            namespace = {"folder_paths": paths, "Image": Image, "np": np, "json": json, "os": os, "random": random,
                         "PngInfo": PngInfo, "args": types.SimpleNamespace(disable_metadata=False)}
            exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source_path), "exec"), namespace)
            actual_native = types.SimpleNamespace(SaveImage=namespace["SaveImage"], PreviewImage=namespace["PreviewImage"])
            image = torch.ones((1, 4, 8, 4))
            image[..., 3] = 0.5
            graph = {"9": {"class_type": "MengBaoSaveImage", "inputs": {}}}
            with patch.dict(sys.modules, nodes=actual_native):
                saved = module.MengBaoSaveImage().save_images(image, "alpha", prompt=graph, extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9")
                previewed = module.MengBaoPreviewImage().save_images(image)
            with Image.open(output / saved["ui"]["images"][0]["filename"]) as result:
                self.assertEqual(result.mode, "RGBA")
                self.assertEqual(result.size, (8, 4))
                self.assertEqual(result.getpixel((0, 0))[3], 127)
                self.assertEqual(json.loads(result.info["prompt"]), graph)
                self.assertEqual(json.loads(result.info["workflow"]), {"nodes": []})
            self.assertTrue((temporary / previewed["ui"]["images"][0]["filename"]).is_file())
            self.assertEqual(previewed["ui"]["images"][0]["type"], "temp")


if __name__ == "__main__":
    unittest.main()
