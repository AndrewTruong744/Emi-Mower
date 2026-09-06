# Safety and trust boundaries

Software changes must preserve independent controls; an AI workflow or operator
procedure is not itself a safety mechanism.

## Motion

The STM32 validates CAN message identity, format, checksum, and sequence
progression. It makes output safe for disabled, invalid, or stale commands.
The Jetson also sends a disabled zero-velocity frame when ROS commands go
stale. See [the CAN motion contract](../interfaces/can-motion.md).

## Fleet identity

Each mower receives a unique identifier, mTLS client credentials, and
least-privilege Zenoh ACLs during trusted provisioning. Treat certificate
issuance, credential replacement, ACL reconciliation, and mower reassignment as
operational changes with an auditable outcome. See
[mower provisioning](../operations/mower-provisioning.md).

## Change safety

Do not flash firmware, start a physical mower, rotate production credentials,
or delete fleet data as part of an implementation task without explicit
authorization and an approved environment. Run offline or simulation checks
first whenever they cover the change.
