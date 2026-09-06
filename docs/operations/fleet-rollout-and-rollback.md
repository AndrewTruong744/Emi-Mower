# Fleet rollout and rollback

This repository does not yet define a production release system. Until one is
added, every fleet rollout should have a written change record with target
mowers, versions, owner, verification evidence, and rollback version.

## Minimum release sequence

1. Run the affected offline and integration tests.
2. Validate the image, configuration, and certificate mounts in simulation or a
   bench environment.
3. Deploy to one explicitly selected non-critical mower and verify telemetry,
   command disable behaviour, and recovery from a router outage.
4. Expand only after the canary result is recorded.
5. Keep the previous deployable artifact and configuration available for
   rollback.

Firmware flashing, live command tests, and production deployment require
explicit authorization for the target mower(s).
