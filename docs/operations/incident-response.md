# Incident response

Prioritize physical safety and preservation of evidence.

1. Stop or isolate the affected mower using the approved operational control;
   do not use a code change as an emergency stop.
2. Record mower ID, time, deployed versions, observed state, and available
   telemetry.
3. Preserve relevant Jetson, backend, and router logs without exposing keys or
   user data.
4. Investigate the applicable boundary: app command, Zenoh identity/routing,
   ROS-to-CAN bridge, or STM32 validation/watchdog.
5. Re-enable or redeploy only under the fleet rollout procedure.

Add concrete escalation contacts and approved emergency procedures here when
they exist; do not invent them in an agent skill.
