import math

import torch
import torch.nn.functional as functional


def _ensure_image_tensor(image):
    if not isinstance(image, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("IMAGE input must have shape [batch, height, width, channels]")
    return image


def _resize(image, height, width):
    height = max(1, int(height))
    width = max(1, int(width))
    if image.shape[1:3] == (height, width):
        return image
    resized = functional.interpolate(
        image.movedim(-1, 1),
        size=(height, width),
        mode="bilinear",
        align_corners=False,
    )
    return resized.movedim(1, -1)


def _scale_bounds(width, height, max_width, max_height, min_width, min_height):
    lower = max(
        min_width / width if min_width else 0.0,
        min_height / height if min_height else 0.0,
    )
    upper = min(
        max_width / width if max_width else math.inf,
        max_height / height if max_height else math.inf,
    )
    return lower, upper


class MengBaoImageConstraint:
    @classmethod
    def INPUT_TYPES(cls):
        dimension = {"default": 2048, "min": 0, "max": 16384, "step": 8}
        minimum = {"default": 0, "min": 0, "max": 16384, "step": 8}
        return {
            "required": {
                "image": ("IMAGE",),
                "max_width": ("INT", dict(dimension)),
                "max_height": ("INT", dict(dimension)),
                "min_width": ("INT", dict(minimum)),
                "min_height": ("INT", dict(minimum)),
                "crop_if_required": (["no", "yes"], {"default": "no"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "constrain"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "在保持宽高比的前提下约束图片尺寸，必要时可居中裁剪。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "MengBaoImageConstraint",
        "MengBao AI Image Constraint",
        "Image Constraint",
        "Constrain Image",
        "萌宝",
        "萌宝AI",
        "萌宝 图像约束",
        "萌宝图像约束",
        "图像约束",
        "图片尺寸限制",
    ]

    def constrain(
        self,
        image,
        max_width,
        max_height,
        min_width,
        min_height,
        crop_if_required,
    ):
        image = _ensure_image_tensor(image)
        source_height, source_width = image.shape[1:3]
        max_width = max(0, int(max_width))
        max_height = max(0, int(max_height))
        min_width = max(0, int(min_width))
        min_height = max(0, int(min_height))
        lower_scale, upper_scale = _scale_bounds(
            source_width,
            source_height,
            max_width,
            max_height,
            min_width,
            min_height,
        )

        if lower_scale <= upper_scale:
            scale = min(max(1.0, lower_scale), upper_scale)
            target_width = max(1, int(source_width * scale))
            target_height = max(1, int(source_height * scale))
            return (_resize(image, target_height, target_width).contiguous(),)

        # 最大和最小尺寸互相冲突时，默认优先保证不超过最大尺寸。
        contained_scale = upper_scale if math.isfinite(upper_scale) else 1.0
        contained_width = max(1, int(source_width * contained_scale))
        contained_height = max(1, int(source_height * contained_scale))
        if crop_if_required != "yes":
            return (
                _resize(image, contained_height, contained_width).contiguous(),
            )

        target_width = max(contained_width, min_width)
        target_height = max(contained_height, min_height)
        if max_width:
            target_width = min(target_width, max_width)
        if max_height:
            target_height = min(target_height, max_height)

        cover_scale = max(
            target_width / source_width,
            target_height / source_height,
        )
        resized_width = max(target_width, int(math.ceil(source_width * cover_scale)))
        resized_height = max(target_height, int(math.ceil(source_height * cover_scale)))
        resized = _resize(image, resized_height, resized_width)
        left = (resized_width - target_width) // 2
        top = (resized_height - target_height) // 2
        cropped = resized[
            :,
            top : top + target_height,
            left : left + target_width,
            :,
        ]
        return (cropped.contiguous(),)
