# Mobile app

The Expo/React Native app provides user authentication, mower views, controls,
telemetry presentation, boundaries, and media features. Its Zenoh client uses
the remote API WebSocket; setup and local connection configuration are
documented in [development](development.md).

## App guides

- [Capabilities](capabilities.md) — user-facing features and their current
  boundaries.
- [Development](development.md) — setup, local Zenoh connection, and app
  commands.
- [Folder structure](folder-structure.md) — where routes, UI components,
  hooks, state, configuration, and generated bindings belong.
- [Authentication](authentication.md) — Google/Firebase sign-in and the
  scoped Zenoh session lifecycle.
- [APIs and Zenoh routes](apis-and-zenoh.md) — external APIs and the exact
  Zenoh routes called or subscribed to by the app.
- [Global error handling](error-handling.md) — reporting, deduplication, and
  presentation of operational errors.
- [Testing and code coverage](testing.md) — test layout, coverage thresholds,
  and local quality commands.
- [Zenoh WASM compatibility](zenoh-wasm-react-native.md) — maintaining the
  TypeScript shims that allow Zenoh to run in React Native.

Before changing mower commands or telemetry handling, read the
[Zenoh interface contract](../interfaces/zenoh.md). The app must preserve the
per-mower route scope supplied by the backend and Jetson runtime.

Use the app's lint, test, and typecheck commands described in
[development verification](../development/verification.md).
