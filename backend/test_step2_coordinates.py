"""
Step 2 Verification Test Suite: Table Coordinate System & Calibration

Verifies:
1. Explicit separation of IMAGE_COORDINATES_PIXELS and TABLE_COORDINATES.
2. Accurate coordinate conversion from 2D pixel space (u, v) to 3D physical table space (X, Y, Z in mm).
3. Configurable calibration parameters (scale, offsets, and fixed table surface height Z).
4. Multiple pixel positions across the camera image sensor.
5. Generic YOLO objects: bottle, mango, mobile phone, cup.
6. Object matching integration preserving both pixel coordinates and table coordinates.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Mock minimal modules if running in pure-Python environment without full third-party wheels
for mod_name in ["fastapi", "cv2", "ultralytics", "numpy"]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            import types
            mock_mod = types.ModuleType(mod_name)
            if mod_name == "fastapi":
                class APIRouter:
                    def __init__(self, *args, **kwargs): pass
                    def get(self, *args, **kwargs): return lambda f: f
                    def post(self, *args, **kwargs): return lambda f: f
                    def websocket(self, *args, **kwargs): return lambda f: f
                class HTTPException(Exception):
                    def __init__(self, status_code, detail=None):
                        self.status_code = status_code
                        self.detail = detail
                mock_mod.APIRouter = APIRouter
                mock_mod.HTTPException = HTTPException
                mock_mod.Query = lambda *a, **k: None
                mock_mod.Response = object
                mock_mod.UploadFile = object
                mock_mod.File = lambda *a, **k: None
                mock_mod.Form = lambda *a, **k: None
                mock_responses = types.ModuleType("fastapi.responses")
                mock_responses.StreamingResponse = object
                sys.modules["fastapi.responses"] = mock_responses
            elif mod_name == "numpy":
                class _MockImg:
                    def __init__(self, shape):
                        self.shape = shape
                        self.size = shape[0] * shape[1] if len(shape) >= 2 else 1
                    def copy(self): return self
                mock_mod.ndarray = _MockImg
                mock_mod.uint8 = int
                mock_mod.float32 = float
                mock_mod.pi = 3.141592653589793
                mock_mod.full = lambda shape, val, dtype=None: _MockImg(shape)
                mock_mod.zeros = lambda shape, dtype=None: _MockImg(shape)
                mock_mod.ones = lambda shape, dtype=None: _MockImg(shape)
                mock_mod.array = lambda x, *a, **k: x
            elif mod_name == "cv2":
                mock_mod.FONT_HERSHEY_SIMPLEX = 0
                mock_mod.LINE_AA = 16
                mock_mod.MORPH_RECT = 0
                mock_mod.MORPH_OPEN = 2
                mock_mod.MORPH_CLOSE = 3
                mock_mod.RETR_EXTERNAL = 0
                mock_mod.CHAIN_APPROX_SIMPLE = 1
                mock_mod.COLOR_BGR2HSV = 40
                mock_mod.line = lambda *a, **k: None
                mock_mod.rectangle = lambda *a, **k: None
                mock_mod.ellipse = lambda *a, **k: None
                mock_mod.circle = lambda *a, **k: None
                mock_mod.putText = lambda *a, **k: None
            elif mod_name == "ultralytics":
                class _StubYOLO:
                    def __init__(self, *args, **kwargs): pass
                mock_mod.YOLO = _StubYOLO
            sys.modules[mod_name] = mock_mod

from vision.calibration import (
    FRAME_IMAGE_PIXELS,
    FRAME_TABLE_COORDINATES,
    CameraTableCalibrator,
    TableCoordinates,
    TableDimensions,
    estimate_dimensions,
    pixel_to_table,
    table_calibrator,
    table_to_pixel,
)
from vision.detector import BoundingBox, DetectedObject, Point2D
from vision.object_matcher import ObjectMatchQuery, object_matcher
from ai.interpreter import parse_command


def test_frame_distinctions():
    """Verify explicit distinction between camera image pixels and physical table coordinates."""
    print("\n--- 1. Testing Coordinate Frame Distinction ---")
    assert FRAME_IMAGE_PIXELS == "IMAGE_COORDINATES_PIXELS"
    assert FRAME_TABLE_COORDINATES == "TABLE_COORDINATES"
    assert FRAME_IMAGE_PIXELS != FRAME_TABLE_COORDINATES
    print(f"[OK] Camera Frame: {FRAME_IMAGE_PIXELS} (2D sensor pixel plane)")
    print(f"[OK] Table Frame:  {FRAME_TABLE_COORDINATES} (3D physical table workspace in mm)")


def test_multiple_pixel_positions():
    """Test coordinate conversion across multiple image pixel positions."""
    print("\n--- 2. Testing Multiple Pixel Positions (Pixel -> Table Conversion) ---")

    test_positions = [
        # (u, v, description)
        (320, 240, "Image Principal Center (optical axis)"),
        (420, 315, "User Prompt Example (X: 420, Y: 315)"),
        (120, 180, "Workbench Top-Left Region"),
        (530, 260, "Workbench Right Region"),
        (210, 390, "Workbench Bottom Region"),
        (0, 0, "Top-Left Corner Boundary"),
        (640, 480, "Bottom-Right Corner Boundary"),
    ]

    for px, py, desc in test_positions:
        coords: TableCoordinates = pixel_to_table(px, py)
        assert coords.frame == "TABLE_COORDINATES"
        assert coords.unit == "mm"
        assert coords.z == 0.0  # Default table surface height

        # Verify Round-trip back to pixel space
        inv_px, inv_py = table_to_pixel(coords.x, coords.y)
        assert abs(inv_px - px) < 0.2, f"Roundtrip X mismatch: got {inv_px}, expected {px}"
        assert abs(inv_py - py) < 0.2, f"Roundtrip Y mismatch: got {inv_py}, expected {py}"

        print(f"[OK] {desc:40s} -> Pixel: ({px:3d}, {py:3d}) => Table: (X={coords.x:6.1f} mm, Y={coords.y:6.1f} mm, Z={coords.z:4.1f} mm)")


def test_configurable_calibration_values():
    """Verify that calibration values (scale, offsets, table surface Z) are configurable."""
    print("\n--- 3. Testing Configurable Calibration Values ---")

    calib = CameraTableCalibrator()

    # Initial default placeholder check
    c0 = calib.pixel_to_table(320, 240)
    assert c0.x == 0.0
    assert c0.y == 300.0
    assert c0.z == 0.0
    print(f"[OK] Default Placeholder: Center (320, 240) -> Table X={c0.x} mm, Y={c0.y} mm, Z={c0.z} mm")

    # Update table surface height to 25.0 mm (e.g. raised platform / fixture)
    calib.configure(table_surface_z_mm=25.0)
    c1 = calib.pixel_to_table(320, 240)
    assert c1.z == 25.0
    print(f"[OK] Configured Table Height Z=25.0 mm -> Table Z={c1.z} mm")

    # Update scale factors: e.g. 2.0 pixels/mm
    calib.configure(pixels_per_mm_x=2.0, pixels_per_mm_y=2.0, table_origin_offset_x_mm=50.0, table_origin_offset_y_mm=400.0)
    c2 = calib.pixel_to_table(420, 340)
    # X = (420 - 320) / 2.0 + 50.0 = 50 + 50 = 100.0
    # Y = (340 - 240) / 2.0 + 400.0 = 50 + 400 = 450.0
    assert abs(c2.x - 100.0) < 0.1
    assert abs(c2.y - 450.0) < 0.1
    print(f"[OK] Configured New Scale (2.0 px/mm) & Offset -> Table X={c2.x} mm, Y={c2.y} mm, Z={c2.z} mm")


def test_generic_yolo_objects():
    """
    Test generic objects (bottle, mango, mobile phone, cup)
    verifying that each DetectedObject retains YOLO pixel coordinates AND has table X/Y/Z coordinates.
    """
    print("\n--- 4. Testing Generic YOLO Detected Objects with Table Coordinates ---")

    generic_objects = [
        DetectedObject(
            name="bottle",
            confidence=0.95,
            color="red",
            bounding_box=BoundingBox(x1=390, y1=245, x2=450, y2=385),
            center=Point2D(x=420, y=315),
            coordinate_frame=FRAME_IMAGE_PIXELS,
        ),
        DetectedObject(
            name="mango",
            confidence=0.91,
            color=None,
            bounding_box=BoundingBox(x1=180, y1=240, x2=240, y2=320),
            center=Point2D(x=210, y=280),
            coordinate_frame=FRAME_IMAGE_PIXELS,
        ),
        DetectedObject(
            name="mobile phone",
            confidence=0.93,
            color=None,
            bounding_box=BoundingBox(x1=325, y1=170, x2=395, y2=270),
            center=Point2D(x=360, y=220),
            coordinate_frame=FRAME_IMAGE_PIXELS,
        ),
        DetectedObject(
            name="cup",
            confidence=0.89,
            color="blue",
            bounding_box=BoundingBox(x1=490, y1=210, x2=570, y2=310),
            center=Point2D(x=530, y=260),
            coordinate_frame=FRAME_IMAGE_PIXELS,
        ),
    ]

    for obj in generic_objects:
        # 1. Verify YOLO Pixel Coordinates are preserved
        assert obj.coordinate_frame == "IMAGE_COORDINATES_PIXELS"
        assert obj.center.x is not None and obj.center.y is not None
        assert obj.bounding_box.width > 0 and obj.bounding_box.height > 0

        # 2. Verify Table Coordinates are attached
        assert obj.table_coordinates is not None
        assert obj.table_coordinates.frame == "TABLE_COORDINATES"
        assert obj.table_coordinates.unit == "mm"
        assert obj.table_x is not None
        assert obj.table_y is not None
        assert obj.table_z is not None

        # 3. Verify Table Dimensions are attached
        assert obj.table_dimensions is not None
        assert obj.table_dimensions.width_mm > 0
        assert obj.table_dimensions.length_mm > 0

        print(f"[OBJECT DETECTED] {obj.name.upper()}")
        print(f"   Name:             {obj.name}")
        print(f"   Colour:           {obj.color or 'null (unspecified)'}")
        print(f"   Pixel X/Y:        X: {obj.center.x} px, Y: {obj.center.y} px  [{obj.coordinate_frame}]")
        print(f"   Table X/Y/Z:      X: {obj.table_x:.1f} mm, Y: {obj.table_y:.1f} mm, Z: {obj.table_z:.1f} mm  [{obj.table_coordinates.frame}]")
        print(f"   Dimensions (px):  {obj.bounding_box.width} x {obj.bounding_box.height} px")
        print(f"   Dimensions (mm):  ~{obj.table_dimensions.width_mm:.1f} x {obj.table_dimensions.length_mm:.1f} mm")
        print(f"   Confidence:       {int(obj.confidence * 100)}%")
        print()


def test_object_matcher_with_table_coordinates():
    """Verify that ObjectMatcher returns both pixel coordinates and table coordinates."""
    print("\n--- 5. Testing Object Matcher Output with Table Coordinates ---")

    detections = [
        DetectedObject(
            name="bottle",
            confidence=0.94,
            color="red",
            bounding_box=BoundingBox(x1=390, y1=245, x2=450, y2=385),
            center=Point2D(x=420, y=315),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
        DetectedObject(
            name="mango",
            confidence=0.92,
            color=None,
            bounding_box=BoundingBox(x1=180, y1=240, x2=240, y2=320),
            center=Point2D(x=210, y=280),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
    ]

    # Match "red bottle"
    t1 = parse_command("Robot 1 pick the red bottle and give it to Robot 2")
    eval_res = object_matcher.evaluate_match(detections, t1)
    assert eval_res.found is True
    assert eval_res.target.name == "bottle"
    assert eval_res.target.color == "red"
    assert eval_res.target.center.x == 420
    assert eval_res.target.center.y == 315
    assert eval_res.target.table_coordinates is not None
    assert eval_res.target.table_coordinates.frame == "TABLE_COORDINATES"
    assert eval_res.target.table_x is not None

    print(f"[OK] Evaluated Target Match: '{eval_res.target.name}'")
    print(f"     Pixel:  ({eval_res.target.center.x}, {eval_res.target.center.y}) px [{eval_res.target.coordinate_frame}]")
    print(f"     Table:  (X={eval_res.target.table_x} mm, Y={eval_res.target.table_y} mm, Z={eval_res.target.table_z} mm) [{eval_res.target.table_coordinates.frame}]")

    # Test legacy match interface
    match_result = object_matcher.match(detections, ObjectMatchQuery(name="mango"))
    assert match_result.matched is True
    assert match_result.image_coordinates is not None
    assert match_result.table_coordinates is not None
    assert match_result.coordinate_frame == "IMAGE_COORDINATES_PIXELS"
    assert match_result.table_coordinate_frame == "TABLE_COORDINATES"
    assert match_result.table_coordinates["x"] is not None
    print(f"[OK] MatchResult: image_coords={match_result.image_coordinates['center']}, table_coords={match_result.table_coordinates}")


def main():
    print("=" * 66)
    print("  STEP 2 VERIFICATION: TABLE COORDINATE SYSTEM & CALIBRATION")
    print("=" * 66)

    test_frame_distinctions()
    test_multiple_pixel_positions()
    test_configurable_calibration_values()
    test_generic_yolo_objects()
    test_object_matcher_with_table_coordinates()

    print("=" * 66)
    print("  ALL STEP 2 TABLE COORDINATE & CALIBRATION TESTS PASSED!")
    print("=" * 66)


if __name__ == "__main__":
    main()
