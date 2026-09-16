from .auth import register_image_routes
from .material_routes import register_material_routes
from .prompt_routes import register_prompt_routes
from .replica_routes import register_replica_routes


def register_routes() -> None:
    register_image_routes()
    register_prompt_routes()
    register_material_routes()
    register_replica_routes()


__all__ = ["register_routes"]
