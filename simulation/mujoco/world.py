"""Build a small MuJoCo world with one three-motor skid steer per connection."""

import colorsys
import hashlib
import math
import xml.etree.ElementTree as ET


WHEEL_RADIUS = 0.16
TRACK_WIDTH = 0.68
MAX_LINEAR = 5.0
MAX_ANGULAR = 5.0
BLADE_SPEED = 40.0
MAX_WHEEL_SPEED = (MAX_LINEAR + MAX_ANGULAR * TRACK_WIDTH / 2) / WHEEL_RADIUS
MAX_WHEEL_ACCELERATION = 60.0  # rad/s²; avoid impulses when changing direction.
DRIVE_RESPONSE = 30.0
LATERAL_RESPONSE = 40.0
MAX_PLANAR_ACCELERATION = 30.0
MAX_YAW_ACCELERATION = 60.0


def body_motion(model, data, root_joint):
    """Return horizontal +X heading, body forward/side speed and world-Z yaw rate.

    Free-joint translation is in world coordinates; its angular velocity is
    local. Read the current quaternion directly: xmat can still describe the
    pose before the last mj_step integrated qpos.
    """
    position = model.jnt_qposadr[root_joint]
    velocity = model.jnt_dofadr[root_joint]
    w, x, y, z = data.qpos[position + 3:position + 7]
    forward_x = 1 - 2 * (y * y + z * z)
    forward_y = 2 * (x * y + w * z)
    length = math.hypot(forward_x, forward_y)
    forward_x /= max(length, 1e-9)
    forward_y /= max(length, 1e-9)
    vx, vy = data.qvel[velocity:velocity + 2]
    wx, wy, wz = data.qvel[velocity + 3:velocity + 6]
    yaw_rate = (2 * (x * z - w * y) * wx
                + 2 * (y * z + w * x) * wy
                + (1 - 2 * (x * x + y * y)) * wz)
    return (
        forward_x, forward_y,
        vx * forward_x + vy * forward_y,
        -vx * forward_y + vy * forward_x,
        yaw_rate,
    )


def apply_drive_brake(model, data, root_joint, left, right):
    """Engage ideal planar brakes on neutral axes without mixing local/world Z."""
    velocity = model.jnt_dofadr[root_joint]
    if left + right == 0.0:
        data.qvel[velocity:velocity + 2] = 0.0
    if left == right:
        position = model.jnt_qposadr[root_joint]
        w, x, y, z = data.qpos[position + 3:position + 7]
        # World vertical expressed in the free joint's local rotation frame.
        vertical = (2 * (x * z - w * y), 2 * (y * z + w * x),
                    1 - 2 * (x * x + y * y))
        yaw_rate = sum(vertical[i] * data.qvel[velocity + 3 + i] for i in range(3))
        for i in range(3):
            data.qvel[velocity + 3 + i] -= yaw_rate * vertical[i]


def apply_drive_control(model, data, motor_offset, root_joint, left, right):
    """Model tire traction from the same two synchronized wheel motor targets.

    This is a simplified skid-steer traction controller, not a calibrated tire
    model. Applied forces keep travel aligned with chassis +X while MuJoCo
    continues to resolve gravity and collisions.
    """
    changes = (left - data.ctrl[motor_offset], right - data.ctrl[motor_offset + 1])
    largest_change = max(abs(change) for change in changes)
    max_change = MAX_WHEEL_ACCELERATION * model.opt.timestep
    fraction = min(1.0, max_change / largest_change) if largest_change else 1.0
    # One fraction preserves the differential from the very first step. Two
    # independent clamps incorrectly ramped both motors equally at first.
    for index, change in enumerate(changes):
        data.ctrl[motor_offset + index] += fraction * change

    fx, fy, forward, lateral, yaw_rate = body_motion(model, data, root_joint)
    current_left, current_right = data.ctrl[motor_offset:motor_offset + 2]
    target_linear = (current_left + current_right) * WHEEL_RADIUS / 2
    target_angular = (current_right - current_left) * WHEEL_RADIUS / TRACK_WIDTH
    if left + right == 0.0:
        target_linear = 0.0
    if left == right:
        target_angular = 0.0

    forward_accel = DRIVE_RESPONSE * (target_linear - forward)
    # Centripetal feedforward turns the velocity vector with the chassis;
    # damping removes sideways momentum instead of carrying it into a turn.
    lateral_accel = forward * yaw_rate - LATERAL_RESPONSE * lateral
    magnitude = math.hypot(forward_accel, lateral_accel)
    scale = min(1.0, MAX_PLANAR_ACCELERATION / magnitude) if magnitude else 1.0
    body_id = model.jnt_bodyid[root_joint]
    mass = model.body_subtreemass[body_id]
    data.xfrc_applied[body_id, 0] = mass * scale * (forward_accel * fx - lateral_accel * fy)
    data.xfrc_applied[body_id, 1] = mass * scale * (forward_accel * fy + lateral_accel * fx)
    yaw_accel = max(-MAX_YAW_ACCELERATION, min(
        MAX_YAW_ACCELERATION, DRIVE_RESPONSE * (target_angular - yaw_rate)))
    # Approximate aggregate yaw inertia for this chassis and its four wheels.
    data.xfrc_applied[body_id, 5] = mass * 0.2 * yaw_accel


def wheel_speeds(linear, angular):
    """Convert body velocity to left/right wheel angular speeds in rad/s."""
    if not all(math.isfinite(value) for value in (linear, angular)):
        return 0.0, 0.0
    linear = max(-MAX_LINEAR, min(MAX_LINEAR, linear))
    angular = max(-MAX_ANGULAR, min(MAX_ANGULAR, angular))
    return (
        (linear - angular * TRACK_WIDTH / 2) / WHEEL_RADIUS,
        (linear + angular * TRACK_WIDTH / 2) / WHEEL_RADIUS,
    )


def build_world(mower_ids, spawn_slots=None):
    root = ET.Element("mujoco", model="emi_mower_world")
    ET.SubElement(root, "compiler", angle="radian")
    ET.SubElement(root, "option", timestep="0.01", gravity="0 0 -9.81", integrator="implicitfast")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1280", offheight="720")
    defaults = ET.SubElement(root, "default")
    # A skid steer must slip sideways while turning; high lateral friction
    # otherwise makes the simulated mower rotate far below its commanded rate.
    ET.SubElement(defaults, "geom", friction="0.1 0.1 0.01", condim="3")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", name="sun", pos="0 0 20", directional="true", dir="0 0 -1")
    ET.SubElement(world, "camera", name="overview", pos="0 0 25", quat="1 0 0 0", fovy="55")
    ET.SubElement(world, "geom", name="grass", type="plane", size="50 50 0.1", rgba="0.35 0.55 0.3 1")
    ET.SubElement(world, "geom", name="obstacle", type="box", pos="3 5 0.35", size="0.7 0.7 0.35", rgba="0.6 0.48 0.3 1")
    equality = ET.SubElement(root, "equality")
    actuators = ET.SubElement(root, "actuator")

    for index, mower_id in enumerate(mower_ids):
        digest = hashlib.sha256(mower_id.encode()).hexdigest()
        prefix = f"m_{digest[:24]}"
        slot = (spawn_slots or {}).get(mower_id, index)
        x = -8 + (slot % 5) * 4
        y = -8 + (slot // 5) * 4
        color = colorsys.hsv_to_rgb(int(digest[:8], 16) / 2**32, 0.65, 0.9)
        chassis_rgba = " ".join(str(component) for component in (*color, 1))
        body = ET.SubElement(world, "body", name=f"{prefix}_body", pos=f"{x} {y} 0.35")
        ET.SubElement(body, "freejoint", name=f"{prefix}_root")
        ET.SubElement(body, "geom", name=f"{prefix}_chassis", type="box", size="0.48 0.29 0.12", mass="12", rgba=chassis_rgba)
        ET.SubElement(body, "site", name=mower_id, pos="0 0 0.45", size="0.012", rgba="0.9 0.95 1 1")
        ET.SubElement(body, "geom", name=f"{prefix}_deck", type="cylinder", pos="0.15 0 -0.13", size="0.34 0.035", mass="2", rgba="0.18 0.22 0.2 1")
        ET.SubElement(body, "geom", name=f"{prefix}_label", type="box", pos="-0.05 0 0.14", size="0.22 0.21 0.025", mass="0.2", rgba="0.15 0.2 0.8 1")
        for part, start in (("shaft", "0 0 0.18"), ("left", "0.27 0.08 0.18"), ("right", "0.27 -0.08 0.18")):
            ET.SubElement(body, "geom", name=f"{prefix}_forward_{part}", type="capsule", fromto=f"{start} 0.4 0 0.18", size="0.012", mass="0", rgba="1 0.85 0.1 1", contype="0", conaffinity="0")
        for side, side_y in (("left", 0.34), ("right", -0.34)):
            for axle, axle_x in (("front", 0.32), ("rear", -0.32)):
                name = f"{prefix}_{side}_{axle}"
                wheel = ET.SubElement(body, "body", name=name, pos=f"{axle_x} {side_y} -0.17")
                ET.SubElement(wheel, "joint", name=f"{name}_joint", type="hinge", axis="0 1 0", damping="0.1")
                ET.SubElement(wheel, "geom", type="cylinder", size="0.16 0.055", euler="1.57079632679 0 0", mass="0.7", rgba="0.08 0.08 0.08 1")
            ET.SubElement(equality, "joint", joint1=f"{prefix}_{side}_front_joint", joint2=f"{prefix}_{side}_rear_joint", polycoef="0 1 0 0 0")
            ET.SubElement(actuators, "velocity", name=f"{prefix}_{side}_motor", joint=f"{prefix}_{side}_rear_joint", kv="15", ctrlrange=f"{-MAX_WHEEL_SPEED} {MAX_WHEEL_SPEED}", ctrllimited="true")
        blade = ET.SubElement(body, "body", name=f"{prefix}_blade", pos="0.15 0 -0.2")
        ET.SubElement(blade, "joint", name=f"{prefix}_blade_joint", type="hinge", axis="0 0 1", damping="0.02")
        ET.SubElement(blade, "geom", type="box", size="0.29 0.035 0.008", mass="0.3", rgba="0.8 0.8 0.7 1", contype="0", conaffinity="0")
        ET.SubElement(actuators, "velocity", name=f"{prefix}_blade_motor", joint=f"{prefix}_blade_joint", kv="0.2", ctrlrange="0 40", ctrllimited="true")
    return ET.tostring(root, encoding="unicode")
