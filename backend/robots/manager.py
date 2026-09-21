from typing import Dict, List, Optional
from .base import RobotArmInterface
from .diy_arm import DIYArmController
from .jetarm import JetArmController
from .models import RobotStatus


class RobotManager:
    """
    Central registry managing robot arm instances.
    Provides unified access for API endpoints, tasks, and telemetry loops.
    """

    def __init__(self):
        self._robots: Dict[str, RobotArmInterface] = {}
        self._initialize_default_arms()

    def _initialize_default_arms(self):
        # Register both 6-DOF robotic arms
        diy = DIYArmController(robot_id="diy_arm", name="DIY 3D-Printed Arm")
        jet = JetArmController(robot_id="jetarm", name="Hiwonder JetArm")

        self.register_robot(diy)
        self.register_robot(jet)

    def register_robot(self, robot: RobotArmInterface):
        self._robots[robot.get_id()] = robot

    def get_robot(self, robot_id: str) -> Optional[RobotArmInterface]:
        return self._robots.get(robot_id)

    def list_robots(self) -> List[RobotArmInterface]:
        return list(self._robots.values())

    def get_all_statuses(self) -> List[RobotStatus]:
        return [robot.get_status() for robot in self._robots.values()]

    async def emergency_stop_all(self) -> Dict[str, bool]:
        """Trigger emergency stop across all registered arms simultaneously."""
        results = {}
        for robot_id, robot in self._robots.items():
            results[robot_id] = await robot.emergency_stop()
        return results

    async def home_all(self) -> Dict[str, bool]:
        """Send all arms to home positions."""
        results = {}
        for robot_id, robot in self._robots.items():
            results[robot_id] = await robot.home()
        return results


# Global singleton manager
robot_manager = RobotManager()
