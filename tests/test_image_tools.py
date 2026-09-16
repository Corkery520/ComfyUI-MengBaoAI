import importlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

import torch
from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mengbao_image_tools_test"


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
split_module = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.image_tools.split_crop"
)
load_module = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.image_tools.load_image"
)
collage_module = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.image_tools.collage"
)
constraint_module = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.image_tools.constraint"
)


class ImageToolsTests(unittest.TestCase):
    def test_locales_cover_every_registered_node_input_and_output(self):
        locale_data = {}
        for language in ("en", "zh"):
            locale_data[language] = json.loads(
                (PLUGIN_ROOT / "locales" / language / "nodeDefs.json").read_text(
                    encoding="utf-8"
                )
            )

        expected_ids = set(node_pack.NODE_CLASS_MAPPINGS)
        for language, definitions in locale_data.items():
            self.assertEqual(set(definitions), expected_ids, language)
            for node_id, node_class in node_pack.NODE_CLASS_MAPPINGS.items():
                inputs = node_class.INPUT_TYPES()
                input_names = set(inputs.get("required", {})) | set(
                    inputs.get("optional", {})
                )
                definition = definitions[node_id]
                self.assertEqual(set(definition["inputs"]), input_names, node_id)
                self.assertEqual(
                    len(definition["outputs"]),
                    len(node_class.RETURN_TYPES),
                    node_id,
                )

    def test_grid_split_returns_tiles_in_a_batch(self):
        image = torch.arange(4 * 4 * 3, dtype=torch.float32).reshape(1, 4, 4, 3)
        tiles, rows, columns, count = split_module.ImageGridSplit().split(
            image,
            "2x2",
            2,
            2,
            True,
        )

        self.assertEqual(tuple(tiles.shape), (4, 2, 2, 3))
        self.assertEqual((rows, columns, count), (2, 2, 4))
        torch.testing.assert_close(tiles[0], image[0, :2, :2, :])
        torch.testing.assert_close(tiles[3], image[0, 2:, 2:, :])

    def test_free_crop_clamps_to_the_image_bounds(self):
        image = torch.zeros((1, 8, 10, 3), dtype=torch.float32)
        cropped, x, y, width, height = split_module.ImageFreeCrop().crop(
            image,
            8,
            7,
            20,
            20,
        )

        self.assertEqual(tuple(cropped.shape), (1, 1, 2, 3))
        self.assertEqual((x, y, width, height), (8, 7, 2, 1))

    def test_grid_picker_uses_one_based_row_and_column(self):
        image = torch.arange(6 * 6 * 3, dtype=torch.float32).reshape(1, 6, 6, 3)
        tile, row, column = split_module.ImageGridTilePicker().pick(
            image,
            "3x3",
            2,
            2,
            2,
            3,
        )

        self.assertEqual((row, column), (2, 3))
        torch.testing.assert_close(tile, image[:, 2:4, 4:6, :])

    def test_load_image_accepts_data_url_and_returns_alpha_mask(self):
        source = Image.new("RGBA", (3, 2), (20, 40, 60, 128))
        buffer = io.BytesIO()
        source.save(buffer, format="PNG")
        import base64

        data_url = "data:image/png;base64," + base64.b64encode(
            buffer.getvalue()
        ).decode("ascii")
        image, mask, filename, width, height = (
            load_module.WANGLoadImageUploadPaste().load_image(data_url, "")
        )

        self.assertEqual(tuple(image.shape), (1, 2, 3, 3))
        self.assertEqual(tuple(mask.shape), (2, 3))
        self.assertEqual(filename, "clipboard_image.png")
        self.assertEqual((width, height), (3, 2))
        self.assertAlmostEqual(float(mask[0, 0]), 1.0 - 128 / 255.0, places=5)

    def test_smart_collage_stacks_one_to_three_images_vertically(self):
        first = torch.full((1, 12, 16, 3), 0.1)
        second = torch.full((1, 10, 13, 3), 0.5)
        third = torch.full((1, 14, 10, 3), 0.9)

        (collage,) = collage_module.MengBaoSmartCollage().collage(
            first,
            second,
            third,
            None,
        )

        self.assertEqual(tuple(collage.shape), (1, 46, 16, 3))
        self.assertAlmostEqual(float(collage[0, 2, 2, 0]), 0.1, places=4)
        self.assertAlmostEqual(float(collage[0, 15, 2, 0]), 0.5, places=4)
        self.assertAlmostEqual(float(collage[0, 35, 2, 0]), 0.9, places=4)

    def test_new_image_tool_inputs_match_the_reference_nodes(self):
        collage_inputs = collage_module.MengBaoSmartCollage.INPUT_TYPES()
        self.assertEqual(collage_inputs["required"], {})
        self.assertEqual(
            list(collage_inputs["optional"]),
            ["image_1", "image_2", "image_3", "image_4"],
        )

        constraint_inputs = constraint_module.MengBaoImageConstraint.INPUT_TYPES()[
            "required"
        ]
        self.assertEqual(
            list(constraint_inputs),
            [
                "image",
                "max_width",
                "max_height",
                "min_width",
                "min_height",
                "crop_if_required",
            ],
        )
        self.assertEqual(constraint_inputs["max_width"][1]["default"], 2048)
        self.assertEqual(constraint_inputs["max_height"][1]["default"], 2048)
        self.assertEqual(constraint_inputs["crop_if_required"][1]["default"], "no")

    def test_smart_collage_uses_balanced_two_by_two_layout_for_four_images(self):
        images = (
            torch.full((1, 192, 256, 3), 0.1),
            torch.full((1, 133, 173, 3), 0.3),
            torch.full((1, 168, 121, 3), 0.6),
            torch.full((1, 99, 132, 3), 0.9),
        )

        (collage,) = collage_module.MengBaoSmartCollage().collage(*images)

        self.assertEqual(tuple(collage.shape), (1, 437, 505, 3))
        self.assertAlmostEqual(float(collage[0, 50, 50, 0]), 0.1, places=4)
        self.assertAlmostEqual(float(collage[0, 50, 400, 0]), 0.3, places=4)
        self.assertAlmostEqual(float(collage[0, 350, 50, 0]), 0.6, places=4)
        self.assertAlmostEqual(float(collage[0, 350, 400, 0]), 0.9, places=4)

    def test_smart_collage_requires_at_least_one_image(self):
        with self.assertRaisesRegex(ValueError, "At least one IMAGE"):
            collage_module.MengBaoSmartCollage().collage(None, None, None, None)

    def test_image_constraint_preserves_aspect_ratio_inside_maximum_size(self):
        image = torch.zeros((1, 10, 20, 3), dtype=torch.float32)

        (constrained,) = constraint_module.MengBaoImageConstraint().constrain(
            image,
            max_width=10,
            max_height=10,
            min_width=0,
            min_height=0,
            crop_if_required="no",
        )

        self.assertEqual(tuple(constrained.shape), (1, 5, 10, 3))

    def test_image_constraint_can_crop_when_minimum_and_maximum_conflict(self):
        image = torch.zeros((1, 10, 20, 3), dtype=torch.float32)
        image[:, :, :10, :] = 1.0

        (contained,) = constraint_module.MengBaoImageConstraint().constrain(
            image,
            max_width=10,
            max_height=10,
            min_width=10,
            min_height=10,
            crop_if_required="no",
        )
        (cropped,) = constraint_module.MengBaoImageConstraint().constrain(
            image,
            max_width=10,
            max_height=10,
            min_width=10,
            min_height=10,
            crop_if_required="yes",
        )

        self.assertEqual(tuple(contained.shape), (1, 5, 10, 3))
        self.assertEqual(tuple(cropped.shape), (1, 10, 10, 3))

    def test_new_image_tools_are_registered_with_expected_names(self):
        expected = {
            "MengBaoSmartCollage": "萌宝AI智能拼图",
            "MengBaoImageConstraint": "萌宝图像约束",
        }
        for node_id, display_name in expected.items():
            with self.subTest(node_id=node_id):
                node_class = node_pack.NODE_CLASS_MAPPINGS[node_id]
                self.assertEqual(
                    node_pack.NODE_DISPLAY_NAME_MAPPINGS[node_id],
                    display_name,
                )
                self.assertEqual(node_class.CATEGORY, "萌宝AI/图像处理")


if __name__ == "__main__":
    unittest.main()
