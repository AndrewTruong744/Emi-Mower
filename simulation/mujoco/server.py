#!/usr/bin/env python3
"""Run connected ROS mowers in MuJoCo and serve a browser view."""

import io
import json
import os
import re
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mujoco
from PIL import Image

from world import BLADE_SPEED, build_world, wheel_speeds


class Fleet:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients = {}
        self.revision = 0
        self.frame = b""

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


PAGE = b"""<!doctype html><html><head><meta charset='utf-8'><title>Emi MuJoCo</title>
<style>body{background:#17201b;color:#f0f4ed;font:16px system-ui;margin:24px}img{width:100%;max-width:1280px;border:1px solid #617362}code{color:#abd6b5}</style>
</head><body><h1>Emi Mower simulation</h1><p id='fleet'>Connecting...</p>
<img src='/stream' alt='Live MuJoCo world'><script>
async function update(){try{let r=await fetch('/status');let s=await r.json();
document.getElementById('fleet').textContent=s.mowers.length+' online mower(s): '+s.mowers.join(', ')}catch(e){}}
setInterval(update,1000);update();</script></body></html>"""


class ViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path == "/status":
            _, clients = fleet.snapshot()
            payload = json.dumps({"mowers": sorted(clients)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with fleet.lock:
                        frame = fleet.frame
                    if frame:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
                        self.wfile.flush()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass
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
    model = data = renderer = None
    revision = -1
    next_frame = 0.0
    while True:
        started = time.monotonic()
        current_revision, clients = fleet.snapshot()
        if current_revision != revision:
            ids = sorted(clients)
            new_model = mujoco.MjModel.from_xml_string(build_world(ids))
            new_data = mujoco.MjData(new_model)
            transfer_state(model, data, new_model, new_data)
            if renderer is not None:
                renderer.close()
            model, data = new_model, new_data
            renderer = mujoco.Renderer(model, height=720, width=1280)
            revision = current_revision
            print(f"MuJoCo mowers online: {', '.join(ids) or 'none'}", flush=True)
        now = time.monotonic()
        for index, mower_id in enumerate(sorted(clients)):
            client = clients[mower_id]
            command = client["command"] if now - client["received"] < 0.3 else {}
            data.ctrl[index * 3] = command.get("left", 0.0)
            data.ctrl[index * 3 + 1] = command.get("right", 0.0)
            data.ctrl[index * 3 + 2] = BLADE_SPEED if command.get("blade", False) else 0.0
        mujoco.mj_step(model, data)
        if now >= next_frame:
            renderer.update_scene(data, camera="overview")
            image = Image.fromarray(renderer.render())
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=80)
            with fleet.lock:
                fleet.frame = output.getvalue()
            next_frame = now + 0.1
        time.sleep(max(0.0, model.opt.timestep - (time.monotonic() - started)))


def main():
    bridge_port = int(os.environ.get("MUJOCO_BRIDGE_PORT", "8765"))
    viewer_port = int(os.environ.get("MUJOCO_VIEWER_PORT", "8080"))
    bridge = BridgeServer(("0.0.0.0", bridge_port), BridgeHandler)
    viewer = ThreadingHTTPServer(("0.0.0.0", viewer_port), ViewerHandler)
    threading.Thread(target=bridge.serve_forever, daemon=True).start()
    threading.Thread(target=viewer.serve_forever, daemon=True).start()
    print(f"MuJoCo viewer: http://localhost:{viewer_port}", flush=True)
    run_simulation()


if __name__ == "__main__":
    main()
