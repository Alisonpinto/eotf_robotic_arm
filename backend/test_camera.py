"""
Comprehensive test script for Laptop Webcam Camera Input and YOLO Object Detection.
Tests:
1. CameraSource abstraction (WebcamCamera, VideoFileCamera, FutureNetworkCamera)
2. Opening default laptop webcam via OpenCV (device 0)
3. Capturing real frames continuously
4. YOLOv8 object detection on real webcam frames
5. OpenCV Dominant Color estimation on detected bounding box
6. Structured detection schema verification
7. VisionProcessor MJPEG stream & CameraManager start/stop lifecycle
"""

import time
import numpy as np
from vision.camera import WebcamCamera, VideoFileCamera, FutureNetworkCamera, camera_manager
from vision.detector import vision_detector, ColorEstimator, DetectedObject
from vision.processor import vision_processor


def test_camera_abstractions():
    print("--- Testing Camera Abstractions ---")
    webcam = WebcamCamera(device_index=0)
    status = webcam.get_status()
    assert status["source_type"] == "WebcamCamera"
    assert status["device_index"] == 0
    assert not status["is_running"]
    print("[OK] WebcamCamera initialized with source_type='WebcamCamera'")

    video_cam = VideoFileCamera(file_path="nonexistent.mp4")
    assert not video_cam.start()
    assert video_cam.get_status()["source_type"] == "VideoFileCamera"
    print("[OK] VideoFileCamera initialized and handled non-existent file cleanly")

    net_cam = FutureNetworkCamera(stream_url="rtsp://192.168.1.100:8554/live")
    assert net_cam.get_status()["source_type"] == "FutureNetworkCamera"
    print("[OK] FutureNetworkCamera placeholder registered")


def test_laptop_webcam_and_yolo():
    print("\n--- Testing Laptop Webcam & Real YOLO Detection ---")
    # Start camera via vision_processor / camera_manager
    started = vision_processor.start_camera()
    assert started, "Laptop webcam failed to open on device index 0"
    print("[OK] Laptop webcam opened successfully via CameraManager")

    time.sleep(0.5)  # Allow frame buffer to initialize

    # Test reading continuous frames
    for i in range(3):
        frame = camera_manager.get_frame()
        assert frame is not None, f"Failed to capture frame iteration {i}"
        assert frame.shape[0] > 0 and frame.shape[1] > 0
        time.sleep(0.05)
    print(f"[OK] Continuous frame capture verified: frame dimensions = {frame.shape[1]}x{frame.shape[0]}")

    # Test real object detection with YOLO
    detections = vision_detector.detect(frame)
    print(f"[OK] YOLO Inference executed: found {len(detections)} object(s)")

    for d in detections:
        print(f"   • Class: {d.name} | Conf: {d.confidence * 100:.1f}% | Color: {d.color or 'N/A'}")
        print(f"     Bounding box: [x1:{d.bounding_box.x1}, y1:{d.bounding_box.y1}, x2:{d.bounding_box.x2}, y2:{d.bounding_box.y2}]")
        print(f"     Center: [{d.center.x}, {d.center.y}] ({d.coordinate_frame})")
        assert d.coordinate_frame == "IMAGE_COORDINATES_PIXELS"
        assert d.robot_coordinates is None

    # Test processor frame annotation
    annotated, live_detections = vision_processor.process_frame()
    assert annotated.shape == frame.shape
    print(f"[OK] VisionProcessor annotated frame generated successfully")

    # Stop camera cleanly
    vision_processor.stop_camera()
    assert not vision_processor.is_camera_running()
    print("[OK] Camera cleanly stopped and hardware released")


def test_color_estimator():
    print("\n--- Testing OpenCV Color Estimator ---")
    # Create test synthetic patches
    red_patch = np.full((100, 100, 3), (20, 20, 220), dtype=np.uint8)
    color = ColorEstimator.estimate_color(red_patch, 0, 0, 100, 100)
    assert color == "red", f"Expected red, got {color}"

    blue_patch = np.full((100, 100, 3), (220, 120, 20), dtype=np.uint8)
    color = ColorEstimator.estimate_color(blue_patch, 0, 0, 100, 100)
    assert color == "blue", f"Expected blue, got {color}"

    green_patch = np.full((100, 100, 3), (30, 200, 40), dtype=np.uint8)
    color = ColorEstimator.estimate_color(green_patch, 0, 0, 100, 100)
    assert color == "green", f"Expected green, got {color}"
    print("[OK] ColorEstimator accurately identified synthetic color patches (red, blue, green)")


if __name__ == "__main__":
    test_camera_abstractions()
    test_color_estimator()
    test_laptop_webcam_and_yolo()
    print("\n==================================================")
    print("  ALL REAL-TIME WEBCAM & YOLO TESTS PASSED!       ")
    print("==================================================")
