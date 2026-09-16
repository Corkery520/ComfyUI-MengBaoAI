import math

import torch
import torch.nn.functional as functional

from ...utils.image import image_tensor_to_png_bytes


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


def _constrain_file_size(image, max_file_size_mb):
    limit = float(max_file_size_mb)
    if not math.isfinite(limit) or limit < 0:
        raise ValueError("Maximum file size must be a finite non-negative number")
    if limit == 0:
        return image.contiguous()

    max_bytes = int(limit * 1024 * 1024)
    source = image
    source_height, source_width = source.shape[1:3]
    scale = 1.0
    while True:
        # 同时检查 ComfyUI 保存常用压缩级别和 API 编码级别，不用张量内存估算文件大小。
        largest_size = max(
            max(
                len(image_tensor_to_png_bytes(frame, compress_level=4, force_rgba=False)),
                len(image_tensor_to_png_bytes(frame)),
            )
            for frame in image
        )
        if largest_size <= max_bytes:
            return image.contiguous()
        height, width = image.shape[1:3]
        if height == 1 and width == 1:
            raise ValueError("Maximum file size is too small to encode even a 1x1 PNG")

        # 编码体积与像素数量不是严格线性关系，每次缩小后必须重新编码验证。
        scale *= min(0.95, math.sqrt(max_bytes / largest_size) * 0.95)
        target_height = max(1, int(source_height * scale))
        target_width = max(1, int(source_width * scale))
        image = _resize(source, target_height, target_width)


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
                "max_file_size_mb": (
                    "FLOAT",
                    {
                        "default": 10.0,
                        "min": 0.0,
                        "max": 1024.0,
                        "step": 0.1,
                        "tooltip": "单张 PNG 最大体积（1 MB = 1024×1024 字节），0 为不限。超限时等比缩小，体积限制优先于最小尺寸；不包含保存节点追加的元数据。",
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "constrain"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "保持宽高比约束图片尺寸和单张 PNG 体积，默认不超过 10 MB，必要时可居中裁剪。"
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
        "图片大小限制",
    ]

    def constrain(
        self,
        image,
        max_width,
        max_height,
        min_width,
        min_height,
        crop_if_required,
        max_file_size_mb=10.0,
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
            return (
                _constrain_file_size(
                    _resize(image, target_height, target_width), max_file_size_mb
                ),
            )

        # 最大和最小尺寸互相冲突时，默认优先保证不超过最大尺寸。
        contained_scale = upper_scale if math.isfinite(upper_scale) else 1.0
        contained_width = max(1, int(source_width * contained_scale))
        contained_height = max(1, int(source_height * contained_scale))
        if crop_if_required != "yes":
            return (
                _constrain_file_size(
                    _resize(image, contained_height, contained_width), max_file_size_mb
                ),
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
        return (_constrain_file_size(cropped, max_file_size_mb),)
