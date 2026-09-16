import torch


def _ensure_image_tensor(image):
    if not isinstance(image, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("IMAGE input must have shape [batch, height, width, channels]")
    return image


def _clamp_int(value, minimum, maximum):
    return max(minimum, min(int(value), maximum))


class ImageGridSplit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "grid": (["2x2", "3x3", "4x4", "custom"], {"default": "2x2"}),
                "custom_rows": ("INT", {"default": 2, "min": 1, "max": 16, "step": 1}),
                "custom_cols": ("INT", {"default": 2, "min": 1, "max": 16, "step": 1}),
                "trim_to_even_tiles": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT")
    RETURN_NAMES = ("tiles", "rows", "columns", "tile_count")
    FUNCTION = "split"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "将图片按 2x2、3x3、4x4 或自定义网格拆分为图片批次。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "ImageGridSplit",
        "Image Grid Split",
        "MengBaoAI Image Split",
        "萌宝",
        "萌宝AI",
        "萌宝AI 图片拆分",
        "图片拆分",
        "九宫格",
    ]

    def split(self, image, grid, custom_rows, custom_cols, trim_to_even_tiles):
        image = _ensure_image_tensor(image)

        if grid == "custom":
            rows = int(custom_rows)
            cols = int(custom_cols)
        else:
            rows, cols = (int(part) for part in grid.split("x", 1))

        batch, height, width, channels = image.shape
        tile_h = height // rows
        tile_w = width // cols

        if tile_h < 1 or tile_w < 1:
            raise ValueError("Grid is too large for the input image size")

        if trim_to_even_tiles:
            usable_h = tile_h * rows
            usable_w = tile_w * cols
            top = (height - usable_h) // 2
            left = (width - usable_w) // 2
            image = image[:, top : top + usable_h, left : left + usable_w, :]
        else:
            # Resize by interpolation so each tile has the same output shape.
            usable_h = tile_h * rows
            usable_w = tile_w * cols
            chw = image.movedim(-1, 1)
            chw = torch.nn.functional.interpolate(
                chw,
                size=(usable_h, usable_w),
                mode="bilinear",
                align_corners=False,
            )
            image = chw.movedim(1, -1)

        tiles = []
        for row in range(rows):
            y0 = row * tile_h
            y1 = y0 + tile_h
            for col in range(cols):
                x0 = col * tile_w
                x1 = x0 + tile_w
                tiles.append(image[:, y0:y1, x0:x1, :])

        return (torch.cat(tiles, dim=0).contiguous(), rows, cols, rows * cols)


class ImageFreeCrop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1}),
                "y": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1}),
                "width": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
                "height": ("INT", {"default": 512, "min": 1, "max": 16384, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("cropped_image", "x", "y", "width", "height")
    FUNCTION = "crop"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "按像素坐标和尺寸自由裁剪图片。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "ImageFreeCrop",
        "Image Free Crop",
        "MengBaoAI Image Crop",
        "萌宝",
        "萌宝AI",
        "萌宝AI 自由裁剪",
        "自由裁剪",
        "图片裁剪",
    ]

    def crop(self, image, x, y, width, height):
        image = _ensure_image_tensor(image)
        _, image_h, image_w, _ = image.shape

        x0 = _clamp_int(x, 0, image_w - 1)
        y0 = _clamp_int(y, 0, image_h - 1)
        x1 = _clamp_int(x0 + width, x0 + 1, image_w)
        y1 = _clamp_int(y0 + height, y0 + 1, image_h)

        cropped = image[:, y0:y1, x0:x1, :].contiguous()
        return (cropped, x0, y0, x1 - x0, y1 - y0)


class ImageGridTilePicker:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "grid": (["2x2", "3x3", "4x4", "custom"], {"default": "2x2"}),
                "custom_rows": ("INT", {"default": 2, "min": 1, "max": 16, "step": 1}),
                "custom_cols": ("INT", {"default": 2, "min": 1, "max": 16, "step": 1}),
                "row": ("INT", {"default": 1, "min": 1, "max": 16, "step": 1}),
                "column": ("INT", {"default": 1, "min": 1, "max": 16, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("tile", "row", "column")
    FUNCTION = "pick"
    CATEGORY = "萌宝AI/图像处理"
    DESCRIPTION = "从网格中选择指定行列的单张图片。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "ImageGridTilePicker",
        "Image Grid Tile Picker",
        "MengBaoAI Grid Tile Picker",
        "萌宝",
        "萌宝AI",
        "萌宝AI 网格选图",
        "网格选图",
    ]

    def pick(self, image, grid, custom_rows, custom_cols, row, column):
        image = _ensure_image_tensor(image)

        if grid == "custom":
            rows = int(custom_rows)
            cols = int(custom_cols)
        else:
            rows, cols = (int(part) for part in grid.split("x", 1))

        _, height, width, _ = image.shape
        tile_h = height // rows
        tile_w = width // cols

        if tile_h < 1 or tile_w < 1:
            raise ValueError("Grid is too large for the input image size")

        picked_row = _clamp_int(row, 1, rows)
        picked_col = _clamp_int(column, 1, cols)
        y0 = (picked_row - 1) * tile_h
        x0 = (picked_col - 1) * tile_w

        tile = image[:, y0 : y0 + tile_h, x0 : x0 + tile_w, :].contiguous()
        return (tile, picked_row, picked_col)
