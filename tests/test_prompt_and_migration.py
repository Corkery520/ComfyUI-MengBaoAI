import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mengbao_prompt_test"


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


load_package()
auth_module = importlib.import_module(f"{PACKAGE_NAME}.api.auth")
prompt_store = importlib.import_module(f"{PACKAGE_NAME}.utils.prompt_store")
prompt_nodes = importlib.import_module(
    f"{PACKAGE_NAME}.nodes.prompt.organizer"
)


def organizer_arguments(**overrides):
    values = {
        "action": "save_or_update",
        "group": "default",
        "title": "Product photo",
        "prompt": "A clean product photo",
        "query": "",
        "tags": "product, clean",
        "note": "",
        "merge_mode": "update",
        "new_group": "",
        "import_json": "",
        "import_path": "",
        "export_path": "",
    }
    values.update(overrides)
    return values


class PromptAndMigrationTests(unittest.TestCase):
    def test_prompt_store_migrates_legacy_data_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_path = root / "legacy-prompts.json"
            target_path = root / "user" / "prompts.json"
            legacy_payload = {
                "version": 1,
                "groups": ["product"],
                "prompts": [
                    {
                        "title": "Hero",
                        "group": "product",
                        "prompt": "Studio lighting",
                    }
                ],
            }
            legacy_path.write_text(
                json.dumps(legacy_payload, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch.object(prompt_store, "STORE_PATH", target_path), patch.object(
                prompt_store,
                "LEGACY_STORE_PATHS",
                (legacy_path,),
            ), patch.object(
                prompt_store,
                "DEFAULT_STORE_PATH",
                root / "missing-default.json",
            ):
                migrated = prompt_store._load_store()

            self.assertTrue(target_path.is_file())
            self.assertEqual(migrated["prompts"][0]["prompt"], "Studio lighting")

            legacy_payload["prompts"][0]["prompt"] = "Changed legacy value"
            legacy_path.write_text(
                json.dumps(legacy_payload, ensure_ascii=False),
                encoding="utf-8",
            )
            with patch.object(prompt_store, "STORE_PATH", target_path), patch.object(
                prompt_store,
                "LEGACY_STORE_PATHS",
                (legacy_path,),
            ), patch.object(
                prompt_store,
                "DEFAULT_STORE_PATH",
                root / "missing-default.json",
            ):
                loaded_again = prompt_store._load_store()

            self.assertEqual(
                loaded_again["prompts"][0]["prompt"],
                "Studio lighting",
            )

    def test_prompt_nodes_save_and_read_from_user_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "prompts.json"
            with patch.object(prompt_store, "STORE_PATH", store_path), patch.object(
                prompt_store,
                "LEGACY_STORE_PATHS",
                (),
            ), patch.object(
                prompt_store,
                "DEFAULT_STORE_PATH",
                Path(directory) / "missing-default.json",
            ):
                result = prompt_nodes.WANGPromptOrganizer().run(
                    **organizer_arguments()
                )
                prompt, status = prompt_nodes.WANGPromptReader().read(
                    "default",
                    "Product photo",
                    "fallback",
                )

            self.assertEqual(result[0], "A clean product photo")
            self.assertIn("Saved prompt", result[3])
            self.assertEqual(prompt, "A clean product photo")
            self.assertIn("Loaded prompt", status)

    def test_saved_api_key_migrates_to_user_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_path = root / "legacy.env"
            target_path = root / "user" / ".env"
            legacy_path.write_text(
                "MENGBAO_API_KEY=legacy-secret\n",
                encoding="utf-8",
            )

            with patch.object(auth_module, "ENV_PATH", target_path), patch.object(
                auth_module,
                "USER_DATA_DIRECTORY",
                target_path.parent,
            ), patch.object(
                auth_module,
                "LEGACY_ENV_PATHS",
                (legacy_path,),
            ):
                saved = auth_module.read_saved_api_key()

            self.assertEqual(saved, "legacy-secret")
            self.assertEqual(
                target_path.read_text(encoding="utf-8"),
                "MENGBAO_API_KEY=legacy-secret\n",
            )

            legacy_path.write_text(
                "MENGBAO_API_KEY=changed-legacy-secret\n",
                encoding="utf-8",
            )
            with patch.object(auth_module, "ENV_PATH", target_path), patch.object(
                auth_module,
                "USER_DATA_DIRECTORY",
                target_path.parent,
            ), patch.object(
                auth_module,
                "LEGACY_ENV_PATHS",
                (legacy_path,),
            ):
                loaded_again = auth_module.read_saved_api_key()

            self.assertEqual(loaded_again, "legacy-secret")


if __name__ == "__main__":
    unittest.main()
