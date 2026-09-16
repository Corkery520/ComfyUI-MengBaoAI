"""在临时存储和独立端口预览素材 UI，不加载或修改正在运行的 ComfyUI。"""

import argparse
import importlib
import importlib.util
import io
import os
import sys
import tempfile
import types
from pathlib import Path

from aiohttp import web
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "tests" / "fixtures" / "materials_preview.html"
APP_JS = """
export const app = { graph: { _nodes: [], setDirtyCanvas() {} }, ui: { settings: {
  getSettingValue: () => document.querySelector('#locale').value,
  settingsLookup: { 'Comfy.Locale': { onChange() {} } }
} }, extensions: [], registerExtension(extension) { this.extensions.push(extension); } };
"""
API_JS = "export const api = { fetchApi: (path, options) => fetch(path, options) };"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8197)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mengbao-material-preview-") as directory:
        root = Path(directory)
        os.environ["MENGBAOAI_USER_DIRECTORY"] = str(root / "user")
        # 先加载包，再只注册素材路由，防止隔离预览触发其它节点的服务接口。
        spec = importlib.util.spec_from_file_location("mengbao_preview", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = package
        spec.loader.exec_module(package)
        routes = web.RouteTableDef()
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes))
        sys.modules["server"] = fake_server
        prompt_store = importlib.import_module("mengbao_preview.utils.prompt_store")
        prompt_store.LEGACY_STORE_PATHS = ()
        prompt_store.DEFAULT_STORE_PATH = root / "missing-default.json"
        importlib.import_module("mengbao_preview.api.prompt_routes").register_prompt_routes()
        material_routes = importlib.import_module("mengbao_preview.api.material_routes")
        material_routes.register_material_routes()

        image = Image.new("RGBA", (750, 10661), "#eef0f5")
        draw = ImageDraw.Draw(image)
        colors = ["#397bab", "#58a79b", "#a3567e", "#445261"]
        for index in range(15):
            draw.rectangle((0, index * 720, 749, index * 720 + 600), fill=colors[index % 4])
            draw.text((50, index * 720 + 80), f"PREVIEW {index + 1}", fill="white", font_size=65)
        content = io.BytesIO()
        image.save(content, format="PNG")
        fixture = content.getvalue()
        store = material_routes.MATERIAL_STORE
        store.import_image(fixture, "Long product page.png", "产品")
        small = io.BytesIO()
        Image.new("RGBA", (640, 480), (96, 174, 125, 160)).save(small, format="PNG")
        store.import_image(small.getvalue(), "Transparent sample.png", "参考")

        @routes.get("/")
        async def index(request):
            return web.FileResponse(HTML)

        @routes.get("/image-output")
        async def image_output_preview(request):
            return web.FileResponse(ROOT / "tests" / "fixtures" / "image_output_preview.html")

        @routes.get("/scripts/{script}")
        async def script(request):
            source = APP_JS if request.match_info["script"] == "app.js" else API_JS
            return web.Response(text=source, content_type="text/javascript")

        @routes.get("/extensions/mengbao/js/{file}")
        async def frontend_file(request):
            filename = request.match_info["file"]
            if filename not in {"material_images.js", "material_library.js", "material_uploads.js", "materials.css", "image_output.js", "image_output.css", "prompt_organizer.js"}:
                raise web.HTTPNotFound()
            return web.FileResponse(ROOT / "web" / "js" / filename)

        @routes.get("/fixture.png")
        async def test_image(request):
            return web.Response(body=fixture, content_type="image/png")

        @routes.post("/upload/image")
        async def upload(request):
            reader = await request.multipart()
            async for part in reader:
                if part.name == "image":
                    path = root / "upload.png"
                    path.write_bytes(await part.read())
            return web.json_response({"name": "upload.png", "subfolder": "mengbao", "type": "input"})

        @routes.get("/view")
        async def view(request):
            path = root / "upload.png"
            if not path.is_file():
                return web.Response(body=fixture, content_type="image/png")
            return web.FileResponse(path)

        application = web.Application(client_max_size=34 * 1024 * 1024)
        application.add_routes(routes)
        web.run_app(application, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
