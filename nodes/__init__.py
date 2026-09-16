from .ecommerce import (
    NODE_CLASS_MAPPINGS as ECOMMERCE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as ECOMMERCE_DISPLAY_NAME_MAPPINGS,
)
from .image_api import (
    NODE_CLASS_MAPPINGS as IMAGE_API_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as IMAGE_API_DISPLAY_NAME_MAPPINGS,
)
from .image_tools import (
    NODE_CLASS_MAPPINGS as IMAGE_TOOLS_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as IMAGE_TOOLS_DISPLAY_NAME_MAPPINGS,
)
from .prompt import (
    NODE_CLASS_MAPPINGS as PROMPT_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as PROMPT_DISPLAY_NAME_MAPPINGS,
)


ALLOWED_CATEGORIES = {
    "萌宝AI/基础",
    "萌宝AI/图像API",
    "萌宝AI/图像处理",
    "萌宝AI/提示词",
    "萌宝AI/电商",
    "萌宝AI/视频",
    "萌宝AI/工具",
}

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register_nodes(class_mappings, display_name_mappings):
    duplicate_ids = set(NODE_CLASS_MAPPINGS).intersection(class_mappings)
    if duplicate_ids:
        duplicates = ", ".join(sorted(duplicate_ids))
        raise ValueError(f"Duplicate MengBao node IDs: {duplicates}")

    missing_display_names = set(class_mappings).difference(display_name_mappings)
    if missing_display_names:
        missing = ", ".join(sorted(missing_display_names))
        raise ValueError(f"Missing MengBao node display names: {missing}")

    invalid_categories = {
        node_id: getattr(node_class, "CATEGORY", "")
        for node_id, node_class in class_mappings.items()
        if getattr(node_class, "CATEGORY", "") not in ALLOWED_CATEGORIES
    }
    if invalid_categories:
        details = ", ".join(
            f"{node_id}={category or '<missing>'}"
            for node_id, category in sorted(invalid_categories.items())
        )
        raise ValueError(f"Invalid MengBao node categories: {details}")

    NODE_CLASS_MAPPINGS.update(class_mappings)
    NODE_DISPLAY_NAME_MAPPINGS.update(display_name_mappings)


_register_nodes(IMAGE_API_CLASS_MAPPINGS, IMAGE_API_DISPLAY_NAME_MAPPINGS)
_register_nodes(IMAGE_TOOLS_CLASS_MAPPINGS, IMAGE_TOOLS_DISPLAY_NAME_MAPPINGS)
_register_nodes(PROMPT_CLASS_MAPPINGS, PROMPT_DISPLAY_NAME_MAPPINGS)
_register_nodes(ECOMMERCE_CLASS_MAPPINGS, ECOMMERCE_DISPLAY_NAME_MAPPINGS)


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
