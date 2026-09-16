from .load_image import WANGLoadImageUploadPaste
from .split_crop import ImageFreeCrop, ImageGridSplit, ImageGridTilePicker


NODE_CLASS_MAPPINGS = {
    "ImageGridSplit": ImageGridSplit,
    "ImageFreeCrop": ImageFreeCrop,
    "ImageGridTilePicker": ImageGridTilePicker,
    "WANGLoadImageUploadPaste": WANGLoadImageUploadPaste,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageGridSplit": "萌宝AI·图片拆分",
    "ImageFreeCrop": "萌宝AI·自由裁剪",
    "ImageGridTilePicker": "萌宝AI·网格选图",
    "WANGLoadImageUploadPaste": "萌宝AI·加载图片",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
