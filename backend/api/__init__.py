from .routes_robots import router as robots_router
from .routes_command import router as command_router
from .routes_tasks import router as tasks_router
from .routes_vision import router as vision_router

__all__ = ["robots_router", "command_router", "tasks_router", "vision_router"]
