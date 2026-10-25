#!/usr/bin/env python3
"""Show the Docker simulation in MuJoCo's native interactive 3D viewer."""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import mujoco
import mujoco.viewer

from world import build_world
from viewer_labels import label_rectangle, uuid_label_image


def fetch_state(url):
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://localhost:8080")
    args = parser.parse_args()
    state_url = args.server.rstrip("/") + "/state"
    viewer = None
    mower_ids = None
    pending_ids = None
    pending_since = 0.0
    try:
        while True:
            try:
                state = fetch_state(state_url)
            except (OSError, ValueError) as error:
                print(f"Waiting for MuJoCo simulation: {error}", file=sys.stderr)
                time.sleep(1)
                continue

            current_ids = state["mowers"]
            if viewer is not None and current_ids != mower_ids:
                if current_ids != pending_ids:
                    pending_ids = current_ids
                    pending_since = time.monotonic()
                if time.monotonic() - pending_since < 1:
                    time.sleep(1 / 30)
                    continue
                viewer.close()
                viewer = None
                executable = sys.executable
                if sys.platform == "darwin":
                    executable = str(Path(executable).with_name("mjpython"))
                os.execv(executable, [executable, __file__, *sys.argv[1:]])
            pending_ids = None
            if current_ids != mower_ids:
                model = mujoco.MjModel.from_xml_string(build_world(current_ids))
                data = mujoco.MjData(model)
                viewer = mujoco.viewer.launch_passive(model, data)
                viewer.opt.label = mujoco.mjtLabel.mjLABEL_NONE
                label_sites = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, mower_id)
                               for mower_id in current_ids]
                label_images = [uuid_label_image(
                    mower_id, model.geom_rgba[model.body_geomadr[model.site_bodyid[site]], :3])
                    for mower_id, site in zip(current_ids, label_sites)]
                projection_scene = mujoco.MjvScene(model, maxgeom=0)
                viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
                positions = [state["qpos"][model.jnt_qposadr[joint]:model.jnt_qposadr[joint] + 2]
                             for joint in range(model.njnt)
                             if model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE]
                if positions and all(len(position) == 2 for position in positions):
                    xs, ys = zip(*positions)
                    viewer.cam.lookat[:] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0.2)
                    viewer.cam.distance = max(8, max(max(xs) - min(xs), max(ys) - min(ys)) * 1.8 + 5)
                else:
                    viewer.cam.lookat[:] = (-8, -8, 0)
                    viewer.cam.distance = 8
                viewer.cam.azimuth = 135
                viewer.cam.elevation = -35
                mower_ids = current_ids
                print(f"Native viewer showing: {', '.join(mower_ids) or 'empty world'}", flush=True)
            if not viewer.is_running():
                return
            if len(state["qpos"]) == model.nq and len(state["qvel"]) == model.nv:
                with viewer.lock():
                    data.qpos[:] = state["qpos"]
                    data.qvel[:] = state["qvel"]
                    mujoco.mj_forward(model, data)
                viewer.sync()
                viewport = viewer.viewport
                if viewport is not None and viewport.width > 0 and viewport.height > 0:
                    mujoco.mjv_updateCamera(model, data, viewer.cam, projection_scene)
                    camera = mujoco.mjv_averageCamera(projection_scene.camera[0], projection_scene.camera[1])
                    overlays = []
                    for site, label in zip(label_sites, label_images):
                        rectangle = label_rectangle(camera, viewport, data.site_xpos[site], label.shape)
                        if rectangle is not None:
                            overlays.append((mujoco.MjrRect(*rectangle), label))
                    viewer.set_images(overlays)
            time.sleep(1 / 30)
    finally:
        if viewer is not None:
            viewer.close()


if __name__ == "__main__":
    main()
