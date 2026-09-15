# System overview

Emi-Mower is a fleet system with four runtime layers:

```text
Mobile app
  -> Zenoh command and telemetry routes
  -> Backend identity, fleet data, router ACLs, and media-token services
  -> Jetson ROS runtime
  -> SocketCAN
  -> STM32 motor controller and H-bridges
```

The app sends a per-mower joystick command to Zenoh. The Jetson gateway
validates its mower identity, translates the command into ROS, and the control
package emits a CAN command. The STM32 validates CAN frames and owns the final
watchdog and motor-safe state.

Telemetry travels in the opposite direction: ROS producers publish typed
telemetry, the Jetson gateway converts it to the backend-facing Zenoh contract,
and backend services persist and expose it to the app.

## Boundaries that must remain explicit

- The backend/factory host authorizes each mower's identity and mTLS
  credentials; the CA private key never goes to a Jetson. The local dedicated
  step-ca service owns the local CA state in persistent storage; application
  containers receive only their own leaf credentials. Production should use an
  offline root and an online intermediate signer.
- `MOWER_ID` scopes routes and credentials to one mower.
- The Jetson may make commands safe when ROS input goes stale, but the STM32 is
  the final safety authority for motor output.
- The backend's `zenoh_asyncapi.yaml` defines the app/backend/Jetson telemetry
  contract. Generated clients are derived outputs.

Read [interfaces](../interfaces/README.md) before changing a cross-layer
contract and [operations](../operations/README.md) before changing fleet
identity or deployment behaviour.
