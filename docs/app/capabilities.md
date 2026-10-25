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
- Add a registered, active, unassigned mower by UUID. The backend verifies its
  existence and ownership before the app adds it to the displayed fleet.
- Remove an owned mower from the account or transfer it to an existing app
  account using the recipient's User ID (UID) from Settings. Confirmation is
  required. Removal unassigns the mower; it preserves its records and telemetry.
  Ownership changes update live Zenoh permissions and preserve unrelated traffic.
  **Refresh fleet** reloads the authoritative list, including received transfers
  and removal of any old local-only entries, without signing out.
- Request paginated historical metrics for the selected mower, including motor
  and IMU values where telemetry is available.
- Use the controller screen to publish normalized joystick input every 50 ms
  while held away from center, with speed proportional to joystick distance,
  and a 3% zero band on each axis for straight driving and in-place turns,
  and send one-off power, autonomy, and emergency-stop commands. The command route
  returns an acceptance result; the UI must not be treated as proof of physical
  motion or safety-state execution.
- Request short-lived LiveKit viewer credentials for a selected mower. The
  present livestream screen manages that connection state; a native video
  renderer still needs to be attached to display video.
- Draw a polygonal cutting boundary on a map, review it, and upload the
  resulting cutout image for all account mowers. The backend issues a signed
  upload URL and verifies the completion notice before publishing a short-lived
  download URL to each mower currently owned by the user. The app retains the
  upload details; the backend does not persist a cutout record.
- Start, pause, resume, or cancel the app's map-session view for a confirmed
  boundary, and show mower markers during that session. The session starts only
  after the cutout upload succeeds; on failure, the drawing remains available
  for another attempt.

## Current UI-only behavior

The Rename Mower dialog currently updates the local Zustand store. It does not
call `mower/{mower_id}/update_name`, so mower nicknames edited there reset on
sign-out/session reset. Account display-name updates use the backend.

## Important boundaries

The app receives only the per-user, per-mower scope issued by the backend. It
does not store the CA private key, create mower certificates, or bypass Zenoh
ACLs. A cutout upload succeeds only as far as the signed-upload and backend
verification workflow reports; its eventual use by a mower remains a separate
backend/gateway responsibility.
