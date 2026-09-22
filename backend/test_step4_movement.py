import unittest
try:
    from pydantic import ValidationError
except ImportError:
    try:
        from ai.schemas import ValidationError
    except ImportError:
        pass

from robots.movement_planner import movement_planner, MovementPlan, TargetCoordinate

class TestStep4MovementPlanner(unittest.TestCase):

    def test_valid_target_generates_plan(self):
        """Test that a valid XYZ target creates a MovementPlan for Robot 1."""
        plan = movement_planner.generate_plan_for_robot(
            robot_id="R1", 
            target_x=100.5, 
            target_y=200.0, 
            target_z=50.0
        )
        
        self.assertIsInstance(plan, MovementPlan)
        self.assertEqual(plan.robot_id, "R1")
        self.assertEqual(plan.target.x, 100.5)
        self.assertEqual(plan.target.y, 200.0)
        self.assertEqual(plan.target.z, 50.0)
        self.assertEqual(plan.status, "PLAN_GENERATED_PENDING_IK")

    def test_exactly_six_joints_pending_ik(self):
        """Test that exactly 6 joints exist and contain the PENDING_REAL_IK placeholder."""
        plan = movement_planner.generate_plan_for_robot("R1", 10.0, 10.0, 10.0)
        
        self.assertEqual(plan.joint_1, "PENDING_REAL_IK")
        self.assertEqual(plan.joint_2, "PENDING_REAL_IK")
        self.assertEqual(plan.joint_3, "PENDING_REAL_IK")
        self.assertEqual(plan.joint_4, "PENDING_REAL_IK")
        self.assertEqual(plan.joint_5, "PENDING_REAL_IK")
        self.assertEqual(plan.joint_6, "PENDING_REAL_IK")

        # Verify no joint_7 accidentally exists
        self.assertFalse(hasattr(plan, "joint_7"))

    def test_base_remains_fixed(self):
        """Test that the planner explicitly enforces the fixed base constraint."""
        plan = movement_planner.generate_plan_for_robot("R1", 10.0, 10.0, 10.0)
        self.assertTrue(plan.base_fixed)
        
        # Test base movement rejection
        with self.assertRaises(ValidationError):
            MovementPlan(
                robot_id="R1",
                target=TargetCoordinate(x=0, y=0, z=0),
                base_fixed=False # Attempting to un-fix the base
            )

    def test_rejects_missing_or_invalid_coordinates(self):
        """Test that strings, None, or missing coordinates are rejected."""
        # Missing argument
        with self.assertRaises(TypeError):
            movement_planner.generate_plan_for_robot("R1", target_x=100.0, target_y=100.0) # Missing Z

        # Invalid type
        with self.assertRaises(ValueError):
            movement_planner.generate_plan_for_robot("R1", target_x="INVALID", target_y=100.0, target_z=100.0)

    def test_rejects_invalid_robot_id(self):
        """Test that unknown robot IDs are rejected using the Step 3 config."""
        with self.assertRaises(ValueError):
            movement_planner.generate_plan_for_robot("UNKNOWN_ROBOT", target_x=0.0, target_y=0.0, target_z=0.0)


if __name__ == "__main__":
    unittest.main()
