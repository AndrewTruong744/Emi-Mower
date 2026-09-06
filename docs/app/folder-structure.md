# App folder structure

The mobile client is an Expo Router application. Keep route files thin, place
rendering in components, place reusable stateful/transport behavior in hooks,
and keep cross-screen state in the Zustand store.

```text
app/
├── src/app/          Expo Router route groups and screen entry points
├── src/components/   Presentational UI, grouped by feature
├── src/hooks/        Stateful feature hooks and API/query hooks
├── src/store/        Zustand bound store, types, and feature slices
├── src/config/       Runtime integration and provider configuration
├── src/zenoh/        Zenoh session-specific workflows and telemetry parsing
├── src/errors/       Error taxonomy, reporter, and global presentation host
├── src/generated/    Generated Zenoh models and paths — do not hand-edit
├── src/constants/    Shared layout and theme constants
├── src/assets/       Bundled image assets
└── tests/            Jest tests, feature mirrors, and native/service mocks
```

## Responsibilities

### Routes and components

`src/app/` defines navigation and route groups such as `(auth)` and `(tabs)`.
It composes providers and feature components; it should not contain network
requests or durable business state. `src/components/` renders screens and
feature UI (`map`, `mowers`, `controller`, `settings`, and shared `ui`). A
component should receive data and callbacks through props or focused selectors
instead of owning transport details.

### Hooks

`src/hooks/` is the home for reusable stateful behavior. Feature hooks such as
`map/useMap`, `controller/useController`, and `mowers/useMowers` coordinate
screen behavior. `hooks/api/` contains React Query queries and mutations for
Zenoh-backed requests. `hooks/auth/` owns the Firebase-session bootstrap and
route redirect lifecycle.

Use a hook when behavior needs React state, effects, derived state, or a
transport call. Keep a transport operation in an API hook rather than in a UI
component so it can be tested and given consistent error handling.

### Global and server state

`src/store/useBoundStore.ts` composes small Zustand slices for auth, user,
mowers, map session state, theme preference, and the global error queue. Put
only cross-screen client state here. State that is server-derived, cacheable,
or mutation-oriented belongs in React Query hooks; temporary control/form state
normally belongs in the component or feature hook.

### Integration boundaries

`src/config/` owns environment validation, Firebase, React Query, the Zenoh
client, and React Native compatibility shims. `src/zenoh/` builds on that
client for the login handoff and live telemetry lifecycle. `src/errors/`
provides one centralized operational-error policy rather than feature-specific
ad hoc alerts.

`src/generated/zenoh.ts` and `src/generated/zenohPaths.ts` come from
`backend/zenoh_asyncapi.yaml`. Change the contract and regenerate; do not edit
these outputs directly.

## Tests and imports

`tests/` mirrors the feature boundaries (`components`, `hooks`, `store`,
`zenoh`, and `config`) and provides mocks for native modules. The `@/` import
alias resolves to `src/`; use it for app modules instead of long relative
paths. Place a new test alongside the closest mirrored feature folder.
