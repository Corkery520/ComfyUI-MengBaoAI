import importlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mengbao_ecommerce_settings_test"


def load_package():
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load MengBaoAI package from {PLUGIN_ROOT}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = package
    spec.loader.exec_module(package)
    return package


node_pack = load_package()
ecommerce_module = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.ecommerce.settings"
)


class EcommerceSettingsTests(unittest.TestCase):
    def test_node_exposes_the_requested_fields_and_reference_defaults(self):
        required = ecommerce_module.MengBaoEcommerceSettings.INPUT_TYPES()["required"]

        self.assertEqual(
            list(required),
            [
                "product_name",
                "copy_information",
                "special_requirements",
                "product_size",
                "language",
                "quantity",
                "aspect_ratio",
                "usage",
                "page_content",
                "font_style",
                "reverse_pages",
                "model_setting",
                "model_appearance_count",
            ],
        )
        self.assertEqual(required["language"][1]["default"], "中文")
        self.assertEqual(required["quantity"][1]["default"], 8)
        self.assertEqual(required["aspect_ratio"][1]["default"], "9:16")
        self.assertEqual(required["usage"][1]["default"], "详情页")
        self.assertEqual(required["page_content"][1]["default"], "中等")
        self.assertEqual(required["font_style"][1]["default"], "自动判断")
        self.assertEqual(required["reverse_pages"][1]["default"], "自动判断")
        self.assertEqual(required["model_setting"][1]["default"], "自动判断")
        self.assertEqual(
            required["model_appearance_count"][1]["default"],
            "自动判断",
        )
        self.assertEqual(list(required["language"][0]), list(ecommerce_module.LANGUAGE_OPTIONS))
        self.assertEqual(list(required["usage"][0]), list(ecommerce_module.USAGE_OPTIONS))
        self.assertEqual(
            list(required["aspect_ratio"][0]),
            list(ecommerce_module.ASPECT_RATIO_OPTIONS),
        )
        self.assertEqual(
            list(required["font_style"][0]),
            list(ecommerce_module.FONT_STYLE_OPTIONS),
        )

    def test_build_returns_prompt_and_machine_readable_settings(self):
        prompt, aspect_ratio, quantity, settings_json = (
            ecommerce_module.MengBaoEcommerceSettings().build(
                product_name="欧莱雅眼霜 15ml",
                copy_information="保湿；改善眼部暗沉；淡化细纹",
                special_requirements="保持包装文字清晰，不虚构检测数据",
                product_size="长 12cm × 宽 4cm × 高 4cm",
                language="中文",
                quantity=8,
                aspect_ratio="9:16",
                usage="详情页",
                page_content="中等",
                font_style="现代极简无衬线字体",
                reverse_pages="插入1张",
                model_setting="女性模特",
                model_appearance_count="2",
            )
        )

        settings = json.loads(settings_json)
        self.assertEqual(aspect_ratio, "9:16")
        self.assertEqual(quantity, 8)
        self.assertEqual(settings["product_name"], "欧莱雅眼霜 15ml")
        self.assertEqual(settings["reverse_page_mode"], "manual")
        self.assertEqual(settings["reverse_page_count"], 1)
        self.assertEqual(settings["model_appearance_count"], 2)
        self.assertIn("产品名称：欧莱雅眼霜 15ml", prompt)
        self.assertIn("产品尺寸：长 12cm × 宽 4cm × 高 4cm", prompt)
        self.assertIn("页面内容：中等", prompt)
        self.assertIn("必须严格生成 8 张", prompt)
        self.assertIn("不得虚构", prompt)

    def test_dependent_counts_are_normalized_to_the_selected_quantity(self):
        _, _, quantity, settings_json = ecommerce_module.MengBaoEcommerceSettings().build(
            product_name="测试产品",
            copy_information="",
            special_requirements="",
            product_size="",
            language="英语",
            quantity=4,
            aspect_ratio="1:1",
            usage="详情页",
            page_content="精简",
            font_style="自动判断",
            reverse_pages="插入3张",
            model_setting="不使用模特",
            model_appearance_count="4",
        )

        settings = json.loads(settings_json)
        self.assertEqual(quantity, 4)
        self.assertEqual(settings["reverse_page_count"], 1)
        self.assertEqual(settings["reverse_pages"], "插入1张")
        self.assertEqual(settings["model_appearance_count"], 0)

    def test_node_is_registered_in_the_ecommerce_category(self):
        node_class = node_pack.NODE_CLASS_MAPPINGS["MengBaoEcommerceSettings"]
        self.assertIs(node_class, ecommerce_module.MengBaoEcommerceSettings)
        self.assertEqual(node_class.CATEGORY, "萌宝AI/电商")
        self.assertEqual(
            node_pack.NODE_DISPLAY_NAME_MAPPINGS["MengBaoEcommerceSettings"],
            "萌宝AI·电商设置",
        )


if __name__ == "__main__":
    unittest.main()
