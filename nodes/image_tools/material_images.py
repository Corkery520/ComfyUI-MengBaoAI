from ...utils.material_store import MATERIAL_STORE
from .load_image import WANGLoadImageUploadPaste


MATERIAL_PREFIX = "mengbao-material:"


def _load_image(path):
    image, mask, *_ = WANGLoadImageUploadPaste().load_image(str(path), "")
    return image, mask.unsqueeze(0)


class MengBaoLoadImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("STRING", {"default": "", "multiline": False})}}

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_image"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "上传、拖拽或 Ctrl+V 粘贴图片，也可从萌宝AI·素材库选择图片。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoLoadImage", "MengBao Load Image", "MengBaoAI Load Image", "萌宝", "萌宝AI", "萌宝AI·加载图片", "萌宝AI 加载图片", "萌宝图片加载", "图片加载", "加载素材"]

    def load_image(self, image):
        image = str(image or "").strip()
        if not image:
            raise ValueError("Please upload an image or select a material first.")
        if image.startswith(MATERIAL_PREFIX):
            image = MATERIAL_STORE.file_path(image[len(MATERIAL_PREFIX):])
        return _load_image(image)

    @classmethod
    def IS_CHANGED(cls, image):
        if str(image).startswith(MATERIAL_PREFIX):
            return MATERIAL_STORE.file_path(str(image)[len(MATERIAL_PREFIX):]).stat().st_mtime_ns
        try:
            from folder_paths import get_annotated_filepath
            from pathlib import Path
            return Path(get_annotated_filepath(image)).stat().st_mtime_ns
        except (ImportError, OSError, ValueError):
            return image


class MengBaoMaterialLibrary:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"material_id": ("STRING", {"default": "", "multiline": False})}}

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_material"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "管理图片素材、分类和收藏，选择素材后输出原图及遮罩。"
    SEARCH_ALIASES = ["Meng", "MengBao", "MengBaoAI", "MengBao AI", "MengBaoMaterialLibrary", "MengBao Material Library", "萌宝", "萌宝AI", "萌宝素材库", "萌宝AI·素材库", "素材库", "素材", "Material Library"]

    def load_material(self, material_id):
        if not str(material_id or "").strip():
            raise ValueError("Please select a material first.")
        return _load_image(MATERIAL_STORE.file_path(material_id))

    @classmethod
    def IS_CHANGED(cls, material_id):
        return MATERIAL_STORE.file_path(material_id).stat().st_mtime_ns if material_id else ""
