from ...MengBao_image_api_nodes import MengBaoImageAPI


# 保留历史 ID，确保已有工作流继续识别同一个节点。
NODE_CLASS_MAPPINGS = {
    "WANGImageAPI": MengBaoImageAPI,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WANGImageAPI": "萌宝AI·图像生成",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
