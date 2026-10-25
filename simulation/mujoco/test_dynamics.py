"""Check that the simulated skid steer can attain useful drive and turn rates."""

import math
import unittest

import mujoco

from world import apply_drive_brake, apply_drive_control, body_motion, build_world, wheel_speeds


def step_command(model, data, linear, angular):
    left, right = wheel_speeds(linear, angular)
    apply_drive_control(model, data, 0, 0, left, right)
    mujoco.mj_step(model, data)
    apply_drive_brake(model, data, 0, left, right)


def yaw(data):
    w, x, y, z = data.qpos[3:7]
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def run_command(linear, angular, seconds=10):
    model = mujoco.MjModel.from_xml_string(build_world(["speed-test"]))
    data = mujoco.MjData(model)
    previous_yaw = 0.0
    yaw_change = 0.0
    for _ in range(int(seconds / model.opt.timestep)):
        step_command(model, data, linear, angular)
        current_yaw = yaw(data)
        yaw_change += (current_yaw - previous_yaw + math.pi) % (2 * math.pi) - math.pi
        previous_yaw = current_yaw
    return data, yaw_change


class DynamicsTests(unittest.TestCase):
    def test_full_mower_uuids_are_visible_labels_in_the_render_scene(self):
        ids = ["b688f3ea-b8df-4112-8ffe-63da14f851a5", "849b54b6-5d57-44a5-95be-c94742903b37"]
        model = mujoco.MjModel.from_xml_string(build_world(ids))
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        scene = mujoco.MjvScene(model, maxgeom=1000)
        options = mujoco.MjvOption()
        options.label = mujoco.mjtLabel.mjLABEL_SITE
        mujoco.mjv_updateScene(model, data, options, mujoco.MjvPerturb(),
                              mujoco.MjvCamera(), mujoco.mjtCatBit.mjCAT_ALL, scene)
        labels = {geom.label for geom in scene.geoms[:scene.ngeom] if geom.label}
        self.assertEqual(labels, set(ids))

    def test_neutral_turn_brake_uses_world_vertical_when_chassis_is_tilted(self):
        model = mujoco.MjModel.from_xml_string(build_world(["frame-test"]))
        data = mujoco.MjData(model)
        data.qpos[3:7] = (math.cos(0.2), math.sin(0.2), 0, 0)
        data.qvel[3:6] = (0.1, 0.7, 2.0)
        apply_drive_brake(model, data, 0, 1, 1)
        self.assertLess(abs(body_motion(model, data, 0)[4]), 1e-10)
        self.assertAlmostEqual(data.qvel[3], 0.1)

    def test_drive_control_is_isolated_to_its_mower(self):
        model = mujoco.MjModel.from_xml_string(build_world(["first", "second"]))
        data = mujoco.MjData(model)
        roots = [joint for joint in range(model.njnt)
                 if model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE]
        left, right = wheel_speeds(3, -3)
        for _ in range(20):
            apply_drive_control(model, data, 0, roots[0], left, right)
            apply_drive_control(model, data, 3, roots[1], 0, 0)
            mujoco.mj_step(model, data)
            apply_drive_brake(model, data, roots[1], 0, 0)
        self.assertGreater(body_motion(model, data, roots[0])[2], 0.2)
        self.assertLess(body_motion(model, data, roots[0])[4], -0.2)
        self.assertEqual(body_motion(model, data, roots[1])[2], 0)
        self.assertAlmostEqual(body_motion(model, data, roots[1])[4], 0)

    def test_diagonal_starts_driving_and_turning_together(self):
        model = mujoco.MjModel.from_xml_string(build_world(["diagonal-test"]))
        data = mujoco.MjData(model)
        for _ in range(50):
            step_command(model, data, 0, 0)
        linear, angular = 5 / math.sqrt(2), -5 / math.sqrt(2)
        left, right = wheel_speeds(linear, angular)
        step_command(model, data, linear, angular)
        self.assertAlmostEqual(data.ctrl[1] / data.ctrl[0], right / left)
        for _ in range(9):
            step_command(model, data, linear, angular)
        _, _, forward, _, yaw_rate = body_motion(model, data, 0)
        self.assertGreater(forward, 0.2)
        self.assertLess(yaw_rate, -0.2)

    def test_diagonal_travel_stays_aligned_with_chassis_heading(self):
        for linear, angular in ((3.5, -3.5), (3.5, 3.5), (-3.5, -3.5), (-3.5, 3.5)):
            with self.subTest(linear=linear, angular=angular):
                model = mujoco.MjModel.from_xml_string(build_world(["alignment-test"]))
                data = mujoco.MjData(model)
                for _ in range(50):
                    step_command(model, data, 0, 0)
                for _ in range(500):
                    step_command(model, data, linear, angular)
                    _, _, _, lateral, _ = body_motion(model, data, 0)
                    self.assertLess(abs(lateral), 0.1)
                    self.assertLess(data.qpos[2], 0.4)

    def test_forward_uses_model_heading_in_every_world_direction(self):
        for heading in (0, math.pi / 2, math.pi, -math.pi / 2):
            with self.subTest(heading=heading):
                model = mujoco.MjModel.from_xml_string(build_world(["heading-test"]))
                data = mujoco.MjData(model)
                data.qpos[3:7] = (math.cos(heading / 2), 0, 0, math.sin(heading / 2))
                start = data.qpos[:2].copy()
                for _ in range(150):
                    step_command(model, data, 3, 0)
                dx, dy = data.qpos[:2] - start
                self.assertGreater(dx * math.cos(heading) + dy * math.sin(heading), 2)
                self.assertLess(abs(-dx * math.sin(heading) + dy * math.cos(heading)), 0.02)

    def test_left_turn_to_forward_brakes_rotation_without_tipping(self):
        model = mujoco.MjModel.from_xml_string(build_world(["transition-test"]))
        data = mujoco.MjData(model)
        for _ in range(300):
            step_command(model, data, 0, 5)
        self.assertGreater(data.qvel[5], 1)
        for _ in range(50):
            step_command(model, data, 5, 0)
        heading = yaw(data)
        for _ in range(250):
            step_command(model, data, 5, 0)
            self.assertLess(abs(body_motion(model, data, 0)[4]), 1e-10)
            self.assertLess(data.qpos[2], 0.4)
        heading_change = (yaw(data) - heading + math.pi) % (2 * math.pi) - math.pi
        self.assertLess(abs(heading_change), 0.02)

    def test_neutral_brakes_both_axes_after_diagonal_motion(self):
        model = mujoco.MjModel.from_xml_string(build_world(["stop-test"]))
        data = mujoco.MjData(model)
        for _ in range(200):
            step_command(model, data, 3.5, -3.5)
        for _ in range(100):
            step_command(model, data, 0, 0)
        _, _, forward, lateral, yaw_rate = body_motion(model, data, 0)
        for speed in (forward, lateral, yaw_rate):
            self.assertLess(abs(speed), 0.01)

    def test_full_right_command_rotates_multiple_times(self):
        _, yaw_change = run_command(0, -5)
        self.assertLess(yaw_change, -4 * math.pi)

    def test_full_forward_command_reaches_fast_ground_speed(self):
        data, _ = run_command(5, 0)
        self.assertGreater(data.qpos[0] + 8, 25)


if __name__ == "__main__":
    unittest.main()
