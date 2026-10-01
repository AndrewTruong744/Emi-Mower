import math
import unittest
import uuid
import xml.etree.ElementTree as ET

from world import build_world, wheel_speeds


class WorldTests(unittest.TestCase):
    def test_drive_mixing(self):
        self.assertEqual(wheel_speeds(0, 0), (0, 0))
        left, right = wheel_speeds(0, 1)
        self.assertAlmostEqual(left, -right)
        self.assertLess(left, 0)
        self.assertEqual(wheel_speeds(math.nan, 1), (0, 0))

    def test_each_mower_has_three_motors_and_coupled_wheels(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        root = ET.fromstring(build_world(ids))
        self.assertEqual(len(root.findall("./actuator/velocity")), 6)
        self.assertEqual(len(root.findall("./equality/joint")), 4)
        self.assertEqual(len(root.findall("./worldbody/body/freejoint")), 2)


if __name__ == "__main__":
    unittest.main()
