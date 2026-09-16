import importlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "mengbao_material_test"
spec = importlib.util.spec_from_file_location(PACKAGE, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load MengBaoAI package from {ROOT}")
pack = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = pack
spec.loader.exec_module(pack)


def image_bytes(mode="RGBA", size=(8, 4)):
    buffer = io.BytesIO()
    Image.new(mode, size, (20, 40, 60, 128) if mode == "RGBA" else (20, 40, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


class MaterialLibraryTests(unittest.TestCase):
    def setUp(self):
        module = importlib.import_module(f"{PACKAGE}.utils.material_store")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.store = module.MaterialStore(self.root / "materials")

    def test_import_is_persistent_and_preserves_alpha_and_name(self):
        item = self.store.import_image(image_bytes(), "产品图.png", "产品")
        reloaded = type(self.store)(self.store.root)
        self.assertEqual(reloaded.get_item(item["id"])["name"], "产品图.png")
        self.assertEqual((item["width"], item["height"]), (8, 4))
        with Image.open(reloaded.file_path(item["id"])) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 128)
        with Image.open(reloaded.file_path(item["id"], thumbnail=True)) as thumbnail:
            self.assertLessEqual(max(thumbnail.size), 512)

    def test_categories_search_favorites_move_and_delete(self):
        self.store.add_category("新品")
        item = self.store.import_image(image_bytes(), "Spring.png", "新品")
        self.store.update_item(item["id"], favorite=True, name="Spring product.png")
        self.assertEqual(len(self.store.list_items(query="SPRING", favorites_only=True)["items"]), 1)
        self.store.rename_category("新品", "春季")
        self.assertEqual(self.store.get_item(item["id"])["category"], "春季")
        self.store.delete_category("春季")
        self.assertEqual(self.store.get_item(item["id"])["category"], "未分类")
        path = self.store.file_path(item["id"])
        self.store.delete_item(item["id"])
        self.assertFalse(path.exists())
        self.assertEqual(self.store.list_items()["items"], [])

    def test_invalid_files_paths_and_categories_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.import_image(b"not an image", "bad.png", "产品")
        with self.assertRaises(ValueError):
            self.store.file_path("../../secret")
        with self.assertRaises(ValueError):
            self.store.add_category("../unsafe")
        with self.assertRaises(ValueError):
            self.store.delete_category("未分类")
        self.assertEqual(self.store.list_items()["items"], [])

    def test_corrupt_index_is_not_overwritten(self):
        self.store.root.mkdir(parents=True)
        self.store.index_path.write_text("broken json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.add_category("新品")
        self.assertEqual(self.store.index_path.read_text(encoding="utf-8"), "broken json")

    def test_two_nodes_load_the_same_material_and_return_standard_mask_batch(self):
        module = importlib.import_module(f"{PACKAGE}.nodes.image_tools.material_images")
        item = self.store.import_image(image_bytes(), "reference.png", "参考")
        from unittest.mock import patch
        with patch.object(module, "MATERIAL_STORE", self.store):
            loader = module.MengBaoLoadImage()
            image, mask = loader.load_image(f"mengbao-material:{item['id']}")
            selected_image, selected_mask = module.MengBaoMaterialLibrary().load_material(item["id"])
            self.assertEqual(tuple(image.shape), (1, 4, 8, 3))
            self.assertEqual(tuple(mask.shape), (1, 4, 8))
            self.assertAlmostEqual(float(mask[0, 0, 0]), 1 - 128 / 255, places=5)
            self.assertTrue((selected_image == image).all())
            self.assertTrue((selected_mask == mask).all())
            with self.assertRaisesRegex(ValueError, "select a material"):
                module.MengBaoMaterialLibrary().load_material("")

    def test_only_material_loader_is_registered_under_the_unified_name(self):
        self.assertNotIn("WANGLoadImageUploadPaste", pack.NODE_CLASS_MAPPINGS)
        self.assertNotIn("WANGLoadImageUploadPaste", pack.NODE_DISPLAY_NAME_MAPPINGS)
        self.assertEqual(pack.NODE_DISPLAY_NAME_MAPPINGS["MengBaoLoadImage"], "萌宝AI·加载图片")
        self.assertEqual(list(pack.NODE_DISPLAY_NAME_MAPPINGS.values()).count("萌宝AI·加载图片"), 1)
        for alias in ("萌宝AI·加载图片", "MengBaoAI Load Image", "萌宝AI 加载图片"):
            self.assertIn(alias, pack.NODE_CLASS_MAPPINGS["MengBaoLoadImage"].SEARCH_ALIASES)
        self.assertEqual(pack.NODE_DISPLAY_NAME_MAPPINGS["MengBaoMaterialLibrary"], "萌宝AI·素材库")
        for node_id in ("MengBaoLoadImage", "MengBaoMaterialLibrary"):
            node = pack.NODE_CLASS_MAPPINGS[node_id]
            self.assertEqual(node.RETURN_TYPES, ("IMAGE", "MASK"))
            self.assertIn("MengBaoAI", node.SEARCH_ALIASES)


if __name__ == "__main__":
    unittest.main()
