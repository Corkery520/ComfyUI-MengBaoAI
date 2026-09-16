"""使用本机 ComfyUI 的真实验证器检查接线及局部执行，不提交生成请求。"""
import argparse
import asyncio
import importlib.util
import os
import sys
import tempfile
from pathlib import Path


def defaults(node_class):
    return {name: definition[1]["default"] for name, definition in node_class.INPUT_TYPES()["required"].items() if len(definition) > 1 and "default" in definition[1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-directory", type=Path, required=True)
    parser.add_argument("--plugin-directory", type=Path, default=Path(__file__).resolve().parents[1])
    options = parser.parse_args()
    sys.argv = [sys.argv[0], "--cpu"]
    sys.path.insert(0, str(options.comfy_directory.resolve()))
    with tempfile.TemporaryDirectory(prefix="mengbao-replica-comfy-check-") as directory:
        os.environ["MENGBAOAI_USER_DIRECTORY"] = directory
        import nodes
        import execution

        root = options.plugin_directory.resolve()
        spec = importlib.util.spec_from_file_location("mengbao_replica_comfy_check", root / "__init__.py", submodule_search_locations=[str(root)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = package
        spec.loader.exec_module(package)
        nodes.NODE_CLASS_MAPPINGS.update(package.NODE_CLASS_MAPPINGS)

        class ImageSource:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}}
            RETURN_TYPES = ("IMAGE",)
            FUNCTION = "image"
            CATEGORY = "test"

        nodes.NODE_CLASS_MAPPINGS["ReplicaCheckImageSource"] = ImageSource
        generation = defaults(package.NODE_CLASS_MAPPINGS["WANGImageAPI"])
        generation.update(prompt=["3", 0], replica_settings=["3", 1])
        prompt = {
            "1": {"class_type": "ReplicaCheckImageSource", "inputs": {}},
            "2": {"class_type": "MengBaoImageReverse", "inputs": {"image": ["1", 0], "request_id": "a" * 32}},
            "3": {"class_type": "MengBaoImageReplicaSettings", "inputs": {"analysis": ["2", 0], "draft_json": "{}", "draft_id": "b" * 32}},
            "4": {"class_type": "WANGImageAPI", "inputs": generation},
            "5": {"class_type": "MengBaoReplicaAudit", "inputs": {"images": ["4", 0], "replica_settings": ["3", 1]}},
        }
        result = asyncio.run(execution.validate_prompt("replica-local-validation", prompt, ["2"]))
        assert result[0] and result[2] == ["2"], result
        result = asyncio.run(execution.validate_prompt("replica-local-validation", prompt, ["5"]))
        assert result[0] and result[2] == ["5"], result
        print("Real ComfyUI validator: isolated analysis target and full replica/audit port types passed. No API requests executed.")


if __name__ == "__main__":
    main()
