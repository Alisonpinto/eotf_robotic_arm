"""
Camera-to-Table Coordinate Calibration Module.

CRITICAL ARCHITECTURAL DISTINCTIONS:
========================================================================================
1. IMAGE_COORDINATES_PIXELS:
   - 2D camera sensor image plane coordinates: (u, v)
   - Origin (0, 0) is at the TOP-LEFT of the camera image frame.
   - Units are strictly in pixels: u in [0, width], v in [0, height].
   - Determined directly by YOLO bounding boxes and object centers.

2. TABLE_COORDINATES:
   - 3D physical workspace coordinates: (X, Y, Z) on the fixed table plane.
   - Origin (0, 0, 0) is a defined physical reference datum on the fixed table surface.
   - Units are strictly in MILLIMETERS (mm).
   - Z represents height relative to the table surface (default Z = 0.0 mm for table plane).
   - X and Y correspond to the planar surface of the table.

3. ROBOT_COORDINATES:
   - Coordinate frames of Robot 1 and Robot 2 are distinct from table coordinates.
   - Robot dimensions, base offsets, and kinematics are NOT implemented in Step 2.

CALIBRATION CONFIGURATION & PLACEHOLDER NOTICE:
========================================================================================
The default calibration parameters implemented here are CONFIGURABLE PLACEHOLDERS.
DO NOT assume these placeholder values represent actual physical dimensions.

When you set up your physical camera and table, you will enter your REAL measurements in:
    backend/vision/table_calibration.json
or configure them dynamically via:
    table_calibrator.configure(...)
========================================================================================
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from pydantic import BaseModel, Field
except ImportError:
    try:
        from ai.schemas import BaseModel, Field
    except ImportError:
        from ..ai.schemas import BaseModel, Field


# Standard Coordinate Frame Identifiers
FRAME_IMAGE_PIXELS: str = "IMAGE_COORDINATES_PIXELS"
FRAME_TABLE_COORDINATES: str = "TABLE_COORDINATES"


class TableCoordinates(BaseModel):
    """
    Physical coordinates located on the fixed table workspace.
    Units: Millimeters (mm).
    """
    x: float = Field(..., description="Table coordinate X in millimeters (mm)")
    y: float = Field(..., description="Table coordinate Y in millimeters (mm)")
    z: float = Field(..., description="Table coordinate Z in millimeters (mm) - table surface height")
    frame: str = Field(FRAME_TABLE_COORDINATES, description="Explicit coordinate frame identifier")
    unit: str = Field("mm", description="Measurement unit (always millimeters)")
    is_placeholder_calibration: bool = Field(
        True,
        description="True while placeholder calibration values are used; False once real physical measurements are entered"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "z": round(self.z, 2),
            "frame": self.frame,
            "unit": self.unit,
            "is_placeholder_calibration": self.is_placeholder_calibration,
        }

    def __str__(self) -> str:
        return f"TableCoordinates(X={self.x:.1f} mm, Y={self.y:.1f} mm, Z={self.z:.1f} mm [{self.frame}])"


class TableDimensions(BaseModel):
    """
    Estimated physical dimensions on the table plane derived from bounding box and calibration scale.
    Units: Millimeters (mm).
    """
    width_mm: float = Field(..., description="Estimated width in millimeters along table X axis")
    length_mm: float = Field(..., description="Estimated length in millimeters along table Y axis")
    pixel_width: int = Field(..., description="Original bounding box width in pixels")
    pixel_height: int = Field(..., description="Original bounding box height in pixels")
    unit: str = Field("mm", description="Measurement unit")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width_mm": round(self.width_mm, 1),
            "length_mm": round(self.length_mm, 1),
            "pixel_width": self.pixel_width,
            "pixel_height": self.pixel_height,
            "unit": self.unit,
        }

    def __str__(self) -> str:
        return f"TableDimensions({self.width_mm:.1f} mm x {self.length_mm:.1f} mm [{self.pixel_width}x{self.pixel_height} px])"


class TableCalibrationConfig(BaseModel):
    """
    Configurable parameters for camera-to-table coordinate calibration.
    All values are placeholder defaults and can be updated when physical measurements are made.
    """
    # Calibration status notice
    is_placeholder_calibration: bool = Field(
        True,
        description="Set to False when replaced with real measured physical calibration values"
    )
    description: str = Field(
        "Camera 1 to Fixed Table Coordinate Calibration Configuration",
        description="Human-readable description"
    )

    # Fixed Table surface height
    table_surface_z_mm: float = Field(
        0.0,
        description="Fixed physical table surface height (Z=0 mm corresponds to the table plane)"
    )

    # Image sensor resolution
    image_width: int = Field(640, description="Expected camera frame width in pixels")
    image_height: int = Field(480, description="Expected camera frame height in pixels")

    # Linear scale factors (pixels per millimeter)
    # Placeholder: 1.5 pixels = 1.0 mm (i.e. 1 px = ~0.667 mm)
    pixels_per_mm_x: float = Field(1.5, description="Scale factor: pixels per mm along X")
    pixels_per_mm_y: float = Field(1.5, description="Scale factor: pixels per mm along Y")

    # Camera optical center (principal point) in image pixels
    principal_point_x: float = Field(320.0, description="Camera optical center X in pixels (width / 2)")
    principal_point_y: float = Field(240.0, description="Camera optical center Y in pixels (height / 2)")

    # Table physical origin offset relative to camera optical center (in mm)
    table_origin_offset_x_mm: float = Field(
        0.0,
        description="Table X origin offset relative to optical center in mm"
    )
    table_origin_offset_y_mm: float = Field(
        300.0,
        description="Table Y origin offset relative to optical center in mm (e.g. table center 300 mm in front)"
    )

    # 4-Point reference pairs for homography / perspective transformation (optional advanced calibration)
    reference_pixel_points: Optional[List[List[float]]] = Field(
        default_factory=lambda: [
            [120.0, 100.0],
            [520.0, 100.0],
            [520.0, 380.0],
            [120.0, 380.0],
        ],
        description="4 reference points in image pixel coordinates [[u, v], ...]"
    )
    reference_table_points: Optional[List[List[float]]] = Field(
        default_factory=lambda: [
            [-133.33, 206.67],
            [133.33, 206.67],
            [133.33, 393.33],
            [-133.33, 393.33],
        ],
        description="4 reference points on physical table in mm [[x, y], ...]"
    )


class CameraTableCalibrator:
    """
    Transforms 2D camera image coordinates (pixels) into 3D fixed table coordinates (millimeters).
    
    Supports:
    1. Linear scale and offset mapping (fast, intuitive, ideal for perpendicular overhead camera).
    2. 4-Point perspective homography transformation (for angled/perspective cameras).
    3. Persistent configuration file (backend/vision/table_calibration.json).
    4. Configurable table surface height (Z_table).
    """

    DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "table_calibration.json"

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config: TableCalibrationConfig = self._load_or_create_config()
        self._homography_matrix: Optional[List[List[float]]] = None
        self._inv_homography_matrix: Optional[List[List[float]]] = None
        self._recompute_matrices()

    def _load_or_create_config(self) -> TableCalibrationConfig:
        """Load configuration from JSON file or create with default placeholders."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TableCalibrationConfig(**{k: v for k, v in data.items() if not k.startswith("_")})
            except Exception as e:
                print(f"[TableCalibrator] Warning: could not parse {self.config_path} ({e}), using default placeholders.")
        return TableCalibrationConfig()

    def save_config(self, target_path: Optional[Union[str, Path]] = None) -> None:
        """Save the active calibration configuration to JSON."""
        save_path = Path(target_path) if target_path else self.config_path
        payload = {
            "_notice": "CONFIGURABLE PLACEHOLDER CALIBRATION: Replace these values later with actual physical camera/table measurements.",
            **self.config.model_dump()
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def configure(
        self,
        table_surface_z_mm: Optional[float] = None,
        pixels_per_mm_x: Optional[float] = None,
        pixels_per_mm_y: Optional[float] = None,
        principal_point_x: Optional[float] = None,
        principal_point_y: Optional[float] = None,
        table_origin_offset_x_mm: Optional[float] = None,
        table_origin_offset_y_mm: Optional[float] = None,
        is_placeholder_calibration: Optional[bool] = None,
        save: bool = False,
    ) -> None:
        """
        Dynamically update calibration parameters.
        This provides a single clean entrypoint for replacing placeholder values with real measurements.
        """
        if table_surface_z_mm is not None:
            self.config.table_surface_z_mm = float(table_surface_z_mm)
        if pixels_per_mm_x is not None and pixels_per_mm_x > 0:
            self.config.pixels_per_mm_x = float(pixels_per_mm_x)
        if pixels_per_mm_y is not None and pixels_per_mm_y > 0:
            self.config.pixels_per_mm_y = float(pixels_per_mm_y)
        if principal_point_x is not None:
            self.config.principal_point_x = float(principal_point_x)
        if principal_point_y is not None:
            self.config.principal_point_y = float(principal_point_y)
        if table_origin_offset_x_mm is not None:
            self.config.table_origin_offset_x_mm = float(table_origin_offset_x_mm)
        if table_origin_offset_y_mm is not None:
            self.config.table_origin_offset_y_mm = float(table_origin_offset_y_mm)
        if is_placeholder_calibration is not None:
            self.config.is_placeholder_calibration = bool(is_placeholder_calibration)

        self._recompute_matrices()
        if save:
            self.save_config()

    def set_table_surface_z(self, z_mm: float) -> None:
        """Set the physical table surface height in millimeters."""
        self.config.table_surface_z_mm = float(z_mm)

    def _recompute_matrices(self) -> None:
        """Compute homography matrices if 4-point calibration pairs are defined."""
        if (
            self.config.reference_pixel_points
            and self.config.reference_table_points
            and len(self.config.reference_pixel_points) >= 4
            and len(self.config.reference_table_points) >= 4
        ):
            try:
                self._homography_matrix = self._compute_homography_4pts(
                    self.config.reference_pixel_points[:4],
                    self.config.reference_table_points[:4]
                )
                self._inv_homography_matrix = self._invert_3x3(self._homography_matrix)
            except Exception:
                self._homography_matrix = None
                self._inv_homography_matrix = None
        else:
            self._homography_matrix = None
            self._inv_homography_matrix = None

    def pixel_to_table(
        self,
        pixel_x: float,
        pixel_y: float,
        table_z: Optional[float] = None,
        use_homography: bool = False,
    ) -> TableCoordinates:
        """
        Convert 2D camera image coordinates (pixel_x, pixel_y)
        to 3D physical table coordinates (X, Y, Z in mm).
        
        Args:
            pixel_x: Image X coordinate in pixels (horizontal, 0 = left).
            pixel_y: Image Y coordinate in pixels (vertical, 0 = top).
            table_z: Optional override for table surface height (defaults to config.table_surface_z_mm).
            use_homography: If True and 4-point homography is available, use perspective transformation.
            
        Returns:
            TableCoordinates with x (mm), y (mm), z (mm), and frame="TABLE_COORDINATES".
        """
        z_val = self.config.table_surface_z_mm if table_z is None else float(table_z)

        if use_homography and self._homography_matrix:
            # Apply 3x3 homography: [x_t, y_t, w]^T = H * [u, v, 1]^T
            h = self._homography_matrix
            u, v = float(pixel_x), float(pixel_y)
            x_t = h[0][0] * u + h[0][1] * v + h[0][2]
            y_t = h[1][0] * u + h[1][1] * v + h[1][2]
            w_t = h[2][0] * u + h[2][1] * v + h[2][2]
            if abs(w_t) > 1e-9:
                table_x = x_t / w_t
                table_y = y_t / w_t
            else:
                table_x = (u - self.config.principal_point_x) / self.config.pixels_per_mm_x + self.config.table_origin_offset_x_mm
                table_y = (v - self.config.principal_point_y) / self.config.pixels_per_mm_y + self.config.table_origin_offset_y_mm
        else:
            # Linear orthogonal projection model:
            # X_table = (u - c_x) / scale_x + offset_x
            # Y_table = (v - c_y) / scale_y + offset_y
            u = float(pixel_x)
            v = float(pixel_y)
            table_x = ((u - self.config.principal_point_x) / self.config.pixels_per_mm_x) + self.config.table_origin_offset_x_mm
            table_y = ((v - self.config.principal_point_y) / self.config.pixels_per_mm_y) + self.config.table_origin_offset_y_mm

        return TableCoordinates(
            x=round(table_x, 2),
            y=round(table_y, 2),
            z=round(z_val, 2),
            frame=FRAME_TABLE_COORDINATES,
            unit="mm",
            is_placeholder_calibration=self.config.is_placeholder_calibration,
        )

    def table_to_pixel(
        self,
        table_x: float,
        table_y: float,
        use_homography: bool = False,
    ) -> Tuple[float, float]:
        """
        Inverse mapping: Convert 3D/2D table coordinates (X, Y in mm)
        back to 2D camera image coordinates (pixel_x, pixel_y).
        """
        if use_homography and self._inv_homography_matrix:
            inv_h = self._inv_homography_matrix
            x, y = float(table_x), float(table_y)
            u_t = inv_h[0][0] * x + inv_h[0][1] * y + inv_h[0][2]
            v_t = inv_h[1][0] * x + inv_h[1][1] * y + inv_h[1][2]
            w_t = inv_h[2][0] * x + inv_h[2][1] * y + inv_h[2][2]
            if abs(w_t) > 1e-9:
                return round(u_t / w_t, 1), round(v_t / w_t, 1)

        # Linear inverse model:
        # u = (X_table - offset_x) * scale_x + c_x
        # v = (Y_table - offset_y) * scale_y + c_y
        x = float(table_x)
        y = float(table_y)
        pixel_x = (x - self.config.table_origin_offset_x_mm) * self.config.pixels_per_mm_x + self.config.principal_point_x
        pixel_y = (y - self.config.table_origin_offset_y_mm) * self.config.pixels_per_mm_y + self.config.principal_point_y
        return round(pixel_x, 1), round(pixel_y, 1)

    def estimate_dimensions_mm(self, pixel_width: int, pixel_height: int) -> TableDimensions:
        """Estimate the physical width and length of an object in millimeters from its bounding box."""
        width_mm = abs(pixel_width) / self.config.pixels_per_mm_x
        length_mm = abs(pixel_height) / self.config.pixels_per_mm_y
        return TableDimensions(
            width_mm=round(width_mm, 1),
            length_mm=round(length_mm, 1),
            pixel_width=int(pixel_width),
            pixel_height=int(pixel_height),
            unit="mm",
        )

    # ----------------------------------------------------------------------------------
    # Pure-Python Direct Linear Transformation (DLT) for 4-Point Homography
    # Requires zero external dependencies (no numpy / cv2 required).
    # ----------------------------------------------------------------------------------
    @staticmethod
    def _compute_homography_4pts(
        src_pts: List[List[float]],
        dst_pts: List[List[float]],
    ) -> List[List[float]]:
        """
        Solves the 8-unknown linear system for a 3x3 homography matrix H
        mapping src_pts (u, v) to dst_pts (x, y) such that H[2][2] = 1.0.
        """
        A: List[List[float]] = []
        B: List[float] = []

        for (u, v), (x, y) in zip(src_pts, dst_pts):
            # Row 1: u*h00 + v*h01 + h02 - x*u*h20 - x*v*h21 = x
            A.append([u, v, 1.0, 0.0, 0.0, 0.0, -x * u, -x * v])
            B.append(x)
            # Row 2: u*h10 + v*h11 + h12 - y*u*h20 - y*v*h21 = y
            A.append([0.0, 0.0, 0.0, u, v, 1.0, -y * u, -y * v])
            B.append(y)

        # Solve A * h = B using Gaussian elimination
        h = CameraTableCalibrator._solve_linear_system_8x8(A, B)
        return [
            [h[0], h[1], h[2]],
            [h[3], h[4], h[5]],
            [h[6], h[7], 1.0],
        ]

    @staticmethod
    def _solve_linear_system_8x8(A: List[List[float]], B: List[float]) -> List[float]:
        """Gaussian elimination with partial pivoting for an 8x8 system."""
        n = 8
        M = [row[:] + [B[i]] for i, row in enumerate(A)]

        for col in range(n):
            # Pivot
            max_row = max(range(col, n), key=lambda r: abs(M[r][col]))
            if abs(M[max_row][col]) < 1e-12:
                continue
            M[col], M[max_row] = M[max_row], M[col]

            pivot = M[col][col]
            for c in range(col, n + 1):
                M[col][c] /= pivot

            for r in range(n):
                if r != col:
                    factor = M[r][col]
                    for c in range(col, n + 1):
                        M[r][c] -= factor * M[col][c]

        return [M[i][n] for i in range(n)]

    @staticmethod
    def _invert_3x3(M: List[List[float]]) -> List[List[float]]:
        """Invert a 3x3 matrix in pure Python."""
        det = (
            M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
        )
        if abs(det) < 1e-12:
            return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        inv_det = 1.0 / det
        return [
            [
                (M[1][1] * M[2][2] - M[1][2] * M[2][1]) * inv_det,
                (M[0][2] * M[2][1] - M[0][1] * M[2][2]) * inv_det,
                (M[0][1] * M[1][2] - M[0][2] * M[1][1]) * inv_det,
            ],
            [
                (M[1][2] * M[2][0] - M[1][0] * M[2][2]) * inv_det,
                (M[0][0] * M[2][2] - M[0][2] * M[2][0]) * inv_det,
                (M[0][2] * M[1][0] - M[0][0] * M[1][2]) * inv_det,
            ],
            [
                (M[1][0] * M[2][1] - M[1][1] * M[2][0]) * inv_det,
                (M[0][1] * M[2][0] - M[0][0] * M[2][1]) * inv_det,
                (M[0][0] * M[1][1] - M[0][1] * M[1][0]) * inv_det,
            ],
        ]


# Singleton Calibrator Instance
table_calibrator = CameraTableCalibrator()


# Convenience Module-level Helper Functions
def pixel_to_table(pixel_x: float, pixel_y: float, table_z: Optional[float] = None) -> TableCoordinates:
    """Convenience helper: Convert (pixel_x, pixel_y) to TableCoordinates (X, Y, Z in mm)."""
    return table_calibrator.pixel_to_table(pixel_x, pixel_y, table_z)


def table_to_pixel(table_x: float, table_y: float) -> Tuple[float, float]:
    """Convenience helper: Convert (table_x, table_y in mm) to camera pixels (u, v)."""
    return table_calibrator.table_to_pixel(table_x, table_y)


def estimate_dimensions(pixel_width: int, pixel_height: int) -> TableDimensions:
    """Convenience helper: Estimate physical dimensions (mm) from bounding box pixel width & height."""
    return table_calibrator.estimate_dimensions_mm(pixel_width, pixel_height)
