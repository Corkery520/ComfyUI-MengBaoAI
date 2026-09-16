from .collage import MengBaoSmartCollage
from .constraint import MengBaoImageConstraint
from .load_image import WANGLoadImageUploadPaste
from .split_crop import ImageFreeCrop, ImageGridSplit, ImageGridTilePicker


NODE_CLASS_MAPPINGS = {
    "ImageGridSplit": ImageGridSplit,
    "ImageFreeCrop": ImageFreeCrop,
    "ImageGridTilePicker": ImageGridTilePicker,
    "WANGLoadImageUploadPaste": WANGLoadImageUploadPaste,
    "MengBaoSmartCollage": MengBaoSmartCollage,
    "MengBaoImageConstraint": MengBaoImageConstraint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageGridSplit": "萌宝AI·图片拆分",
    "ImageFreeCrop": "萌宝AI·自由裁剪",
    "ImageGridTilePicker": "萌宝AI·网格选图",
    "WANGLoadImageUploadPaste": "萌宝AI·加载图片",
    "MengBaoSmartCollage": "萌宝AI智能拼图",
    "MengBaoImageConstraint": "萌宝图像约束",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
