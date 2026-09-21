from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Union
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    class _MockImg:
        def __init__(self, shape):
            self.shape = shape
            self.size = shape[0] * shape[1] if len(shape) >= 2 else 1
        def copy(self):
            return self

    class _NpMock:
        uint8 = int
        float32 = float
        ndarray = _MockImg
        @staticmethod
        def array(x, *a, **k):
            return x
        @staticmethod
        def full(shape, fill_value, dtype=None):
            return _MockImg(shape)
        @staticmethod
        def zeros(shape, dtype=None):
            return _MockImg(shape)
        @staticmethod
        def ones(shape, dtype=None):
            return _MockImg(shape)
    np = _NpMock()

if cv2 is None:
    class _Cv2Mock:
        FONT_HERSHEY_SIMPLEX = 0
        LINE_AA = 16
        MORPH_RECT = 0
        MORPH_OPEN = 2
        MORPH_CLOSE = 3
        RETR_EXTERNAL = 0
        CHAIN_APPROX_SIMPLE = 1
        COLOR_BGR2HSV = 40
        @staticmethod
        def line(*a, **k): pass
        @staticmethod
        def rectangle(*a, **k): pass
        @staticmethod
        def ellipse(*a, **k): pass
        @staticmethod
        def circle(*a, **k): pass
        @staticmethod
        def putText(*a, **k): pass
    cv2 = _Cv2Mock()

import os
import threading
import time


class CameraSource(ABC):
    """
    Abstract Base Class for camera input sources in the Robot-AI Vision Subsystem.
    Allows switching between:
    - Laptop webcam (WebcamCamera)
    - Video files (VideoFileCamera)
    - Future network / USB phone camera (FutureNetworkCamera)
    without modifying the object detection or downstream pipelines.
    """

    @abstractmethod
    def start(self) -> bool:
        """Start the camera stream and background grabber thread."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the camera stream and release hardware/network resources."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Return True if the camera is currently actively capturing frames."""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        """Retrieve the latest captured frame in BGR format."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status dictionary for the camera."""
        pass

    # Static utility methods preserved for test image uploads and offline synthesis
    @staticmethod
    def load_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
        """Decode raw image bytes (JPEG, PNG, etc.) into an OpenCV BGR numpy array."""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"[CameraSource] Failed to decode image from bytes: {e}")
            return None

    @staticmethod
    def load_from_file(file_path: str) -> Optional[np.ndarray]:
        """Load an image file from the local filesystem."""
        if not os.path.exists(file_path):
            print(f"[CameraSource] File not found: {file_path}")
            return None
        return cv2.imread(file_path, cv2.IMREAD_COLOR)

    @staticmethod
    def generate_sample_workbench_image(width: int = 640, height: int = 480) -> np.ndarray:
        """
        Synthesize a realistic test workbench image containing colored objects:
        - Red bottle
        - Blue cup
        - Green box
        - Yellow canister
        """
        img = np.full((height, width, 3), (38, 42, 48), dtype=np.uint8)

        # Workbench grid markings
        for x in range(0, width, 50):
            cv2.line(img, (x, 0), (x, height), (48, 54, 62), 1)
        for y in range(0, height, 50):
            cv2.line(img, (0, y), (width, y), (48, 54, 62), 1)

        # 1. Red Bottle: BGR: (30, 30, 210)
        cv2.rectangle(img, (120, 180), (180, 320), (30, 30, 210), -1)
        cv2.rectangle(img, (138, 140), (162, 180), (25, 25, 190), -1)
        cv2.rectangle(img, (135, 130), (165, 140), (255, 255, 255), -1)
        cv2.putText(img, "BOTTLE", (122, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # 2. Blue Cup: BGR: (210, 120, 20)
        cv2.rectangle(img, (270, 220), (340, 310), (210, 120, 20), -1)
        cv2.ellipse(img, (345, 265), (14, 25), 0, -90, 90, (190, 100, 15), 4)
        cv2.putText(img, "CUP", (285, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # 3. Green Box: BGR: (40, 180, 50)
        cv2.rectangle(img, (420, 180), (530, 280), (40, 180, 50), -1)
        cv2.rectangle(img, (420, 180), (530, 280), (70, 220, 80), 2)
        cv2.putText(img, "BOX", (455, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 4. Yellow Canister / Item: BGR: (20, 210, 220)
        cv2.circle(img, (210, 390), 32, (20, 210, 220), -1)
        cv2.circle(img, (210, 390), 32, (10, 230, 240), 2)
        cv2.putText(img, "CAN", (195, 395), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1)

        return img


class WebcamCamera(CameraSource):
    """
    OpenCV physical webcam capture source (laptop built-in webcam or USB camera).
    Runs a thread-safe background capture loop to eliminate buffer buildup and deliver low-latency frames.
    """

    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        target_fps: int = 30,
    ):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._current_frame: Optional[np.ndarray] = None
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.time()
        self._last_fps_count = 0
        self._last_error: Optional[str] = None

    def start(self) -> bool:
        if self._running and self._cap is not None and self._cap.isOpened():
            return True

        self.stop()

        try:
            # Try Windows DirectShow first for fast startup, fallback to default backend
            cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.device_index)

            if not cap.isOpened():
                self._last_error = f"Cannot open camera device index {self.device_index}"
                print(f"[WebcamCamera] Error: {self._last_error}")
                return False

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            ret, initial_frame = cap.read()
            if not ret or initial_frame is None:
                cap.release()
                self._last_error = "Camera opened but failed to read initial frame"
                print(f"[WebcamCamera] Error: {self._last_error}")
                return False

            with self._lock:
                self._cap = cap
                self._current_frame = initial_frame
                self._running = True
                self._frame_count = 1
                self._last_fps_time = time.time()
                self._last_fps_count = 1
                self._last_error = None

            # Spawn background capture worker thread
            self._thread = threading.Thread(target=self._capture_worker, daemon=True)
            self._thread.start()
            print(f"[WebcamCamera] Started webcam (device={self.device_index}, resolution={initial_frame.shape[1]}x{initial_frame.shape[0]})")
            return True
        except Exception as e:
            self._last_error = str(e)
            print(f"[WebcamCamera] Exception during start: {e}")
            return False

    def _capture_worker(self):
        """Continuous background thread grabbing freshest frames to avoid buffer latency."""
        sleep_duration = 1.0 / max(10, self.target_fps)
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                break

            ret, frame = self._cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._current_frame = frame
                    self._frame_count += 1
                    now = time.time()
                    elapsed = now - self._last_fps_time
                    if elapsed >= 1.0:
                        self._fps = round((self._frame_count - self._last_fps_count) / elapsed, 1)
                        self._last_fps_time = now
                        self._last_fps_count = self._frame_count
            else:
                time.sleep(0.01)

            time.sleep(sleep_duration)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception as e:
                    print(f"[WebcamCamera] Error releasing camera: {e}")
                self._cap = None
            self._current_frame = None
            self._fps = 0.0

        print(f"[WebcamCamera] Stopped webcam (device={self.device_index})")

    def is_running(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": "WebcamCamera",
            "device_index": self.device_index,
            "is_running": self.is_running(),
            "fps": self._fps,
            "frame_count": self._frame_count,
            "width": self.width,
            "height": self.height,
            "last_error": self._last_error,
        }


class VideoFileCamera(CameraSource):
    """
    Video file camera source for offline testing or benchmark playback.
    """

    def __init__(self, file_path: str, loop: bool = True):
        self.file_path = file_path
        self.loop = loop
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False

    def start(self) -> bool:
        if not os.path.exists(self.file_path):
            return False
        self._cap = cv2.VideoCapture(self.file_path)
        self._running = self._cap.isOpened()
        return self._running

    def stop(self) -> None:
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def is_running(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()

    def get_frame(self) -> Optional[np.ndarray]:
        if not self.is_running() or self._cap is None:
            return None
        ret, frame = self._cap.read()
        if not ret:
            if self.loop:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                return frame if ret else None
            return None
        return frame

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": "VideoFileCamera",
            "file_path": self.file_path,
            "is_running": self.is_running(),
        }


class FutureNetworkCamera(CameraSource):
    """
    Future camera abstraction for USB phone cameras (IP Webcam, DroidCam, etc.)
    or RTSP/HTTP network security/industrial cameras.
    """

    def __init__(self, stream_url: str):
        self.stream_url = stream_url
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False

    def start(self) -> bool:
        # Placeholder for future connection logic
        return False

    def stop(self) -> None:
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def is_running(self) -> bool:
        return self._running

    def get_frame(self) -> Optional[np.ndarray]:
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": "FutureNetworkCamera",
            "stream_url": self.stream_url,
            "is_running": self.is_running(),
            "status": "NOT_CONFIGURED (Awaiting phone USB/network camera connection)",
        }


class CameraManager:
    """
    Coordinates camera sources for the vision subsystem.
    Defaults to the laptop built-in webcam (`WebcamCamera(device_index=0)`).
    """

    def __init__(self):
        self.active_source: CameraSource = WebcamCamera(device_index=0)
        self.webcam_source = self.active_source

    def set_source(self, source: CameraSource):
        if self.active_source.is_running():
            self.active_source.stop()
        self.active_source = source

    def start(self) -> bool:
        return self.active_source.start()

    def stop(self) -> None:
        self.active_source.stop()

    def is_running(self) -> bool:
        return self.active_source.is_running()

    def get_frame(self) -> Optional[np.ndarray]:
        return self.active_source.get_frame()

    def get_status(self) -> Dict[str, Any]:
        return self.active_source.get_status()


# Global camera manager instance
camera_manager = CameraManager()

# Backward-compatible alias for existing endpoints
camera_source = CameraSource
