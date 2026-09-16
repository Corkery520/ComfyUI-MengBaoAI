from .organizer import WANGPromptOrganizer, WANGPromptReader


NODE_CLASS_MAPPINGS = {
    "WANGPromptOrganizer": WANGPromptOrganizer,
    "WANGPromptReader": WANGPromptReader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WANGPromptOrganizer": "萌宝AI·提示词整理器",
    "WANGPromptReader": "萌宝AI·提示词读取",
}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
