import math
import unittest
import uuid
import xml.etree.ElementTree as ET

from world import MAX_ANGULAR, MAX_LINEAR, MAX_WHEEL_SPEED, TRACK_WIDTH, WHEEL_RADIUS, build_world, wheel_speeds


class WorldTests(unittest.TestCase):
    def test_new_mower_keeps_a_separate_spawn_slot_when_uuid_sorts_first(self):
        root = ET.fromstring(build_world(["a-new", "z-existing"], {"z-existing": 0, "a-new": 1}))
        bodies = root.findall("./worldbody/body")
        self.assertEqual(bodies[0].attrib["pos"], "-4 -8 0.35")
        self.assertEqual(bodies[1].attrib["pos"], "-8 -8 0.35")

    def test_drive_mixing(self):
        self.assertEqual(wheel_speeds(0, 0), (0, 0))
        left, right = wheel_speeds(0, 1)
        self.assertAlmostEqual(left, -right)
        self.assertLess(left, 0)
        self.assertEqual(wheel_speeds(math.nan, 1), (0, 0))
        self.assertEqual(wheel_speeds(2.5, 0), (2.5 / WHEEL_RADIUS, 2.5 / WHEEL_RADIUS))
        self.assertEqual(wheel_speeds(MAX_LINEAR, MAX_ANGULAR),
                         ((MAX_LINEAR - MAX_ANGULAR * TRACK_WIDTH / 2) / WHEEL_RADIUS,
                          MAX_WHEEL_SPEED))
        self.assertEqual(wheel_speeds(10, 10), wheel_speeds(MAX_LINEAR, MAX_ANGULAR))

    def test_each_mower_has_three_motors_and_coupled_wheels(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        root = ET.fromstring(build_world(ids))
        self.assertEqual(len(root.findall("./actuator/velocity")), 6)
        self.assertEqual(len(root.findall("./equality/joint")), 4)
        self.assertEqual(len(root.findall("./worldbody/body/freejoint")), 2)
        for motor in root.findall("./actuator/velocity"):
            if motor.attrib["name"].endswith("_blade_motor"):
                continue
            self.assertEqual(motor.attrib["ctrlrange"], f"{-MAX_WHEEL_SPEED} {MAX_WHEEL_SPEED}")


if __name__ == "__main__":
    unittest.main()
