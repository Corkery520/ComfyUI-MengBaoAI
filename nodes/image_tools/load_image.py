import base64
import io
import os
from typing import Tuple

import numpy as np
import torch
from PIL import Image, ImageOps

try:
    import folder_paths
except Exception:
    folder_paths = None


def _decode_data_url(value: str) -> Tuple[bytes, str]:
    header, encoded = value.split(",", 1)
    extension = "png"
    if "image/jpeg" in header or "image/jpg" in header:
        extension = "jpg"
    elif "image/webp" in header:
        extension = "webp"
    elif "image/bmp" in header:
        extension = "bmp"
    return base64.b64decode(encoded), extension


def _read_image_bytes(image_data: str) -> Tuple[bytes, str]:
    image_data = (image_data or "").strip()
    if not image_data:
        raise ValueError("Please upload an image or paste an image with Ctrl+V first.")

    if image_data.startswith("data:image/"):
        return _decode_data_url(image_data)

    if os.path.exists(image_data):
        with open(image_data, "rb") as image_file:
            return image_file.read(), os.path.splitext(image_data)[1].lstrip(".") or "png"

    if folder_paths is not None:
        try:
            image_path = folder_paths.get_annotated_filepath(image_data)
        except Exception:
            image_path = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return image_file.read(), os.path.splitext(image_path)[1].lstrip(".") or "png"

    try:
        return base64.b64decode(image_data), "png"
    except Exception as exc:
        raise ValueError("Image data is not a file path, data URL, or valid base64 image.") from exc


def _pil_to_tensors(pil_image: Image.Image):
    pil_image = ImageOps.exif_transpose(pil_image)

    if pil_image.mode == "I":
        pil_image = pil_image.point(lambda value: value * (1 / 255))

    alpha = None
    if "A" in pil_image.getbands():
        alpha = pil_image.getchannel("A")

    rgb_image = pil_image.convert("RGB")
    image_array = np.asarray(rgb_image).astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image_array)[None,]

    if alpha is None:
        mask_tensor = torch.zeros((rgb_image.height, rgb_image.width), dtype=torch.float32)
    else:
        alpha_array = np.asarray(alpha).astype(np.float32) / 255.0
        mask_tensor = torch.from_numpy(1.0 - alpha_array)

    return image_tensor, mask_tensor


class WANGLoadImageUploadPaste:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_data": ("STRING", {"default": "", "multiline": True}),
                "filename": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "filename", "width", "height")
    FUNCTION = "load_image"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "通过文件选择或 Ctrl+V 粘贴加载图片，并输出遮罩和尺寸。"
    SEARCH_ALIASES = [
        "MengBao",
        "WANGLoadImageUploadPaste",
        "WANG Load Image Upload Paste",
        "Load Image",
        "加载图片",
        "粘贴图片",
    ]

    def load_image(self, image_data: str, filename: str):
        image_bytes, extension = _read_image_bytes(image_data)
        pil_image = Image.open(io.BytesIO(image_bytes))
        image, mask = _pil_to_tensors(pil_image)
        height = int(image.shape[1])
        width = int(image.shape[2])
        clean_name = (filename or "").strip() or f"clipboard_image.{extension}"
        return (image, mask, clean_name, width, height)

    @classmethod
    def IS_CHANGED(cls, image_data: str, filename: str):
        return f"{hash(image_data)}:{filename}"
