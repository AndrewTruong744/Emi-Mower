# What the app can do

The current Expo/React Native app is an authenticated mobile companion for an
Emi mower fleet. It presents user-scoped information and sends requests to
the backend through Zenoh; it is not the final safety authority for mower
motion. The STM32 independently validates motor commands and watchdog timing.

## Available user workflows

- Sign in with Google and manage the signed-in display name, email flow, theme,
  and sign-out session.
- View the mowers returned for the authenticated account, select a mower, and
  inspect its session telemetry, status, battery, position, and charts.
- Request paginated historical metrics for the selected mower, including motor
  and IMU values where telemetry is available.
- Use the controller screen to publish normalized joystick input and send
  one-off power, autonomy, and emergency-stop commands. The command route
  returns an acceptance result; the UI must not be treated as proof of physical
  motion or safety-state execution.
- Request short-lived LiveKit viewer credentials for a selected mower. The
  present livestream screen manages that connection state; a native video
  renderer still needs to be attached to display video.
- Draw a polygonal cutting boundary on a map, review it, and upload the
  resulting cutout image for all selected account mowers. The backend issues a
  signed upload URL and verifies the completion notice before the mower uses
  the cutout.
- Start, pause, resume, or cancel the app's map-session view for a confirmed
  boundary, and show mower markers during that session.

## Current UI-only behavior

The Add Mower and Rename Mower dialogs currently update the local Zustand
store. They do not call the generated `user/add_mower` or
`mower/{mower_id}/update_name` routes, so those changes are not persisted
through the backend and reset on sign-out/session reset. Treat these controls
as local UI behavior until their API hooks are implemented.

## Important boundaries

The app receives only the per-user, per-mower scope issued by the backend. It
does not store the CA private key, create mower certificates, or bypass Zenoh
ACLs. A cutout upload succeeds only as far as the signed-upload and backend
verification workflow reports; its eventual use by a mower remains a separate
backend/gateway responsibility.
