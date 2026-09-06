# APIs and Zenoh routes

**Zenoh contract source of truth:**
[`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml). The app's
generated TypeScript models and path helpers in `app/src/generated/` are
derived from that contract. Regenerate them from `backend/` with
`sh tools/generate_types.sh`; never edit them by hand.

The app connects to the Zenoh remote-API WebSocket configured by
`EXPO_PUBLIC_ZENOH_URL`. It serializes JSON and uses three transport helpers
from [`zenohClient.ts`](../../app/src/config/zenohClient.ts):

- `zenohQuery` for request/reply operations;
- `zenohPut` for one-way publications; and
- `zenohSubscribe` for live telemetry.

All mower-specific paths must retain their `{mower_id}` scope. Access is
ultimately enforced by the authenticated Zenoh session's ACL, not by UI checks.

## Zenoh routes used by the app

| Route                                             | Direction | App use                                                                                   |
| ------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------- |
| `user/login`                                      | Query     | Exchanges the Firebase ID token for user data and short-lived Zenoh credentials.          |
| `user/update_name`                                | Query     | Updates the signed-in user's display name.                                                |
| `user/update_email`                               | Query     | Synchronizes an email change after Firebase updates the identity.                         |
| `mower/{mower_id}/joystick`                       | Put       | Publishes normalized `x`/`y` joystick input.                                              |
| `mower/{mower_id}/command`                        | Query     | Sends one state-changing command with a command ID and waits for acceptance or rejection. |
| `mower/{mower_id}/telemetry/{telemetry_type}/old` | Query     | Fetches cursor-paginated telemetry history for charts.                                    |
| `mower/{mower_id}/telemetry`                      | Subscribe | Receives live telemetry; the app subscribes with `*` and keeps only its owned mowers.     |
| `mower/{mower_id}/livekit/consume`                | Query     | Requests short-lived viewer credentials for a mower's LiveKit room.                       |
| `user/cutouts/upload-url`                         | Query     | Requests a short-lived signed upload URL for a cutting-area image.                        |
| `user/cutouts/uploaded`                           | Put       | Tells the backend whether that signed upload succeeded so it can verify or discard it.    |

Generated helpers also expose routes for assigning and renaming mowers,
cutout download, LiveKit publishing, and mower certificate renewal. They are
not currently invoked by the mobile app. Certificate-renewal bootstrap routes
are mower infrastructure routes, not app routes.

## Other external APIs

| Service                 | How the app uses it                                                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Google Sign-In          | Obtains Google identity tokens on the device.                                                                                                                                          |
| Firebase Authentication | Establishes and observes the native Firebase user session; supplies Firebase ID tokens to the backend.                                                                                 |
| Google Cloud Storage    | Receives a signed `PUT` URL from Zenoh and uploads a cutout image directly. The app does not hold GCS credentials.                                                                     |
| LiveKit                 | Receives room-scoped viewer credentials through Zenoh. The current UI manages the credential connection state; attaching a native video renderer is still a separate integration step. |

There is no separate REST client in the app. The direct signed GCS upload is
the only ordinary HTTP request path; backend operations use Zenoh.

## Change procedure

For a route or schema change, update the AsyncAPI document first, regenerate
the bindings, then update the backend, app, and Jetson consumers together.
Follow the cross-layer verification guidance in
[the Zenoh interface documentation](../interfaces/zenoh.md).
