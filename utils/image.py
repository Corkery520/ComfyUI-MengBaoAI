import io
import json
from typing import Any, Iterable, List, Optional

import numpy as np
import torch
from PIL import Image, ImageDraw


def normalize_ui_language(value: str) -> str:
    return "zh" if str(value or "").lower().startswith("zh") else "en"


def json_text(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return str(payload)


def image_tensor_to_png_bytes(
    image: torch.Tensor, *, compress_level: int = 6, force_rgba: bool = True
) -> bytes:
    if image.dim() == 4:
        image = image[0]
    if image.dim() != 3:
        raise ValueError(
            "IMAGE input must be [height, width, channels] or "
            "[batch, height, width, channels]"
        )

    array = image.detach().cpu().numpy()
    array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
    pil_image = Image.fromarray(array)
    if force_rgba and pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG", compress_level=compress_level)
    return buffer.getvalue()


def png_bytes_to_image_tensor(data: bytes) -> torch.Tensor:
    source = Image.open(io.BytesIO(data))
    output_mode = "RGBA" if "A" in source.getbands() else "RGB"
    pil_image = source.convert(output_mode)
    array = np.array(pil_image, dtype=np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def optional_images(
    images: Iterable[Optional[torch.Tensor]],
    limit: int,
) -> List[bytes]:
    encoded: List[bytes] = []
    for image in images:
        if image is None:
            continue
        batches = image if image.dim() == 4 else image.unsqueeze(0)
        for batch_image in batches:
            encoded.append(image_tensor_to_png_bytes(batch_image))
            if len(encoded) >= limit:
                return encoded
    return encoded


def _message_image_title(ui_language: str) -> str:
    if normalize_ui_language(ui_language) == "zh":
        return "萌宝AI·图像生成未收到图片"
    return "MengBao AI · Image Generation did not receive an image"


def message_image(
    message: str,
    ui_language: str = "en",
    width: int = 1024,
    height: int = 768,
) -> torch.Tensor:
    pil_image = Image.new("RGB", (width, height), (28, 28, 28))
    draw = ImageDraw.Draw(pil_image)
    lines = [_message_image_title(ui_language), ""]
    clean = (message or "").replace("\r", "\n")
    for raw_line in clean.split("\n"):
        raw_line = raw_line.strip()
        while len(raw_line) > 72:
            lines.append(raw_line[:72])
            raw_line = raw_line[72:]
        if raw_line:
            lines.append(raw_line)
        if len(lines) >= 28:
            lines.append("...")
            break

    y = 28
    for index, line in enumerate(lines):
        color = (255, 120, 120) if index == 0 else (235, 235, 235)
        draw.text((28, y), line, fill=color)
        y += 24

    array = np.asarray(pil_image).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def cat_images(
    images: List[torch.Tensor],
    fallback_text: str,
    ui_language: str = "en",
) -> torch.Tensor:
    if not images:
        return message_image(fallback_text, ui_language)

    target_height = images[0].shape[1]
    target_width = images[0].shape[2]
    target_channels = images[0].shape[3]
    normalized: List[torch.Tensor] = []
    for image in images:
        normalized_image = image
        if normalized_image.shape[3] != target_channels:
            if target_channels == 4 and normalized_image.shape[3] == 3:
                alpha = torch.ones(
                    (*normalized_image.shape[:3], 1),
                    dtype=normalized_image.dtype,
                )
                normalized_image = torch.cat([normalized_image, alpha], dim=3)
            else:
                normalized_image = normalized_image[:, :, :, :target_channels]
        if normalized_image.shape[1:3] != (target_height, target_width):
            channels_first = normalized_image.movedim(-1, 1)
            resized = torch.nn.functional.interpolate(
                channels_first,
                size=(target_height, target_width),
                mode="bilinear",
                align_corners=False,
            )
            normalized_image = resized.movedim(1, -1)
        normalized.append(normalized_image)
    return torch.cat(normalized, dim=0).contiguous()
