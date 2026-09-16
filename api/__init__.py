from .auth import register_image_routes
from .prompt_routes import register_prompt_routes


def register_routes() -> None:
    register_image_routes()
    register_prompt_routes()


__all__ = ["register_routes"]
