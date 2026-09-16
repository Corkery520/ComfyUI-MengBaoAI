"""在指定临时用户目录生成历史面板测试数据，不调用真实 API。"""

import argparse
import base64
import importlib
import importlib.util
import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user_directory", type=Path)
    parser.add_argument("--running-only", action="store_true")
    args = parser.parse_args()
    os.environ["MENGBAOAI_USER_DIRECTORY"] = str(args.user_directory / "mengbaoai")
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("mengbao_history_preview", root / "__init__.py", submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    node = importlib.import_module(f"{spec.name}.nodes.image_api.generate")
    storage = importlib.import_module(f"{spec.name}.utils.history_store").HISTORY_STORE
    if args.running_only:
        running = storage.start("gpt-image-2", "测试中的生成任务", {"size": "auto"}, 1)
        storage.progress(running, 45)
        return
    material_storage = importlib.import_module(f"{spec.name}.utils.material_store").MATERIAL_STORE
    image = Image.new("RGBA", (800, 600), (234, 241, 242, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((200, 460, 610, 520), fill=(195, 212, 211, 255))
    draw.rounded_rectangle((325, 110, 475, 480), radius=18, fill=(58, 135, 123, 255))
    draw.rectangle((350, 75, 450, 110), fill=(43, 57, 55, 255))
    draw.rectangle((338, 250, 462, 360), fill=(244, 247, 248, 255))
    draw.text((361, 285), "MENGBAO", fill=(45, 82, 75, 255))
    content = io.BytesIO()
    image.save(content, "PNG")
    encoded = base64.b64encode(content.getvalue()).decode("ascii")
    material_storage.import_image(content.getvalue(), "Preview product.png", "产品")
    arguments = {name: settings[1]["default"] for name, settings in node.MengBaoImageAPI.INPUT_TYPES()["required"].items()}
    arguments.update(api_key="smoke-fixture-key", ui_language="zh", prompt="产品摄影：清晰展示瓶身和品牌", batch_size=1)
    success = {"data": [{"b64_json": encoded}]}
    failed = {"error": {"message": "HTTP 429: Too Many Requests"}}
    for model, batches, payloads in (("gpt-image-2", 1, [success]), ("gpt-image-2.5", 2, [success, success]),
                                    ("nano-banana-2", 2, [success, failed]), ("nano-banana-2-pro", 1, [failed])):
        arguments.update(model_type=model, batch_size=batches)
        with patch.object(node, "_call_media_api", side_effect=payloads):
            node.MengBaoImageAPI().generate(**arguments)
    running = storage.start("gpt-image-2", "测试中的生成任务", {"size": "auto"}, 1)
    storage.progress(running, 45)
    print(f"Preview records: {storage.list_items()['counts']}")


if __name__ == "__main__":
    main()
