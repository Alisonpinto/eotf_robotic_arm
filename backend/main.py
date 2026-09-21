import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import sys
import time

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

try:
    from api import robots_router, command_router, tasks_router, vision_router
    from robots.manager import robot_manager
    from tasks.task_manager import task_manager
except ImportError:
    from .api import robots_router, command_router, tasks_router, vision_router
    from .robots.manager import robot_manager
    from .tasks.task_manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("==================================================")
    print("  ROBOT-AI PLATFORM: BACKEND SERVER ONLINE")
    print("  Arms Registered : DIY 3D-Printed Arm, Hiwonder JetArm")
    print("  Simulation Mode : ACTIVE (Hardware Interfaces Ready)")
    print("  Vision Stream   : ACTIVE (OpenCV Engine on /api/vision/stream)")
    print("==================================================")
    yield
    print("ROBOT-AI Platform backend shutting down.")


app = FastAPI(
    title="Robot-AI Dual 6-DOF Robotic Arm Control Platform",
    description="Full-stack AI robotic-arm control platform controlling DIY Arm and Hiwonder JetArm",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend (default port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(robots_router)
app.include_router(command_router)
app.include_router(tasks_router)
app.include_router(vision_router)


@app.get("/api/status")
async def system_status():
    """System health check and global platform telemetry."""
    active_task = task_manager.get_active_task()
    return {
        "status": "online",
        "platform": "Robot-AI Core",
        "simulation_mode": True,
        "robots_online": len(robot_manager.list_robots()),
        "active_task_id": active_task.task_id if active_task else None,
        "system_time": time.time(),
    }


@app.websocket("/ws/status")
async def websocket_status_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint streaming live arm telemetry and task status at 10Hz.
    Allows real-time, low-latency UI synchronization.
    """
    await websocket.accept()
    try:
        while True:
            statuses = [s.model_dump() for s in robot_manager.get_all_statuses()]
            active = task_manager.get_active_task()
            payload = {
                "timestamp": time.time(),
                "robots": statuses,
                "active_task": active.model_dump() if active else None,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.1)  # 10 Hz broadcast
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
