"""隔离复刻面板预览：临时数据、模拟视觉服务，无付费 API 请求。"""
import argparse
import asyncio
import importlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import torch
from aiohttp import web
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
APP = """
export const app = { extensions: [], graph: { _nodes: [], links: {10: {origin_id:2,target_id:3}}, getNodeById(id) {return this._nodes.find(n => String(n.id) === String(id));}, setDirtyCanvas(){} },
 ui: {settings: {getSettingValue: () => document.querySelector('#locale').value, settingsLookup: {'Comfy.Locale': {onChange(){}}}}},
 registerExtension(e){this.extensions.push(e);}, async graphToPrompt(){ return {output:{'1':{class_type:'LoadImage',inputs:{}},'2':{class_type:'MengBaoImageReverse',inputs:{image:['1',0],request_id:this.graph._nodes[0].widgets[0].value}},'3':{class_type:'MengBaoImageReplicaSettings',inputs:{analysis:['2',0]}},'4':{class_type:'WANGImageAPI',inputs:{replica_settings:['3',1]}}}} } };
"""
API = """
const listeners = {};
export const api = { clientId: 'replica-qa', apiURL: path => path, addEventListener(name, fn){(listeners[name] ||= []).push(fn);},
 removeEventListener(name, fn){listeners[name] = (listeners[name] || []).filter(item => item !== fn);},
 async fetchApi(path, options) { const response = await fetch(path, options); if(path === '/prompt' && response.ok){ const data = await response.clone().json(); setTimeout(() => {for(const fn of listeners.executed || []) fn({detail:{node:'2',prompt_id:data.prompt_id,output:data.ui}});},20); } return response; } };
"""
ANALYSIS = {"composition": "Clean green product poster with red headline", "elements": [
    {"id": "title", "kind": "text", "name": "Headline", "box": {"x": .08, "y": .04, "w": .84, "h": .15}, "text": "FRESH DAILY", "textStyle": "Red bold sans serif"},
    {"id": "p1", "kind": "product", "name": "Bottle", "box": {"x": .27, "y": .28, "w": .46, "h": .52}, "description": "Green glass bottle", "productGroup": "bottle"},
    {"id": "label", "kind": "text", "name": "Bottle label", "box": {"x": .31, "y": .47, "w": .37, "h": .1}, "text": "OLD BRAND", "parentId": "p1"},
    {"id": "background", "kind": "background", "name": "Background", "box": {"x": 0, "y": 0, "w": 1, "h": 1}, "description": "Light gray background"},
]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8199)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mengbao-replica-qa-") as directory:
        os.environ["MENGBAOAI_USER_DIRECTORY"] = str(Path(directory) / "user")
        routes = web.RouteTableDef()
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes, send_sync=lambda *args: None))
        sys.modules["server"] = fake_server
        spec = importlib.util.spec_from_file_location("replica_qa", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = package
        spec.loader.exec_module(package)
        vision = importlib.import_module("replica_qa.api.vision_client")
        nodes = importlib.import_module("replica_qa.nodes.ecommerce.replica")
        calls = []
        vision.read_saved_api_key = lambda: "qa-not-a-real-key"

        def mock_post(url, **kwargs):
            calls.append(url)
            if "gem-3.7-flash" in url:
                return types.SimpleNamespace(ok=False, status_code=503, reason="Service Unavailable", json=lambda: {"error": "QA primary unavailable"})
            prompt = kwargs["json"]["contents"][0]["parts"][0]["text"]
            data = {"description": "将原图对应产品替换为当前参考图中的蓝色瓶身，保持真实长宽高比例及包装结构，适配原位置与光照，不拉宽或压缩。"} if "产品替换描述" in prompt else ANALYSIS
            return types.SimpleNamespace(ok=True, json=lambda: {"candidates": [{"content": {"parts": [{"text": json.dumps(data, ensure_ascii=False)}]}}]})
        vision.requests = types.SimpleNamespace(post=mock_post, ConnectionError=ConnectionError, Timeout=TimeoutError)
        image = Image.new("RGB", (480, 640), "#e5e8e6")
        draw = ImageDraw.Draw(image)
        draw.text((40, 42), "FRESH DAILY", fill="#a93045", font_size=44)
        draw.rounded_rectangle((146, 194, 334, 506), radius=25, fill="#438275")
        draw.rectangle((150, 309, 330, 382), fill="#cce0d9")
        draw.text((160, 335), "OLD BRAND", fill="#183c33", font_size=25)
        tensor = torch.from_numpy(np.asarray(image).astype(np.float32) / 255)[None]
        buffer = io.BytesIO()
        Image.new("RGB", (240, 480), "#428bd1").save(buffer, "PNG")
        sample = buffer.getvalue()

        @routes.get("/")
        async def index(_request):
            return web.FileResponse(ROOT / "tests" / "fixtures" / "replica_preview.html")

        @routes.get("/scripts/{name}")
        async def script(request):
            return web.Response(text=APP if request.match_info["name"] == "app.js" else API, content_type="text/javascript")

        @routes.get("/extensions/mengbao/js/{name}")
        async def frontend(request):
            name = request.match_info["name"]
            if name not in {"replica.js", "replica.css", "replica_editor.js", "replica_model.js", "material_uploads.js", "material_library.js", "materials.css"}:
                raise web.HTTPNotFound()
            return web.FileResponse(ROOT / "web" / "js" / name)

        @routes.post("/prompt")
        async def prompt(request):
            body = await request.json()
            if set(body.get("prompt", {})) != {"1", "2"} or body.get("partial_execution_targets") != ["2"]:
                return web.json_response({"error": "QA: downstream execution is forbidden"}, status=400)
            result = await asyncio.to_thread(nodes.MengBaoImageReverse().analyze, tensor, body["prompt"]["2"]["inputs"]["request_id"])
            return web.json_response({"prompt_id": "qa-prompt", "ui": result["ui"]})

        @routes.get("/qa-sample.png")
        async def sample_image(_request):
            return web.Response(body=sample, content_type="image/png")

        @routes.get("/qa-state")
        async def state(_request):
            return web.json_response({"calls": calls})

        web_app = web.Application(client_max_size=34 * 1024 * 1024)
        web_app.add_routes(routes)
        print(f"Replica QA storage: {directory}", flush=True)
        web.run_app(web_app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
