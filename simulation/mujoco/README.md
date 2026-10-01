# MuJoCo mower simulation

This local simulator creates one skid steer mower for every connected Jetson
simulation container. Each model has four wheels, one motor for the coupled
left wheels, one for the coupled right wheels, and one for the mower blade.
The world has a grass plane, an obstacle, lighting, and an overhead camera.
The viewer is an MJPEG stream in a normal browser on macOS or Linux; no X11
server or desktop forwarding is required.

## Start

Start the backend and provisioned Jetson simulation containers as described in
[`nvidia_jetson/README.md`](../../nvidia_jetson/README.md). Start MuJoCo first:

```bash
cd simulation/mujoco
docker compose up --build -d
```

Open <http://localhost:8080>. Start one or more Jetson simulation projects.
Their ROS bridges reconnect automatically; each connection creates a mower in
the world, and stopping a container removes it. A restarted container regains
its model. The bridge port is `8765`. Set `MUJOCO_BRIDGE_ENDPOINT` in a mower's
Compose environment if the simulator is on another host.

The simulator container serves the browser view on `127.0.0.1:8080`. Its
bridge port is published on all host interfaces so `host.docker.internal` works
with Docker Desktop and Linux Docker. This bridge is for a trusted local
development network: it has no authentication. Set `MUJOCO_BRIDGE_BIND` to a
specific host interface if the workstation is on an untrusted network.

## ROS bindings

In a Jetson simulation container, the app joystick reaches the gateway and
then `/mower/<MOWER_ID>/teleop/cmd_vel`. The existing simulation command sink
forwards it to `/mower/<MOWER_ID>/sim/cmd_vel`; the ROS bridge sends linear and
angular velocity to MuJoCo. It clamps both axes to 1 m/s and 1 rad/s, mixes
them to wheel speeds using the 0.68 m track width and 0.16 m wheel radius, and
stops drive motors when commands are older than 200 ms. The server also stops
motors if bridge updates stop for 300 ms.

Publish `std_msgs/msg/Bool` at 10 Hz or faster to
`/mower/<MOWER_ID>/sim/blade_enable` to turn the simulated blade motor on.
Blade enable expires after 200 ms without an update. Example inside that
Jetson ROS container:

```bash
ros2 topic pub -r 10 /mower/<MOWER_ID>/sim/blade_enable std_msgs/msg/Bool '{data: true}'
```

This topic is simulation only. It does not issue a physical blade command.
The physical CAN and STM32 watchdog path is unchanged. The ROS bridge uses a
small newline-delimited JSON stream over TCP between containers; it does not
require access to the Docker socket or mower credentials.

## Verification

```bash
cd simulation/mujoco
python3 -m unittest test_world.py
docker compose config
```

For an end-to-end check, start the simulator and a provisioned Jetson
simulation container, open the viewer, and confirm its UUID appears. Stop the
Jetson container and confirm the mower disappears. If the app joystick is
available, verify left, right, and turning motion.
