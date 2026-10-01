"""Build a small MuJoCo world with one three-motor skid steer per connection."""

import hashlib
import math
import xml.etree.ElementTree as ET


WHEEL_RADIUS = 0.16
TRACK_WIDTH = 0.68
MAX_LINEAR = 1.0
MAX_ANGULAR = 1.0
BLADE_SPEED = 40.0


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


def build_world(mower_ids):
    root = ET.Element("mujoco", model="emi_mower_world")
    ET.SubElement(root, "compiler", angle="radian")
    ET.SubElement(root, "option", timestep="0.01", gravity="0 0 -9.81", integrator="implicitfast")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1280", offheight="720")
    defaults = ET.SubElement(root, "default")
    ET.SubElement(defaults, "geom", friction="1.5 0.1 0.01", condim="3")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", name="sun", pos="0 0 20", directional="true", dir="0 0 -1")
    ET.SubElement(world, "camera", name="overview", pos="0 0 25", quat="1 0 0 0", fovy="55")
    ET.SubElement(world, "geom", name="grass", type="plane", size="50 50 0.1", rgba="0.35 0.55 0.3 1")
    ET.SubElement(world, "geom", name="obstacle", type="box", pos="3 5 0.35", size="0.7 0.7 0.35", rgba="0.6 0.48 0.3 1")
    equality = ET.SubElement(root, "equality")
    actuators = ET.SubElement(root, "actuator")

    for index, mower_id in enumerate(mower_ids):
        prefix = f"m_{hashlib.sha256(mower_id.encode()).hexdigest()[:24]}"
        x = -8 + (index % 5) * 4
        y = -8 + (index // 5) * 4
        body = ET.SubElement(world, "body", name=f"{prefix}_body", pos=f"{x} {y} 0.35")
        ET.SubElement(body, "freejoint", name=f"{prefix}_root")
        ET.SubElement(body, "geom", name=f"{prefix}_chassis", type="box", size="0.48 0.29 0.12", mass="12", rgba="0.88 0.35 0.12 1")
        ET.SubElement(body, "geom", name=f"{prefix}_deck", type="cylinder", pos="0.15 0 -0.13", size="0.34 0.035", mass="2", rgba="0.18 0.22 0.2 1")
        ET.SubElement(body, "geom", name=f"{prefix}_label", type="box", pos="-0.05 0 0.14", size="0.22 0.21 0.025", mass="0.2", rgba="0.15 0.2 0.8 1")
        for side, side_y in (("left", 0.34), ("right", -0.34)):
            for axle, axle_x in (("front", 0.32), ("rear", -0.32)):
                name = f"{prefix}_{side}_{axle}"
                wheel = ET.SubElement(body, "body", name=name, pos=f"{axle_x} {side_y} -0.17")
                ET.SubElement(wheel, "joint", name=f"{name}_joint", type="hinge", axis="0 1 0", damping="0.1")
                ET.SubElement(wheel, "geom", type="cylinder", size="0.16 0.055", euler="1.57079632679 0 0", mass="0.7", rgba="0.08 0.08 0.08 1")
            ET.SubElement(equality, "joint", joint1=f"{prefix}_{side}_front_joint", joint2=f"{prefix}_{side}_rear_joint", polycoef="0 1 0 0 0")
            ET.SubElement(actuators, "velocity", name=f"{prefix}_{side}_motor", joint=f"{prefix}_{side}_rear_joint", kv="15", ctrlrange="-12 12", ctrllimited="true")
        blade = ET.SubElement(body, "body", name=f"{prefix}_blade", pos="0.15 0 -0.2")
        ET.SubElement(blade, "joint", name=f"{prefix}_blade_joint", type="hinge", axis="0 0 1", damping="0.02")
        ET.SubElement(blade, "geom", type="box", size="0.29 0.035 0.008", mass="0.3", rgba="0.8 0.8 0.7 1", contype="0", conaffinity="0")
        ET.SubElement(actuators, "velocity", name=f"{prefix}_blade_motor", joint=f"{prefix}_blade_joint", kv="0.2", ctrlrange="0 40", ctrllimited="true")
    return ET.tostring(root, encoding="unicode")
