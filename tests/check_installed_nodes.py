import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path


EXPECTED_NAMES = {
    "MengBaoSmartCollage": "萌宝AI·智能拼图",
    "MengBaoGlobalAPIKey": "萌宝AI全局API Key管理",
    "MengBaoEcommerceSettings": "萌宝AI·电商设置",
    "MengBaoMaterialLibrary": "萌宝AI·素材库",
    "MengBaoImageConstraint": "萌宝AI·图像约束",
    "MengBaoSaveImage": "萌宝AI·保存图片",
    "MengBaoPreviewImage": "萌宝AI·预览图片",
    "MengBaoImageReverse": "萌宝AI·图片反推",
    "MengBaoImageReplicaSettings": "萌宝AI·图片复刻设置",
    "MengBaoReplicaAudit": "萌宝AI·复刻检查",
}


def check_installation(root):
    spec = importlib.util.spec_from_file_location("mengbao_installed_nodes_check", root / "__init__.py", submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    missing = EXPECTED_NAMES.keys() - package.NODE_CLASS_MAPPINGS.keys()
    assert not missing, f"Missing installed node IDs: {', '.join(sorted(missing))}"
    for node_id, name in EXPECTED_NAMES.items():
        assert package.NODE_DISPLAY_NAME_MAPPINGS[node_id] == name, f"Installed display name mismatch: {node_id}"
        assert name in package.NODE_CLASS_MAPPINGS[node_id].SEARCH_ALIASES, f"Installed search alias is missing: {node_id}"
    for locale in ("en", "zh"):
        definitions = json.loads((root / "locales" / locale / "nodeDefs.json").read_text(encoding="utf-8"))
        for node_id, name in EXPECTED_NAMES.items():
            definition = definitions[node_id]
            if locale == "zh":
                assert definition["display_name"] == name, f"Installed locale name mismatch: {node_id}"
            schema = package.NODE_CLASS_MAPPINGS[node_id].INPUT_TYPES()
            inputs = set(schema.get("required", {})) | set(schema.get("optional", {}))
            assert inputs <= definition["inputs"].keys(), f"Installed locale inputs incomplete: {node_id}"
    for relative in ("web/js/image_output.js", "web/js/prompt_organizer.js", "web/js/material_images.js", "web/js/replica.js", "web/js/replica_editor.js"):
        assert (root / relative).is_file(), f"Installed frontend file is missing: {relative}"
    assert "MengBaoPromptOrganizerDraft" in (root / "web/js/prompt_organizer.js").read_text(encoding="utf-8"), "Installed prompt draft bridge is missing"
    print("Installed node registration, names, locale inputs and prompt draft bridge passed.")
    for node_id, name in EXPECTED_NAMES.items():
        print(f"{node_id}: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-directory", type=Path, required=True)
    args = parser.parse_args()
    # 安装检查只导入注册信息，不读写用户的密钥、提示词或素材数据。
    with tempfile.TemporaryDirectory(prefix="mengbao-install-check-") as directory:
        os.environ["MENGBAOAI_USER_DIRECTORY"] = directory
        check_installation(args.plugin_directory.resolve())
