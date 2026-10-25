# MuJoCo mower simulation

This local simulator creates one skid steer mower for every connected Jetson
simulation container. Each model has four wheels, one motor for the coupled
left wheels, one for the coupled right wheels, and one for the mower blade.
The world has a grass plane, an obstacle, and lighting. The native MuJoCo
desktop viewer runs on macOS or Linux and reads the simulation's live model
state from the container. Port 8080 serves state data only; it has no web UI.

## Start

Start the backend and provisioned Jetson simulation containers as described in
[`nvidia_jetson/README.md`](../../nvidia_jetson/README.md). Start MuJoCo first:

```bash
cd simulation/mujoco
docker compose up --build -d
```

Start one or more Jetson simulation projects. Their ROS bridges reconnect
automatically; each connection creates a mower in
the world, and stopping a container removes it. A restarted container regains
its model. The bridge port is `8765`. Set `MUJOCO_BRIDGE_ENDPOINT` in a mower's
Compose environment if the simulator is on another host.

## Native viewer installation

### macOS

Install Python 3.12 (for example, `brew install python@3.12`). From
`simulation/mujoco`, create the viewer environment and launch it:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/mjpython native_viewer.py
```

MuJoCo requires its `mjpython` launcher for the macOS GUI event loop. Run it
from a normal Terminal session after starting the simulator container. See the
[MuJoCo Python viewer documentation](https://mujoco.readthedocs.io/en/stable/python.html).

### Linux desktop

Install Python 3.12 with `venv`, OpenGL, and GLFW. On Ubuntu 24.04, for
example, run `sudo apt-get install python3.12 python3.12-venv libgl1 libglfw3`.
From `simulation/mujoco`, create the viewer environment and launch it from a
desktop session:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python native_viewer.py
```

If Python 3.12 is unavailable on the host, `uv venv --python 3.12 .venv`
creates the same environment; install the package with
`uv pip install --python .venv/bin/python -r requirements.txt`. On Linux, run
the viewer with `DISPLAY` or `WAYLAND_DISPLAY` configured.

The viewer reconnects to the simulator and rebuilds its model when the set of
mowers changes. It uses MuJoCo's normal interactive camera and visualization
controls. The simulation remains authoritative inside Docker; the native
window displays its current state. Close the viewer window to exit. The
state endpoint is bound to `127.0.0.1:8080`.

Each mower has its full UUID displayed above its chassis in small, fixed
14-pixel text and a stable color derived from that UUID. Label text does not
scale with window size, camera zoom, or the viewer's UI font setting. The viewer
initially frames all connected mowers.
When another mower connects, the world assigns it a separate spawn slot and
preserves the existing mowers' poses.

To control multiple mowers, add each provisioned UUID from the app's Mowers
screen. On Controller, select the desired mower, enable Power in Manual mode,
and use the joystick. Switching the selected mower stops the previous joystick
stream; commands remain scoped to the selected UUID.

## Close and reopen

From `simulation/mujoco`, close the native viewer and stop the simulator:

```bash
pkill -f '[n]ative_viewer.py'
docker compose stop mujoco
```

Reopen on macOS after installing the viewer environment above:

```bash
docker compose up -d mujoco
.venv/bin/mjpython native_viewer.py
```

On Linux, use `.venv/bin/python native_viewer.py` for the last command.
To restart only the simulation while leaving the viewer open, run
`docker compose restart mujoco`. Mower bridges and the viewer reconnect.

The simulator container serves viewer state on `127.0.0.1:8080`. Its bridge
port is published on all host interfaces so `host.docker.internal` works
with Docker Desktop and Linux Docker. This bridge is for a trusted local
development network: it has no authentication. Set `MUJOCO_BRIDGE_BIND` to a
specific host interface if the workstation is on an untrusted network.

## ROS bindings

In a Jetson simulation container, the app joystick reaches the gateway and
then `/mower/<ROS_MOWER_ID>/teleop/cmd_vel`. `ROS_MOWER_ID` is `mower_` followed
by the mower UUID with hyphens replaced by underscores. The simulation command
sink forwards it to `/mower/<ROS_MOWER_ID>/sim/cmd_vel`; the ROS bridge sends linear and
angular velocity to MuJoCo. Simulation defaults to 5 m/s linear speed and
5 rad/s angular speed; both axes scale continuously with joystick displacement.
The bridge clamps to those limits and mixes
them to wheel speeds using the 0.68 m track width and 0.16 m wheel radius, and
stops drive motors when commands are older than 200 ms. The server also stops
motors if bridge updates stop for 300 ms.
The wheel motors have enough control range for simultaneous full linear and
angular commands. Both motor setpoints ramp with the same interpolation
fraction, limited to 60 rad/s² on the faster-changing motor. This preserves
the left/right differential throughout acceleration, so diagonal input starts
driving and turning together.

The chassis frame uses **+X forward, +Y left, and +Z up**; heading is rotation
about Z. A yellow arrow on top marks forward. The simulation reads the current
chassis quaternion to transform between local and world velocity. Its simplified
tire traction controller derives forward speed and yaw rate from the same two
motor targets, applies forces along the chassis heading, and counters sideways
momentum as the mower turns. MuJoCo continues to resolve gravity and collisions.
This is a teleoperation model; its tire traction is not calibrated to hardware.

The simulator brakes each neutral axis independently: a zero turn command
brakes rotation about world vertical even while driving forward, and zero linear
speed brakes translation while turning. A timed-out command brakes both axes.

While the joystick is held away from center, the app republishes its normalized
position every 50 ms. A held right or left position therefore keeps rotating
through multiple revolutions. Releasing or canceling the gesture sends zero
immediately; command timeouts remain the fallback if updates stop.
Each joystick axis has a 3% zero band, allowing straight driving or turning
without an accidental small command on the other axis.

The app's Power, mode, and E-stop controls query the simulation gateway's
`mower/<uuid>/command` route. Manual joystick motion is accepted only when
Power is on, mode is Manual, and E-stop has not been latched. A gateway
reconnect resets this simulation-only control state to Power off. Joystick
`+x` rotates right, `-x` left, `+y` drives forward, and `-y` backward.

Publish `std_msgs/msg/Bool` at 10 Hz or faster to
`/mower/<ROS_MOWER_ID>/sim/blade_enable` to turn the simulated blade motor on.
Blade enable expires after 200 ms without an update. Example inside that
Jetson ROS container:

```bash
ros2 topic pub -r 10 /mower/<ROS_MOWER_ID>/sim/blade_enable std_msgs/msg/Bool '{data: true}'
```

This topic is simulation only. It does not issue a physical blade command.
The physical CAN and STM32 watchdog path is unchanged. The ROS bridge uses a
small newline-delimited JSON stream over TCP between containers; it does not
require access to the Docker socket or mower credentials.

## Verification

```bash
cd simulation/mujoco
python3 -m unittest discover -p 'test_*.py'
docker compose config
```

For an end-to-end check, start the simulator and a provisioned Jetson
simulation container, open the viewer, and confirm its UUID appears. Stop the
Jetson container and confirm the mower disappears. If the app joystick is
available, verify left, right, and turning motion.
