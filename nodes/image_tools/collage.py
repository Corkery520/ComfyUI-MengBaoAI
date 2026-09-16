import math

import torch
import torch.nn.functional as functional


MAX_IMAGE_COUNT = 20


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
                f"image_{index}": ("IMAGE",)
                for index in range(1, MAX_IMAGE_COUNT + 1)
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "collage"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "将一至二十张图片自动排列为无间距拼图，并保持每张图片的宽高比。"
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

    def collage(
        self, image_1=None, image_2=None, image_3=None, image_4=None, **extra_images
    ):
        supported_names = {f"image_{index}" for index in range(5, MAX_IMAGE_COUNT + 1)}
        for name in extra_images:
            if name not in supported_names:
                raise ValueError(f"Unsupported IMAGE input: {name}")
        # 按端口编号而非关键字插入顺序排列，保证工作流重载后的拼图顺序稳定。
        ordered_images = [image_1, image_2, image_3, image_4] + [
            extra_images.get(f"image_{index}")
            for index in range(5, MAX_IMAGE_COUNT + 1)
        ]
        images = [
            _first_frame(image)
            for image in ordered_images
            if image is not None
        ]
        if not images:
            raise ValueError("At least one IMAGE input is required")

        images = _normalize_channels(images)
        # 延续原布局规则，以平方根决定列数，兼容原先 1-4 张的布局。
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
