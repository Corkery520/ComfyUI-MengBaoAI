from .image import (
    NODE_CLASS_MAPPINGS as IMAGE_NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as IMAGE_NODE_DISPLAY_NAME_MAPPINGS,
)


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

    NODE_CLASS_MAPPINGS.update(class_mappings)
    NODE_DISPLAY_NAME_MAPPINGS.update(display_name_mappings)


_register_nodes(IMAGE_NODE_CLASS_MAPPINGS, IMAGE_NODE_DISPLAY_NAME_MAPPINGS)


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
