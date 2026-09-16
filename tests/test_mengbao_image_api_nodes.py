import base64
import importlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mengbao_node_pack_test"


def load_node_pack():
    package_spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    if package_spec is None or package_spec.loader is None:
        raise ImportError(f"Cannot load MengBao node pack from {PLUGIN_ROOT}")
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[PACKAGE_NAME] = package
    package_spec.loader.exec_module(package)
    return package


node_pack = load_node_pack()
node_module = importlib.import_module(f"{PACKAGE_NAME}.nodes.image_api.generate")
auth_module = importlib.import_module(f"{PACKAGE_NAME}.api.auth")
image_utils = importlib.import_module(f"{PACKAGE_NAME}.utils.image")


class FakeResponse:
    def __init__(self, payload, status_code=200, url="https://api.lk888.ai/test", content=b""):
        self._payload = payload
        self.status_code = status_code
        self.url = url
        self.content = content
        self.reason = "OK" if status_code < 400 else "Bad Request"

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class MengBaoImageAPITests(unittest.TestCase):
    def test_node_pack_centralizes_mappings_and_keeps_legacy_id(self):
        expected_ids = {
            "WANGImageAPI",
            "ImageGridSplit",
            "ImageFreeCrop",
            "ImageGridTilePicker",
            "WANGPromptOrganizer",
            "WANGPromptReader",
            "MengBaoEcommerceSettings",
            "MengBaoSmartCollage",
            "MengBaoImageConstraint",
            "MengBaoLoadImage",
            "MengBaoMaterialLibrary",
            "MengBaoSaveImage",
            "MengBaoPreviewImage",
            "MengBaoGlobalAPIKey",
            "MengBaoImageReverse",
            "MengBaoImageReplicaSettings",
            "MengBaoReplicaAudit",
        }
        self.assertEqual(set(node_pack.NODE_CLASS_MAPPINGS), expected_ids)
        self.assertEqual(
            node_pack.NODE_DISPLAY_NAME_MAPPINGS["WANGImageAPI"],
            "萌宝AI·图像生成",
        )
        self.assertEqual(
            set(node_pack.NODE_CLASS_MAPPINGS),
            set(node_pack.NODE_DISPLAY_NAME_MAPPINGS),
        )
        self.assertEqual(node_pack.WEB_DIRECTORY, "./web")
        for node_class in node_pack.NODE_CLASS_MAPPINGS.values():
            self.assertTrue(node_class.CATEGORY.startswith("萌宝AI/"))

    def test_connection_key_accepts_json_in_visible_api_key_field(self):
        connection = '{"_type":"newapi_channel_conn","key":"json-key"}'
        self.assertEqual(node_module._provided_connection_key("", connection), "json-key")
        self.assertEqual(
            node_module._provided_connection_key('{"key":"legacy-key"}', connection),
            "json-key",
        )
        self.assertEqual(
            node_module._provided_connection_key('{"key":"legacy-key"}', ""),
            "legacy-key",
        )

    def test_balance_request_uses_bearer_authentication(self):
        response = FakeResponse({"data": {"balance": 18.75}})
        with patch.object(node_module.requests, "get", return_value=response) as get_mock:
            payload = node_module._fetch_balance("test-key", timeout=12)

        self.assertEqual(payload, {"data": {"balance": 18.75}})
        get_mock.assert_called_once_with(
            "https://api.lk888.ai/api/v1/skills/balance",
            headers={"Authorization": "Bearer test-key"},
            timeout=12,
        )

    def test_transparent_background_augments_gpt_prompt_once(self):
        encoded = base64.b64encode(self._png_bytes()).decode("ascii")
        transparent_instruction = (
            "精确提取当前图片主体，仅移除主体外背景，输出带真实 Alpha 通道的透明 PNG。"
            "禁止绘制棋盘格、马赛克、白底或其他模拟透明背景。"
        )

        for model_type in ("gpt-image-2", "gpt-image-2.5"):
            with self.subTest(model_type=model_type):
                progress_updates = []

                class FakeProgressBar:
                    def __init__(self, total):
                        self.total = total

                    def update_absolute(self, value, total):
                        progress_updates.append((value, total))

                with patch.object(
                    node_module,
                    "_call_media_api",
                    return_value={"data": [{"b64_json": encoded}]},
                ) as api_mock, patch.object(
                    node_module,
                    "ComfyProgressBar",
                    FakeProgressBar,
                ):
                    result = node_module.MengBaoImageAPI().generate(
                        prompt="产品摄影",
                        connection_json="",
                        api_key="test-key",
                        model_type=model_type,
                        batch_size=1,
                        tt2_size="auto",
                        tt2_aspect_ratio="1:1",
                        tt2_resolution="1K",
                        tt2_background="transparent",
                        tt2_quality="auto",
                        tt25_version="flare",
                        tt25_aspect_ratio="1:1",
                        tt25_resolution="1K",
                        tt25_quality="auto",
                        tt25_background="transparent",
                        banana2_aspect_ratio="1:1",
                        banana2_image_size="1K",
                        banana2_thinking_level="minimal",
                        banana_pro_aspect_ratio="1:1",
                        banana_pro_image_size="1K",
                        timeout=30,
                        retries=0,
                        ui_language="zh",
                    )

                sent_prompt = api_mock.call_args.kwargs["prompt"]
                sent_params = api_mock.call_args.kwargs["params"]
                self.assertEqual(result["ui"], {"mengbao_balance_refresh": [True]})
                self.assertEqual(len(result["result"]), 3)
                self.assertEqual(progress_updates, [(1, 100), (100, 100)])
                self.assertEqual(sent_prompt.count(transparent_instruction), 1)
                self.assertTrue(sent_prompt.startswith("产品摄影"))
                if model_type == "gpt-image-2.5":
                    self.assertEqual(sent_params["background"], "transparent")
                else:
                    self.assertNotIn("background", sent_params)

    def test_reference_inputs_expand_to_each_model_limit(self):
        self.assertEqual(node_module.DEFAULT_REFERENCE_IMAGE_COUNT, 3)
        optional_inputs = node_module.MengBaoImageAPI.INPUT_TYPES()["optional"]
        self.assertEqual(
            list(optional_inputs),
            [f"image_{index}" for index in range(1, 17)] + ["replica_settings"],
        )

        encoded = base64.b64encode(self._png_bytes()).decode("ascii")
        reference = node_module.torch.zeros((1, 1, 1, 3), dtype=node_module.torch.float32)
        reference_inputs = {f"image_{index}": reference for index in range(1, 17)}
        expected_limits = {
            "gpt-image-2": 14,
            "gpt-image-2.5": 16,
            "nano-banana-2": 14,
            "nano-banana-2-pro": 14,
        }

        for model_type, expected_limit in expected_limits.items():
            with self.subTest(model_type=model_type):
                with patch.object(
                    node_module,
                    "_call_media_api",
                    return_value={"data": [{"b64_json": encoded}]},
                ) as api_mock, patch.object(
                    image_utils,
                    "image_tensor_to_png_bytes",
                    return_value=b"reference",
                ) as encode_mock:
                    node_module.MengBaoImageAPI().generate(
                        prompt="产品摄影",
                        connection_json="",
                        api_key="test-key",
                        model_type=model_type,
                        batch_size=1,
                        tt2_size="auto",
                        tt2_aspect_ratio="1:1",
                        tt2_resolution="1K",
                        tt2_background="opaque",
                        tt2_quality="auto",
                        tt25_version="flare",
                        tt25_aspect_ratio="1:1",
                        tt25_resolution="1K",
                        tt25_quality="auto",
                        tt25_background="opaque",
                        banana2_aspect_ratio="1:1",
                        banana2_image_size="1K",
                        banana2_thinking_level="minimal",
                        banana_pro_aspect_ratio="1:1",
                        banana_pro_image_size="1K",
                        timeout=30,
                        retries=0,
                        ui_language="zh",
                        **reference_inputs,
                    )

                self.assertEqual(encode_mock.call_count, expected_limit)
                self.assertEqual(
                    len(api_mock.call_args.kwargs["reference_images"]),
                    expected_limit,
                )

    def test_reference_inputs_after_default_count_are_not_duplicated(self):
        encoded = base64.b64encode(self._png_bytes()).decode("ascii")
        reference = node_module.torch.zeros((1, 1, 1, 3), dtype=node_module.torch.float32)

        with patch.object(
            node_module,
            "_call_media_api",
            return_value={"data": [{"b64_json": encoded}]},
        ) as api_mock, patch.object(
            image_utils,
            "image_tensor_to_png_bytes",
            return_value=b"reference",
        ) as encode_mock:
            node_module.MengBaoImageAPI().generate(
                prompt="产品摄影",
                connection_json="",
                api_key="test-key",
                model_type="gpt-image-2.5",
                batch_size=1,
                tt2_size="auto",
                tt2_aspect_ratio="auto",
                tt2_resolution="auto",
                tt2_background="opaque",
                tt2_quality="auto",
                tt25_version="flare",
                tt25_aspect_ratio="auto",
                tt25_resolution="auto",
                tt25_quality="auto",
                tt25_background="opaque",
                banana2_aspect_ratio="1:1",
                banana2_image_size="1K",
                banana2_thinking_level="minimal",
                banana_pro_aspect_ratio="1:1",
                banana_pro_image_size="1K",
                timeout=30,
                retries=0,
                ui_language="zh",
                image_4=reference,
                image_6=reference,
            )

        self.assertEqual(encode_mock.call_count, 2)
        self.assertEqual(len(api_mock.call_args.kwargs["reference_images"]), 2)

    def test_tt_image_2_combines_aspect_ratio_and_resolution(self):
        inputs = node_module.MengBaoImageAPI.INPUT_TYPES()["required"]
        self.assertEqual(inputs["tt2_aspect_ratio"][1]["default"], "auto")
        self.assertEqual(inputs["tt2_resolution"][1]["default"], "auto")
        self.assertEqual(inputs["tt2_background"][1]["default"], "opaque")

        params = node_module._build_model_params(
            "gpt-image-2",
            "auto",
            "auto",
            "flare",
            "1:1",
            "1K",
            "auto",
            "opaque",
            "1:1",
            "1K",
            "minimal",
            "1:1",
            "1K",
            tt2_aspect_ratio="9:16",
            tt2_resolution="2K",
            tt2_background="transparent",
        )
        self.assertEqual(params["size"], "1440x2560")
        self.assertNotIn("background", params)

    def test_locale_files_cover_all_inputs_and_outputs(self):
        plugin_root = PLUGIN_ROOT
        expected_inputs = set(node_module.MengBaoImageAPI.INPUT_TYPES()["required"])
        expected_inputs.update(node_module.MengBaoImageAPI.INPUT_TYPES()["optional"])

        expected = {
            "en": {
                "display_name": "MengBao AI · Image Generation",
                "outputs": ["Images", "Response", "Failed URLs"],
            },
            "zh": {
                "display_name": "萌宝AI·图像生成",
                "outputs": ["图像", "响应文本", "失败 URL"],
            },
        }
        for language, labels in expected.items():
            locale_path = plugin_root / "locales" / language / "nodeDefs.json"
            with locale_path.open("r", encoding="utf-8") as locale_file:
                node_def = json.load(locale_file)["WANGImageAPI"]

            self.assertEqual(node_def["display_name"], labels["display_name"])
            self.assertTrue(node_def["description"])
            self.assertEqual(set(node_def["inputs"]), expected_inputs)
            self.assertEqual(
                [node_def["outputs"][str(index)]["name"] for index in range(3)],
                labels["outputs"],
            )

    def test_ui_language_input_and_error_titles_are_localized(self):
        inputs = node_module.MengBaoImageAPI.INPUT_TYPES()["required"]
        self.assertEqual(inputs["ui_language"][1]["default"], "en")
        self.assertEqual(node_module._normalize_ui_language("zh-CN"), "zh")
        self.assertEqual(node_module._normalize_ui_language("fr"), "en")
        self.assertEqual(
            node_module._message_image_title("zh"),
            "萌宝AI·图像生成未收到图片",
        )
        self.assertEqual(
            node_module._message_image_title("en"),
            "MengBao AI · Image Generation did not receive an image",
        )

    def test_tt_image_2_uses_canonical_auto_and_accepts_legacy_label(self):
        inputs = node_module.MengBaoImageAPI.INPUT_TYPES()["required"]
        self.assertEqual(inputs["tt2_size"][1]["default"], "auto")

        params = node_module._build_model_params(
            "gpt-image-2",
            "自动",
            "auto",
            "flare",
            "1:1",
            "1K",
            "auto",
            "opaque",
            "1:1",
            "1K",
            "minimal",
            "1:1",
            "1K",
        )
        self.assertEqual(params["size"], "auto")

    def test_frontend_models_map_to_documented_api_models(self):
        self.assertEqual(
            node_module.MODEL_TYPES,
            [
                "gpt-image-2",
                "gpt-image-2.5",
                "nano-banana-2",
                "nano-banana-2-pro",
            ],
        )
        self.assertEqual(
            {name: config["api_model"] for name, config in node_module.MODEL_CONFIGS.items()},
            {
                "gpt-image-2": "tt-image-2",
                "gpt-image-2.5": "tt-image-2.5",
                "nano-banana-2": "banana-2",
                "nano-banana-2-pro": "banana-pro",
            },
        )

        inputs = node_module.MengBaoImageAPI.INPUT_TYPES()["required"]
        self.assertEqual(inputs["model_type"][1]["default"], "gpt-image-2")
        self.assertEqual(inputs["tt25_aspect_ratio"][1]["default"], "auto")
        self.assertEqual(inputs["tt25_resolution"][1]["default"], "auto")
        self.assertEqual(inputs["timeout"][1]["default"], 600)

    def test_node_search_aliases_include_current_brand_name(self):
        brand_aliases = {
            "Meng",
            "MengBao",
            "MengBaoAI",
            "MengBao AI",
            "萌宝",
            "萌宝AI",
        }
        for node_id, node_class in node_pack.NODE_CLASS_MAPPINGS.items():
            with self.subTest(node_id=node_id):
                aliases = set(node_class.SEARCH_ALIASES)
                self.assertTrue(brand_aliases.issubset(aliases))
                self.assertIn(node_id, aliases)

        image_aliases = node_module.MengBaoImageAPI.SEARCH_ALIASES
        self.assertIn("MengBao-Image-API", image_aliases)
        self.assertIn("萌宝图像 API", image_aliases)

        bilingual_feature_aliases = {
            "WANGImageAPI": ("MengBaoAI Image Generation", "萌宝AI 图像生成"),
            "ImageGridSplit": ("MengBaoAI Image Split", "萌宝AI 图片拆分"),
            "ImageFreeCrop": ("MengBaoAI Image Crop", "萌宝AI 自由裁剪"),
            "ImageGridTilePicker": (
                "MengBaoAI Grid Tile Picker",
                "萌宝AI 网格选图",
            ),
            "MengBaoLoadImage": (
                "MengBaoAI Load Image",
                "萌宝AI 加载图片",
            ),
            "WANGPromptOrganizer": (
                "MengBaoAI Prompt Organizer",
                "萌宝AI 提示词整理器",
            ),
            "WANGPromptReader": (
                "MengBaoAI Prompt Reader",
                "萌宝AI 提示词读取",
            ),
            "MengBaoEcommerceSettings": (
                "MengBao AI Ecommerce Settings",
                "萌宝AI 电商设置",
            ),
            "MengBaoSmartCollage": (
                "MengBao AI Smart Collage",
                "萌宝AI 智能拼图",
            ),
            "MengBaoImageConstraint": (
                "MengBao AI Image Constraint",
                "萌宝 图像约束",
            ),
        }
        for node_id, expected_aliases in bilingual_feature_aliases.items():
            with self.subTest(node_id=node_id):
                aliases = node_pack.NODE_CLASS_MAPPINGS[node_id].SEARCH_ALIASES
                for alias in expected_aliases:
                    self.assertIn(alias, aliases)

    def test_saved_api_key_uses_local_env_without_exposing_it(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_path = Path(temporary_directory) / ".env"
            env_path.write_text("OTHER_SETTING=keep\n", encoding="utf-8")
            with patch.object(auth_module, "ENV_PATH", env_path), patch.object(
                auth_module,
                "USER_DATA_DIRECTORY",
                env_path.parent,
            ), patch.object(auth_module, "LEGACY_ENV_PATHS", ()):
                auth_module.save_api_key("test-secret-key")
                self.assertEqual(auth_module.read_saved_api_key(), "test-secret-key")
                self.assertEqual(auth_module.connection_key("", ""), "test-secret-key")

            env_text = env_path.read_text(encoding="utf-8")
            self.assertIn("OTHER_SETTING=keep", env_text)
            self.assertIn("MENGBAO_API_KEY=test-secret-key", env_text)

    def test_task_progress_formats_are_normalized(self):
        self.assertEqual(node_module._task_progress_percent({"progress": "45%"}), 45)
        self.assertEqual(node_module._task_progress_percent({"progress": 45}), 45)
        self.assertEqual(node_module._task_progress_percent({"progress": 0.45}), 45)
        self.assertEqual(
            node_module._task_progress_percent({"data": {"progress": "101%"}}),
            100,
        )
        self.assertIsNone(node_module._task_progress_percent({"progress": "pending"}))

    def test_tt_image_25_auto_values_are_linked(self):
        params = node_module._build_model_params(
            "gpt-image-2.5",
            "自动",
            "auto",
            "flare",
            "auto",
            "4K",
            "max",
            "transparent",
            "1:1",
            "1K",
            "minimal",
            "1:1",
            "1K",
        )
        self.assertEqual(params["aspect_ratio"], "auto")
        self.assertEqual(params["resolution"], "auto")
        self.assertEqual(params["version"], "flare")
        self.assertEqual(params["quality"], "max")

    def test_banana_2_uses_camel_case_api_fields(self):
        params = node_module._build_model_params(
            "nano-banana-2",
            "自动",
            "auto",
            "flare",
            "1:1",
            "1K",
            "auto",
            "opaque",
            "9:16",
            "2K",
            "high",
            "1:1",
            "1K",
        )
        self.assertEqual(
            params,
            {"aspectRatio": "9:16", "imageSize": "2K", "thinkingLevel": "high", "n": 1},
        )

    def test_media_request_uses_backend_model_and_polls_to_success(self):
        created = FakeResponse({"code": 200, "data": {"task_id": "task-123"}})
        completed = FakeResponse(
            {
                "task_id": "task-123",
                "state": "success",
                "is_final": True,
                "progress": "100%",
                "result_url": "https://cdn.example.com/output.png",
            }
        )
        image_bytes = self._png_bytes()
        downloaded = FakeResponse({}, content=image_bytes)

        progress_updates = []
        with patch.object(node_module.requests, "post", return_value=created) as post_mock:
            with patch.object(node_module.requests, "get", side_effect=[completed, downloaded]):
                payload = node_module._call_media_api(
                    api_key="test-key",
                    model_type="nano-banana-2-pro",
                    prompt="test prompt",
                    params={"aspectRatio": "1:1", "imageSize": "2K", "n": 1},
                    reference_images=[image_bytes],
                    timeout=30,
                    retries=0,
                    progress_callback=progress_updates.append,
                )
                images, failed_urls = node_module._extract_images(payload, timeout=30, retries=0)

        sent_payload = post_mock.call_args.kwargs["json"]
        self.assertEqual(sent_payload["model"], "banana-pro")
        self.assertTrue(sent_payload["params"]["images"][0].startswith("data:image/png;base64,"))
        self.assertEqual(payload["state"], "success")
        self.assertEqual(progress_updates, [2, 100])
        self.assertEqual(tuple(images[0].shape), (1, 2, 3, 3))
        self.assertEqual(failed_urls, [])

    def test_inline_base64_result_is_decoded(self):
        encoded = base64.b64encode(self._png_bytes()).decode("ascii")
        payload = {"data": [{"b64_json": encoded}]}
        images, failed_urls = node_module._extract_images(payload, timeout=30, retries=0)
        self.assertEqual(tuple(images[0].shape), (1, 2, 3, 3))
        self.assertEqual(failed_urls, [])

    def test_nested_result_url_is_recognized_without_request_url(self):
        base64_values, urls = node_module._collect_image_sources(
            {
                "result_url": {"url": "https://cdn.example.com/output.png"},
                "request": {"url": "https://api.lk888.ai/v1/media/generate"},
            }
        )
        self.assertEqual(base64_values, [])
        self.assertEqual(urls, ["https://cdn.example.com/output.png"])

    def test_transparent_png_preserves_alpha_channel(self):
        buffer = io.BytesIO()
        Image.new("RGBA", (3, 2), (255, 0, 0, 64)).save(buffer, format="PNG")
        image = node_module._png_bytes_to_image_tensor(buffer.getvalue())
        self.assertEqual(tuple(image.shape), (1, 2, 3, 4))
        self.assertAlmostEqual(float(image[0, 0, 0, 3]), 64 / 255, places=5)

    @staticmethod
    def _png_bytes():
        buffer = io.BytesIO()
        Image.new("RGB", (3, 2), (255, 0, 0)).save(buffer, format="PNG")
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
