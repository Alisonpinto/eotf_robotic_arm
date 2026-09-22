import unittest
try:
    from pydantic import ValidationError
except ImportError:
    try:
        from ai.schemas import ValidationError
    except ImportError:
        pass

from robots.system_config import (
    RobotBaseConfig,
    RobotConfig,
    JointConfig,
    HandoffPointConfig,
    RoboticsSystemConfig,
    create_default_system_config,
    PLACEHOLDER_MEASUREMENT
)

class TestStep3RoboticsConfig(unittest.TestCase):

    def test_default_config_creation(self):
        """Test that the default system configuration is created successfully and contains placeholders."""
        system = create_default_system_config()
        
        self.assertIsInstance(system, RoboticsSystemConfig)
        self.assertEqual(system.robot_1.robot_id, "R1")
        self.assertEqual(system.robot_2.robot_id, "R2")
        self.assertEqual(len(system.robot_1.joints), 6)
        self.assertEqual(len(system.robot_2.joints), 6)
        
        # Verify placeholders are correctly identified
        self.assertEqual(system.handoff_point.x, PLACEHOLDER_MEASUREMENT)
        self.assertEqual(system.robot_1.base_position.x, PLACEHOLDER_MEASUREMENT)

    def test_robot_base_is_fixed_and_immutable(self):
        """Test that base positions are fixed and frozen to prevent movement."""
        base = RobotBaseConfig()
        self.assertTrue(base.is_fixed_base)
        
        # Attempting to modify a frozen pydantic model should raise TypeError or ValidationError
        with self.assertRaises((TypeError, ValidationError)):
            base.x = 100.0

        with self.assertRaises(ValidationError):
            # Cannot create a base that is not fixed
            RobotBaseConfig(is_fixed_base=False)

    def test_exactly_six_joints_enforced(self):
        """Test that a robot must have exactly 6 joints."""
        joints_valid = [JointConfig(name=f"J{i}") for i in range(6)]
        joints_invalid = [JointConfig(name=f"J{i}") for i in range(5)]
        
        # Valid creation
        r_valid = RobotConfig(robot_id="T1", name="Test Valid", joints=joints_valid)
        self.assertEqual(len(r_valid.joints), 6)
        
        # Invalid creation (5 joints)
        with self.assertRaises(ValidationError):
            RobotConfig(robot_id="T2", name="Test Invalid", joints=joints_invalid)

        # Invalid creation (7 joints)
        joints_invalid_7 = [JointConfig(name=f"J{i}") for i in range(7)]
        with self.assertRaises(ValidationError):
            RobotConfig(robot_id="T3", name="Test Invalid 7", joints=joints_invalid_7)

    def test_real_measurements_supported(self):
        """Test that we can actually enter real measurements instead of placeholders later."""
        handoff = HandoffPointConfig(x=150.0, y=200.0, z=50.0)
        self.assertEqual(handoff.x, 150.0)
        
        base_1 = RobotBaseConfig(x=0.0, y=0.0, z=0.0)
        self.assertEqual(base_1.x, 0.0)

if __name__ == "__main__":
    unittest.main()
