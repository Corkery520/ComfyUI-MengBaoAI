from .settings import MengBaoEcommerceSettings
from .replica import MengBaoImageReverse, MengBaoImageReplicaSettings, MengBaoReplicaAudit


NODE_CLASS_MAPPINGS = {
    "MengBaoEcommerceSettings": MengBaoEcommerceSettings,
    "MengBaoImageReverse": MengBaoImageReverse,
    "MengBaoImageReplicaSettings": MengBaoImageReplicaSettings,
    "MengBaoReplicaAudit": MengBaoReplicaAudit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MengBaoEcommerceSettings": "萌宝AI·电商设置",
    "MengBaoImageReverse": "萌宝AI·图片反推",
    "MengBaoImageReplicaSettings": "萌宝AI·图片复刻设置",
    "MengBaoReplicaAudit": "萌宝AI·复刻检查",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
