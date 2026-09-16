from .collage import MengBaoSmartCollage
from .constraint import MengBaoImageConstraint
from .image_output import MengBaoPreviewImage, MengBaoSaveImage
from .material_images import MengBaoLoadImage, MengBaoMaterialLibrary
from .split_crop import ImageFreeCrop, ImageGridSplit, ImageGridTilePicker


NODE_CLASS_MAPPINGS = {
    "ImageGridSplit": ImageGridSplit,
    "ImageFreeCrop": ImageFreeCrop,
    "ImageGridTilePicker": ImageGridTilePicker,
    "MengBaoSmartCollage": MengBaoSmartCollage,
    "MengBaoImageConstraint": MengBaoImageConstraint,
    "MengBaoLoadImage": MengBaoLoadImage,
    "MengBaoMaterialLibrary": MengBaoMaterialLibrary,
    "MengBaoSaveImage": MengBaoSaveImage,
    "MengBaoPreviewImage": MengBaoPreviewImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageGridSplit": "萌宝AI·图片拆分",
    "ImageFreeCrop": "萌宝AI·自由裁剪",
    "ImageGridTilePicker": "萌宝AI·网格选图",
    "MengBaoSmartCollage": "萌宝AI·智能拼图",
    "MengBaoImageConstraint": "萌宝AI·图像约束",
    "MengBaoLoadImage": "萌宝AI·加载图片",
    "MengBaoMaterialLibrary": "萌宝AI·素材库",
    "MengBaoSaveImage": "萌宝AI·保存图片",
    "MengBaoPreviewImage": "萌宝AI·预览图片",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
