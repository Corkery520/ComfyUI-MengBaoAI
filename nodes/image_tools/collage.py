import math

import torch
import torch.nn.functional as functional


def _first_frame(image):
    if not isinstance(image, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if image.dim() != 4 or image.shape[0] < 1:
        raise ValueError("IMAGE input must have shape [batch, height, width, channels]")
    return image[:1]


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


def _resize_to_height(image, target_height):
    source_height, source_width = image.shape[1:3]
    target_width = max(1, int(source_width * target_height / source_height))
    return _resize(image, target_height, target_width)


def _resize_to_width(image, target_width):
    source_height, source_width = image.shape[1:3]
    target_height = max(1, int(source_height * target_width / source_width))
    return _resize(image, target_height, target_width)


def _normalize_channels(images):
    target_channels = 4 if any(image.shape[3] == 4 for image in images) else 3
    normalized = []
    for image in images:
        channels = image.shape[3]
        if channels == target_channels:
            normalized.append(image)
        elif channels == 1:
            rgb = image.repeat(1, 1, 1, 3)
            if target_channels == 4:
                alpha = torch.ones_like(rgb[:, :, :, :1])
                rgb = torch.cat([rgb, alpha], dim=3)
            normalized.append(rgb)
        elif channels == 3 and target_channels == 4:
            alpha = torch.ones_like(image[:, :, :, :1])
            normalized.append(torch.cat([image, alpha], dim=3))
        else:
            normalized.append(image[:, :, :, :target_channels])
    return normalized


class MengBaoSmartCollage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "collage"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "将一至四张图片自动排列为无间距拼图，并保持每张图片的宽高比。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "MengBaoSmartCollage",
        "MengBao AI Smart Collage",
        "Smart Collage",
        "Smart Grid",
        "萌宝",
        "萌宝AI",
        "萌宝AI 智能拼图",
        "智能拼图",
        "图片拼接",
        "拼图",
    ]

    def collage(self, image_1=None, image_2=None, image_3=None, image_4=None):
        images = [
            _first_frame(image)
            for image in (image_1, image_2, image_3, image_4)
            if image is not None
        ]
        if not images:
            raise ValueError("At least one IMAGE input is required")

        images = _normalize_channels(images)
        # 参考节点在 1-3 张时使用单列，满 4 张时自动切换为 2x2。
        columns = max(1, int(math.sqrt(len(images))))
        rows = []
        for start in range(0, len(images), columns):
            row_images = images[start : start + columns]
            row_height = max(image.shape[1] for image in row_images)
            normalized_row = [
                _resize_to_height(image, row_height) for image in row_images
            ]
            rows.append(torch.cat(normalized_row, dim=2))

        # 每行再次等比对齐到最宽行，最终纵向无间距拼接。
        canvas_width = max(row.shape[2] for row in rows)
        normalized_rows = [_resize_to_width(row, canvas_width) for row in rows]
        return (torch.cat(normalized_rows, dim=1).contiguous(),)
