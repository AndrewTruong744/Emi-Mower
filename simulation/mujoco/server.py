#!/usr/bin/env python3
"""Run connected ROS mowers in MuJoCo and serve state to the native viewer."""

import json
import os
import re
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mujoco

from world import BLADE_SPEED, apply_drive_brake, apply_drive_control, build_world, wheel_speeds


class Fleet:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients = {}
        self.revision = 0
        self.state = {"mowers": [], "qpos": [], "qvel": []}

    def attach(self, mower_id, connection):
        with self.lock:
            previous = self.clients.get(mower_id)
            self.clients[mower_id] = {"connection": connection, "command": {}, "received": 0.0}
            self.revision += 1
        if previous:
            previous["connection"].close()

    def update(self, mower_id, connection, command):
        if not isinstance(command, dict):
            return
        try:
            linear = float(command["linear"])
            angular = float(command["angular"])
            if not isinstance(command["blade"], bool):
                return
            left, right = wheel_speeds(linear, angular)
        except (KeyError, TypeError, ValueError):
            return
        with self.lock:
            current = self.clients.get(mower_id)
            if current and current["connection"] is connection:
                current["command"] = {"left": left, "right": right, "blade": command["blade"]}
                current["received"] = time.monotonic()

    def detach(self, mower_id, connection):
        with self.lock:
            current = self.clients.get(mower_id)
            if current and current["connection"] is connection:
                del self.clients[mower_id]
                self.revision += 1

    def snapshot(self):
        with self.lock:
            return self.revision, {key: value.copy() for key, value in self.clients.items()}


fleet = Fleet()


class BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self):
        mower_id = None
        self.connection.settimeout(1)
        try:
            hello = json.loads(self.rfile.readline(512))
            mower_id = hello["mower_id"]
            if not isinstance(mower_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", mower_id):
                return
            fleet.attach(mower_id, self.connection)
            while True:
                line = self.rfile.readline(512)
                if not line:
                    break
                fleet.update(mower_id, self.connection, json.loads(line))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
        finally:
            if mower_id:
                fleet.detach(mower_id, self.connection)


class BridgeServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class StateHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            _, clients = fleet.snapshot()
            payload = json.dumps({"mowers": sorted(clients)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/state":
            with fleet.lock:
                payload = json.dumps(fleet.state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_error(404)

    def log_message(self, format_string, *args):
        pass


def transfer_state(old_model, old_data, model, data):
    if old_model is None:
        return
    for joint_id in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
        old_id = mujoco.mj_name2id(old_model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if old_id < 0:
            continue
        size_q = 7 if model.jnt_type[joint_id] == mujoco.mjtJoint.mjJNT_FREE else 1
        size_v = 6 if size_q == 7 else 1
        data.qpos[model.jnt_qposadr[joint_id]:model.jnt_qposadr[joint_id] + size_q] = old_data.qpos[old_model.jnt_qposadr[old_id]:old_model.jnt_qposadr[old_id] + size_q]
        data.qvel[model.jnt_dofadr[joint_id]:model.jnt_dofadr[joint_id] + size_v] = old_data.qvel[old_model.jnt_dofadr[old_id]:old_model.jnt_dofadr[old_id] + size_v]


def run_simulation():
    model = data = None
    revision = -1
    root_joints = []
    spawn_slots = {}
    while True:
        started = time.monotonic()
        current_revision, clients = fleet.snapshot()
        ids = sorted(clients)
        if current_revision != revision:
            for mower_id in ids:
                if mower_id not in spawn_slots:
                    spawn_slots[mower_id] = len(spawn_slots)
            new_model = mujoco.MjModel.from_xml_string(build_world(ids, spawn_slots))
            new_data = mujoco.MjData(new_model)
            transfer_state(model, data, new_model, new_data)
            model, data = new_model, new_data
            root_joints = [
                joint_id
                for joint_id in range(model.njnt)
                if model.jnt_type[joint_id] == mujoco.mjtJoint.mjJNT_FREE
            ]
            revision = current_revision
            print(f"MuJoCo mowers online: {', '.join(ids) or 'none'}", flush=True)
        now = time.monotonic()
        drive_commands = []
        for index, mower_id in enumerate(sorted(clients)):
            client = clients[mower_id]
            command = client["command"] if now - client["received"] < 0.3 else {}
            left = command.get("left", 0.0)
            right = command.get("right", 0.0)
            apply_drive_control(model, data, index * 3, root_joints[index], left, right)
            drive_commands.append((root_joints[index], left, right))
            data.ctrl[index * 3 + 2] = BLADE_SPEED if command.get("blade", False) else 0.0
        mujoco.mj_step(model, data)
        for root_joint, left, right in drive_commands:
            apply_drive_brake(model, data, root_joint, left, right)
        with fleet.lock:
            fleet.state = {
                "mowers": ids,
                "qpos": data.qpos.tolist(),
                "qvel": data.qvel.tolist(),
            }
        time.sleep(max(0.0, model.opt.timestep - (time.monotonic() - started)))


def main():
    bridge_port = int(os.environ.get("MUJOCO_BRIDGE_PORT", "8765"))
    state_port = int(os.environ.get("MUJOCO_STATE_PORT", "8080"))
    bridge = BridgeServer(("0.0.0.0", bridge_port), BridgeHandler)
    state_server = ThreadingHTTPServer(("0.0.0.0", state_port), StateHandler)
    threading.Thread(target=bridge.serve_forever, daemon=True).start()
    threading.Thread(target=state_server.serve_forever, daemon=True).start()
    print(f"MuJoCo native viewer state: http://localhost:{state_port}/state", flush=True)
    run_simulation()


if __name__ == "__main__":
    main()
