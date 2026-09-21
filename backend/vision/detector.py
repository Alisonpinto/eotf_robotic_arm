from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import cv2
import numpy as np
import uuid


class BoundingBox(BaseModel):
    """Image pixel bounding box coordinates (top-left x1,y1 to bottom-right x2,y2)."""
    x1: int = Field(..., description="Top-left X in pixels")
    y1: int = Field(..., description="Top-left Y in pixels")
    x2: int = Field(..., description="Bottom-right X in pixels")
    y2: int = Field(..., description="Bottom-right Y in pixels")

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)


class Point2D(BaseModel):
    """2D point in image pixel coordinates."""
    x: int
    y: int


class DetectedObject(BaseModel):
    """
    Structured detected object representation.
    
    CRITICAL DISTINCTION:
    - bounding_box and center are strictly in IMAGE COORDINATES (pixel space: [0..W, 0..H]).
    - robot_coordinates are explicitly None / pending calibration until a physical camera
      extrinsic transformation matrix is mounted to the robotic arm.
    - camera coordinates != robot coordinates.
    """
    id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:6]}")
    name: str = Field(..., description="Object category or class (e.g. 'mouse', 'bottle', 'cup', 'keyboard', 'laptop', 'person')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bounding_box: BoundingBox
    center: Point2D
    color: Optional[str] = Field(None, description="Dominant recognized color (e.g. 'red', 'blue', 'green', 'black', 'white')")
    area_pixels: int = Field(0, description="Bounding box pixel area")
    coordinate_frame: str = Field(
        "IMAGE_COORDINATES_PIXELS",
        description="Explicit coordinate reference frame (IMAGE_COORDINATES_PIXELS vs ROBOT_COORDINATES_MM)"
    )
    robot_coordinates: Optional[Dict[str, Any]] = Field(
        None,
        description="Robot frame 3D position (X,Y,Z in mm) - currently None, requires physical camera extrinsic calibration"
    )


class ColorEstimator:
    """
    OpenCV-based dominant color estimator for arbitrary detected objects.
    Samples the inner bounding box subregion to minimize background contamination
    and classifies pixels in HSV color space into standard semantic colors.
    """

    COLOR_DEFINITIONS: List[Tuple[str, Tuple[int, int, int], Tuple[int, int, int]]] = [
        # (name, (lower_H, lower_S, lower_V), (upper_H, upper_S, upper_V))
        ("red", (0, 60, 50), (10, 255, 255)),
        ("red", (165, 60, 50), (180, 255, 255)),
        ("orange", (11, 70, 70), (22, 255, 255)),
        ("yellow", (23, 70, 70), (35, 255, 255)),
        ("green", (36, 50, 50), (85, 255, 255)),
        ("blue", (86, 60, 50), (130, 255, 255)),
        ("purple", (131, 50, 50), (155, 255, 255)),
        ("pink", (156, 50, 70), (164, 255, 255)),
    ]

    @classmethod
    def estimate_color(cls, image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Optional[str]:
        if image is None or image.size == 0:
            return None

        h, w = image.shape[:2]
        x1_c = max(0, min(w - 1, x1))
        x2_c = max(0, min(w, x2))
        y1_c = max(0, min(h - 1, y1))
        y2_c = max(0, min(h, y2))

        box_w = x2_c - x1_c
        box_h = y2_c - y1_c

        if box_w < 6 or box_h < 6:
            return None

        # Sample inner region (20% margin on each side) to avoid background clutter
        pad_x = int(box_w * 0.20)
        pad_y = int(box_h * 0.20)
        crop = image[y1_c + pad_y : y2_c - pad_y, x1_c + pad_x : x2_c - pad_x]

        if crop.size == 0:
            crop = image[y1_c:y2_c, x1_c:x2_c]
            if crop.size == 0:
                return None

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        total_pixels = crop.shape[0] * crop.shape[1]
        if total_pixels == 0:
            return None

        # Extract HSV channels
        H = hsv[:, :, 0]
        S = hsv[:, :, 1]
        V = hsv[:, :, 2]

        # 1. Check for Achromatic colors (black, white, gray)
        black_mask = V < 45
        black_count = int(np.sum(black_mask))

        white_mask = (S < 35) & (V > 185)
        white_count = int(np.sum(white_mask))

        gray_mask = (S < 40) & (V >= 45) & (V <= 185)
        gray_count = int(np.sum(gray_mask))

        # 2. Check Chromatic color ranges
        color_counts: Dict[str, int] = {
            "black": black_count,
            "white": white_count,
            "gray": gray_count,
            "red": 0,
            "orange": 0,
            "yellow": 0,
            "green": 0,
            "blue": 0,
            "purple": 0,
            "pink": 0,
        }

        # Mask out neutral/achromatic pixels for chromatic evaluation
        chromatic_filter = (S >= 40) & (V >= 45)

        for color_name, (lower_h, lower_s, lower_v), (upper_h, upper_s, upper_v) in cls.COLOR_DEFINITIONS:
            mask = (
                (H >= lower_h) & (H <= upper_h) &
                (S >= lower_s) & (S <= upper_s) &
                (V >= lower_v) & (V <= upper_v) &
                chromatic_filter
            )
            color_counts[color_name] = color_counts.get(color_name, 0) + int(np.sum(mask))

        # Find highest scoring color
        best_color, best_count = max(color_counts.items(), key=lambda item: item[1])

        # Require at least 15% dominant presence in the sample crop
        if best_count / float(total_pixels) >= 0.15:
            return best_color

        return None


class BaseVisionDetector(ABC):
    """Abstract base detector interface. Allows swapping between OpenCV, YOLO, or other models."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[DetectedObject]:
        """Detect objects in a BGR image array."""
        pass


class OpenCVColorShapeDetector(BaseVisionDetector):
    """
    OpenCV-based Color and Contour Object Detector.
    Uses HSV color thresholding, morphological noise suppression, and contour geometry
    to detect and categorize bottles, cups, boxes, and cylinders.
    """

    COLOR_RANGES = {
        "red": [
            (np.array([0, 70, 50]), np.array([10, 255, 255])),
            (np.array([170, 70, 50]), np.array([180, 255, 255])),
        ],
        "blue": [
            (np.array([100, 70, 50]), np.array([130, 255, 255])),
        ],
        "green": [
            (np.array([35, 60, 50]), np.array([85, 255, 255])),
        ],
        "yellow": [
            (np.array([20, 80, 80]), np.array([35, 255, 255])),
        ],
        "orange": [
            (np.array([10, 80, 80]), np.array([20, 255, 255])),
        ],
    }

    def __init__(self, min_area: int = 600, max_area: int = 150000):
        self.min_area = min_area
        self.max_area = max_area

    def detect(self, image: np.ndarray) -> List[DetectedObject]:
        if image is None or image.size == 0:
            return []

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        detections: List[DetectedObject] = []
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        for color_name, ranges in self.COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if self.min_area <= area <= self.max_area:
                    x, y, w, h = cv2.boundingRect(cnt)

                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx = x + w // 2
                        cy = y + h // 2

                    aspect_ratio = float(h) / max(1, float(w))
                    perimeter = cv2.arcLength(cnt, True)
                    circularity = 4 * np.pi * (area / (perimeter * perimeter)) if perimeter > 0 else 0

                    if aspect_ratio >= 1.4:
                        inferred_name = "bottle"
                        confidence = 0.94
                    elif 0.8 <= aspect_ratio <= 1.3:
                        if circularity > 0.7:
                            inferred_name = "cup"
                            confidence = 0.91
                        else:
                            inferred_name = "box"
                            confidence = 0.93
                    elif aspect_ratio < 0.8:
                        inferred_name = "box"
                        confidence = 0.89
                    else:
                        inferred_name = "item"
                        confidence = 0.85

                    detections.append(
                        DetectedObject(
                            name=inferred_name,
                            confidence=round(confidence, 2),
                            bounding_box=BoundingBox(x1=x, y1=y, x2=x + w, y2=y + h),
                            center=Point2D(x=cx, y=cy),
                            color=color_name,
                            area_pixels=int(area),
                            coordinate_frame="IMAGE_COORDINATES_PIXELS",
                            robot_coordinates=None,
                        )
                    )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections


class YOLOVisionDetector(BaseVisionDetector):
    """
    Real Object Detector powered by pretrained Ultralytics YOLOv8/v11.
    Detects real arbitrary objects (mouse, bottle, cup, laptop, keyboard, person, etc.)
    and computes dominant color attributes and camera coordinates.
    """

    def __init__(self, model_name: str = "yolov8n.pt", min_confidence: float = 0.35):
        self.model_name = model_name
        self.min_confidence = min_confidence
        self._model = None
        self._is_ready = False
        self._init_error: Optional[str] = None
        self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO  # type: ignore
            print(f"[YOLODetector] Loading pretrained YOLO model '{self.model_name}'...")
            self._model = YOLO(self.model_name)
            self._is_ready = True
            print("[YOLODetector] Successfully initialized YOLO detector.")
        except Exception as e:
            self._is_ready = False
            self._init_error = str(e)
            print(f"[YOLODetector] YOLO model unavailable: {e}. Falling back to OpenCV detector.")

    def is_available(self) -> bool:
        if not self._is_ready:
            # Retry initialization in case package was installed after startup
            self._init_model()
        return self._is_ready

    def detect(self, image: np.ndarray) -> List[DetectedObject]:
        if not self.is_available() or self._model is None:
            return []

        if image is None or image.size == 0:
            return []

        h, w = image.shape[:2]
        detections: List[DetectedObject] = []

        try:
            results = self._model(image, conf=self.min_confidence, verbose=False)
            for r in results:
                boxes = getattr(r, "boxes", None)
                if boxes is None:
                    continue

                for box in boxes:
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    name = self._model.names.get(cls_id, f"class_{cls_id}").lower()

                    coords = box.xyxy[0].tolist()
                    x1 = max(0, min(w - 1, int(coords[0])))
                    y1 = max(0, min(h - 1, int(coords[1])))
                    x2 = max(0, min(w, int(coords[2])))
                    y2 = max(0, min(h, int(coords[3])))

                    if x2 <= x1 or y2 <= y1:
                        continue

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    area = (x2 - x1) * (y2 - y1)

                    # Estimate dominant color from cropped bounding box
                    dominant_color = ColorEstimator.estimate_color(image, x1, y1, x2, y2)

                    detections.append(
                        DetectedObject(
                            name=name,
                            confidence=round(conf, 2),
                            bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                            center=Point2D(x=cx, y=cy),
                            color=dominant_color,
                            area_pixels=area,
                            coordinate_frame="IMAGE_COORDINATES_PIXELS",
                            robot_coordinates=None,
                        )
                    )
        except Exception as e:
            print(f"[YOLODetector] Inference error: {e}")
            return []

        # Sort detections by confidence descending
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections


class VisionDetector(BaseVisionDetector):
    """
    Main Vision Detector aggregator.
    Prioritizes real deep-learning YOLO detector; falls back to OpenCV Color/Shape detector
    if YOLO model is initializing or unavailable.
    """

    def __init__(self):
        self.opencv_detector = OpenCVColorShapeDetector()
        self.yolo_detector = YOLOVisionDetector()

    def detect(self, image: np.ndarray) -> List[DetectedObject]:
        if self.yolo_detector.is_available():
            results = self.yolo_detector.detect(image)
            if results:
                return results
        return self.opencv_detector.detect(image)


# Singleton detector instance
vision_detector = VisionDetector()

# Backward compatibility alias
YOLODetectorStub = YOLOVisionDetector
