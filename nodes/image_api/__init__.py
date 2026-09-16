from .generate import MengBaoImageAPI


NODE_CLASS_MAPPINGS = {
    "WANGImageAPI": MengBaoImageAPI,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WANGImageAPI": "萌宝AI·图像生成",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
