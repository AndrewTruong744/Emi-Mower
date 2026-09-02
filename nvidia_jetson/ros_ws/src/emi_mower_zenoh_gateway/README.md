# Emi Mower Zenoh gateway

`zenoh_gateway` is the only ROS node that uses the app/backend's native Zenoh
routes. It has two directions:

```text
mower/<mower_id>/joystick JSON -> /teleop/cmd_vel (geometry_msgs/TwistStamped)
/mower/telemetry (emi_mower_interfaces/TelemetryBatch)
  -> mower/<mower_id>/telemetry (AsyncAPI TelemetryList JSON)
```

`MOWER_ID` is set once by the launch file. The gateway validates that identifier
before constructing a route and injects it into telemetry records, so a ROS
publisher cannot publish data as another mower.

The native Zenoh structs and route helpers in `src/generated/` are generated
from `backend/zenoh_asyncapi.yaml`. Regenerate them from `backend/` with
`./scripts/generate_types.sh`; do not edit those Rust files manually. ROS
messages remain in `emi_mower_interfaces` because they are a separate ROS IDL
contract.

The gateway reconnects to the external Zenoh router with exponential backoff
(2 seconds to 30 seconds). Its telemetry queue is bounded to eight batches:
new telemetry is dropped while disconnected rather than allowing unbounded RAM
growth. A local telemetry producer should make its own buffering decision if
lossless delivery is required.

LiveKit currently remains a direct request/reply client in `emi_mower_livekit`.
Its upload-token exchange is session setup, not a ROS data stream. It should
publish operational state as `/mower/telemetry` when that state is added; the
gateway will then handle backend-facing telemetry like every other ROS node.
