import asyncio
import cv2
import math
import numpy as np
import time
from typing import AsyncGenerator, Dict, List, Optional, Any, Tuple

try:
    from vision.detector import BaseVisionDetector, DetectedObject, vision_detector
    from vision.camera import camera_manager, CameraManager
except ImportError:
    from .detector import BaseVisionDetector, DetectedObject, vision_detector
    from .camera import camera_manager, CameraManager


class VisionProcessor:
    """
    OpenCV Computer Vision Processor & Stream Engine.
    
    Capabilities:
    1. Manages live camera feed from CameraManager (default laptop webcam).
    2. Runs real-time object detection (YOLO / OpenCV) on incoming frames.
    3. Annotates live frames with:
       - Bounding boxes (colored by detected object or class)
       - Object label, color, and confidence score
       - Center X/Y pixel coordinates and reticle
       - Camera HUD header (timestamp, resolution, image coordinates notice)
    4. Provides asynchronous MJPEG stream for real-time web display.
    5. Exposes camera start/stop/status controls without changing detection pipelines.
    """

    def __init__(self):
        self.camera = camera_manager
        self.detector = vision_detector
        self.width = 640
        self.height = 480
        self._last_detections: List[DetectedObject] = []
        self._last_detection_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._last_fps_count = 0
        self._active_target: Optional[Dict[str, Any]] = None

    def start_camera(self) -> bool:
        """Start the active camera source (laptop webcam by default)."""
        return self.camera.start()

    def stop_camera(self) -> None:
        """Stop the camera stream."""
        self.camera.stop()
        self._last_detections = []

    def is_camera_running(self) -> bool:
        return self.camera.is_running()

    def get_camera_status(self) -> Dict[str, Any]:
        status = self.camera.get_status()
        status["stream_fps"] = self._fps
        status["active_detections_count"] = len(self._last_detections)
        status["has_active_target"] = self._active_target is not None
        return status

    def set_active_target(self, target: Optional[Any]) -> None:
        """Set or update the active target object to highlight on the live stream."""
        if target is None:
            self._active_target = None
        elif isinstance(target, dict):
            self._active_target = target
        elif hasattr(target, "model_dump"):
            self._active_target = target.model_dump()
        else:
            self._active_target = None

    def clear_active_target(self) -> None:
        self._active_target = None

    def generate_standby_frame(self) -> np.ndarray:
        """Render a clean high-tech standby canvas when the webcam is paused."""
        frame = np.full((self.height, self.width, 3), (20, 24, 30), dtype=np.uint8)

        # Subtle dark grid
        grid_step = 40
        for x in range(0, self.width, grid_step):
            cv2.line(frame, (x, 0), (x, self.height), (30, 36, 46), 1)
        for y in range(0, self.height, grid_step):
            cv2.line(frame, (0, y), (self.width, y), (30, 36, 46), 1)

        # Standby text banner
        cx, cy = self.width // 2, self.height // 2
        cv2.circle(frame, (cx, cy - 20), 30, (45, 55, 70), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy - 20), 6, (0, 210, 255), -1, cv2.LINE_AA)

        title = "CAMERA STANDBY"
        subtitle = "Click 'Start Camera' to open laptop webcam"
        (tw1, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        (tw2, _), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)

        cv2.putText(frame, title, (cx - tw1 // 2, cy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 230, 245), 2, cv2.LINE_AA)
        cv2.putText(frame, subtitle, (cx - tw2 // 2, cy + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (130, 145, 165), 1, cv2.LINE_AA)

        # HUD header
        cv2.rectangle(frame, (0, 0), (self.width, 28), (14, 18, 24), -1)
        cv2.line(frame, (0, 28), (self.width, 28), (35, 45, 60), 1)
        cv2.putText(frame, "CAM-01: LAPTOP WEBCAM [STANDBY]", (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 155, 175), 1, cv2.LINE_AA)
        cv2.putText(frame, time.strftime("%H:%M:%S UTC"), (self.width - 110, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 135, 155), 1, cv2.LINE_AA)

        return frame

    def annotate_frame(self, frame: np.ndarray, detections: List[DetectedObject]) -> np.ndarray:
        """
        Draw detected objects on the live frames:
        - Bounding box
        - Object name
        - Confidence percentage
        - Center X/Y coordinates (point, crosshair, label)
        - Color attribute
        - Camera status and coordinate frame HUD
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw HUD header bar
        cv2.rectangle(annotated, (0, 0), (w, 28), (12, 16, 22), -1)
        cv2.line(annotated, (0, 28), (w, 28), (40, 50, 65), 1)

        source_name = "LAPTOP WEBCAM" if self.camera.is_running() else "SYNTHETIC WORKSPACE"
        hud_left = f"CAM-01: {source_name} [IMAGE COORDS: PIXELS]"
        hud_right = f"FPS: {self._fps:.1f} | OBJS: {len(detections)}"

        cv2.putText(annotated, hud_left, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 230, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, hud_right, (w - 170, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 180, 205), 1, cv2.LINE_AA)

        # Draw each detected object
        for obj in detections:
            x1, y1 = obj.bounding_box.x1, obj.bounding_box.y1
            x2, y2 = obj.bounding_box.x2, obj.bounding_box.y2
            cx, cy = obj.center.x, obj.center.y

            # Check if this object is the currently active/selected target
            is_target = False
            if self._active_target:
                t_name = str(self._active_target.get("name", "")).lower().strip()
                t_color = str(self._active_target.get("color", "")).lower().strip() if self._active_target.get("color") else None
                t_center = self._active_target.get("center", {})
                tcx = t_center.get("x") if isinstance(t_center, dict) else getattr(t_center, "x", None)
                tcy = t_center.get("y") if isinstance(t_center, dict) else getattr(t_center, "y", None)

                if tcx is not None and tcy is not None and abs(cx - tcx) < 45 and abs(cy - tcy) < 45:
                    is_target = True
                elif t_name and obj.name.lower() == t_name:
                    if not t_color or (obj.color and obj.color.lower() == t_color):
                        is_target = True

            # Determine box color based on target status or detected color
            if is_target:
                color_bgr = (0, 255, 120)  # Vibrant emerald target lock
            elif obj.color == "red":
                color_bgr = (40, 40, 235)
            elif obj.color == "blue":
                color_bgr = (235, 140, 30)
            elif obj.color == "green":
                color_bgr = (50, 210, 60)
            elif obj.color == "yellow":
                color_bgr = (30, 220, 235)
            elif obj.color == "orange":
                color_bgr = (20, 140, 245)
            elif obj.color == "purple":
                color_bgr = (200, 60, 160)
            elif obj.color == "black":
                color_bgr = (80, 80, 80)
            elif obj.color == "white":
                color_bgr = (230, 230, 230)
            else:
                color_bgr = (0, 255, 200)

            # 1. Bounding box (double box if target locked)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 3 if is_target else 2)
            if is_target:
                cv2.rectangle(annotated, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), (0, 255, 120), 1)

            # 2. Corner markers for sleek high-tech robotic aesthetic
            corner_len = min(20 if is_target else 16, max(6, (x2 - x1) // 5))
            thick = 4 if is_target else 3
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), color_bgr, thick)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), color_bgr, thick)
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), color_bgr, thick)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), color_bgr, thick)
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), color_bgr, thick)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), color_bgr, thick)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), color_bgr, thick)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), color_bgr, thick)

            # 3. Center point and crosshair
            cv2.circle(annotated, (cx, cy), 5 if is_target else 4, color_bgr, -1, cv2.LINE_AA)
            cv2.circle(annotated, (cx, cy), 12 if is_target else 8, (255, 255, 255), 1, cv2.LINE_AA)
            if is_target:
                cv2.circle(annotated, (cx, cy), 18, color_bgr, 1, cv2.LINE_AA)
            cv2.line(annotated, (cx - (18 if is_target else 12), cy), (cx + (18 if is_target else 12), cy), color_bgr, 1, cv2.LINE_AA)
            cv2.line(annotated, (cx, cy - (18 if is_target else 12)), (cx, cy + (18 if is_target else 12)), color_bgr, 1, cv2.LINE_AA)

            # Center X/Y coordinate badge
            center_label = f"[{cx},{cy}]"
            cv2.putText(
                annotated,
                center_label,
                (cx + 8, cy - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

            # 4. Top label banner: [Color] Name Confidence% or TARGET LOCKED
            color_prefix = f"{obj.color.upper()} " if obj.color else ""
            if is_target:
                label_text = f"TARGET LOCKED: {color_prefix}{obj.name.upper()} {int(obj.confidence * 100)}%"
            else:
                label_text = f"{color_prefix}{obj.name.upper()} {int(obj.confidence * 100)}%"

            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)

            banner_y1 = max(30, y1 - th - 8)
            banner_y2 = banner_y1 + th + 6
            cv2.rectangle(annotated, (x1, banner_y1), (x1 + tw + 10, banner_y2), (15, 18, 24), -1)
            cv2.rectangle(annotated, (x1, banner_y1), (x1 + tw + 10, banner_y2), color_bgr, 1)
            cv2.putText(
                annotated,
                label_text,
                (x1 + 5, banner_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color_bgr,
                1,
                cv2.LINE_AA,
            )

        return annotated

    def get_raw_frame(self) -> np.ndarray:
        """Get current unannotated frame from active camera or fallback."""
        if self.camera.is_running():
            frame = self.camera.get_frame()
            if frame is not None:
                return frame
        return self.generate_standby_frame()

    def process_frame(self) -> Tuple[np.ndarray, List[DetectedObject]]:
        """Grab current frame, run object detector, and return annotated frame with detections."""
        raw_frame = self.get_raw_frame()

        if self.camera.is_running():
            detections = self.detector.detect(raw_frame)
            self._last_detections = detections
            self._last_detection_time = time.time()
        else:
            detections = []
            self._last_detections = []

        annotated = self.annotate_frame(raw_frame, detections)

        # Update FPS calculation
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self._fps = round((self._frame_count - self._last_fps_count) / elapsed, 1)
            self._last_fps_time = now
            self._last_fps_count = self._frame_count

        return annotated, detections

    def get_frame_jpeg(self) -> bytes:
        annotated, _ = self.process_frame()
        ret, buffer = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ret:
            return b""
        return buffer.tobytes()

    async def generate_mjpeg_stream(self) -> AsyncGenerator[bytes, None]:
        """Asynchronous generator streaming annotated MJPEG frames at ~25-30 FPS."""
        while True:
            frame_bytes = self.get_frame_jpeg()
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
                    + frame_bytes + b"\r\n"
                )
            await asyncio.sleep(0.035)

    def get_detections(self) -> List[DetectedObject]:
        """Return the latest detected objects from the live camera stream."""
        if self.camera.is_running():
            raw_frame = self.camera.get_frame()
            if raw_frame is not None:
                self._last_detections = self.detector.detect(raw_frame)
        return self._last_detections


# Singleton vision processor
vision_processor = VisionProcessor()
