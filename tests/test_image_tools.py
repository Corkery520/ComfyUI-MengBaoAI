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


if __name__ == "__main__":
    unittest.main()
