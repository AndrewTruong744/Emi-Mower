# App development

The Emi Mower mobile app is an Expo Router / React Native client for
authenticated mower monitoring, control requests, cutting-area uploads, and
LiveKit viewer credentials.

## Tech stack

- Expo 54, React Native 0.81, React 19, and Expo Router
- TypeScript, React Native Paper, React Navigation, Gesture Handler, and
  Reanimated
- Zustand for cross-screen state and TanStack React Query for server queries
  and mutations
- MapLibre for the map UI
- Native Firebase Authentication with Google Sign-In
- Native Rust Zenoh through a local Expo module
- Jest, React Native Testing Library, ESLint, Prettier, and TypeScript

## Prerequisites

- A current Node.js LTS release (using `nvm` is recommended).
- Android Studio, the Android SDK, platform tools, and a Java 17 JDK for
  Android builds.
- An Android emulator or a USB-debuggable Android device. The app is currently
  configured primarily for Android.

Install app dependencies from the `app/` directory:

```sh
npm install
```

For WSL development, use WSL's mirrored networking if the device cannot reach
Metro, allow inbound TCP port 8081 through the Windows firewall, and attach the
USB device with `usbipd` before starting Expo. The exact WSL/SDK setup is
environment-specific; use Android Studio's SDK Manager rather than committing
local SDK paths.

## Required environment variables

Create `app/.env` with the native router endpoint and Google OAuth client ID:

```env
EXPO_PUBLIC_ZENOH_URL=tls/zenoh.example.com:7447
EXPO_PUBLIC_WEB_CLIENT_ID=your-google-web-client-id
```

For local Android use `adb reverse tcp:7447 tcp:7447` and
`tls/localhost:7447`, with the local CA's public root PEM in
`EXPO_PUBLIC_ZENOH_CA_PEM`. Emulators can use `10.0.2.2` if the server certificate
includes that address in its SAN. Native TCP is available for isolated tests.
Port 7447 is the native app listener. The app authenticates and renews permissions
on the same session. See [authentication](authentication.md) and
[native module build](zenoh-wasm-react-native.md).

## Run the app

For this checkout's local macOS backend and Android emulator, run from the
repository root:

```sh
./scripts/dev.sh start
```

The launcher starts the Docker backend and its dependencies, selects the canonical
fork router configuration, starts `Medium_Phone` if necessary, forwards Android
ports, supplies the local public CA certificate, and builds/opens the native app.
Keep its terminal open for Metro. It uses the existing `backend/.env`, `app/.env`,
and Google Application Default Credentials at
`~/.config/gcloud/application_default_credentials.json`. Docker Desktop host
networking must be enabled. Set `GOOGLE_ADC_FILE`, `ANDROID_HOME`, `JAVA_HOME`
(Java 17), or `ANDROID_AVD` to override machine-specific defaults.

Run the services separately with `./scripts/dev.sh backend` and
`./scripts/dev.sh android`. Use `./scripts/dev.sh logs` for backend/router logs,
`./scripts/dev.sh status` for containers, and `./scripts/dev.sh stop` to stop
the local containers while preserving their data. Close the emulator window
separately. Google login still requires the Firebase Android app and debug
signing fingerprint to be configured.

The launcher maintains a marked block in ignored `app/.env.local` containing
the local Zenoh endpoint and public CA certificate. This keeps Expo's development
environment module consistent with the shell exports; other local settings are
preserved. Remove that block when switching back to another router environment.

For the regular Expo commands from `app/`:

```sh
npm run start
npm run android
npm run ios
```

Use `npm run start -- --host lan` when a physical device needs to reach Metro
over the local network. For a USB-connected phone in WSL, bind and attach the
device with `usbipd` in Windows, then use `adb devices` inside WSL to confirm
that Android tooling can see it.

When adding a native package or changing native Android/iOS configuration,
regenerate the native project and run an Android build:

```sh
npx expo prebuild --platform android --clean
npm run android
```

This removes and recreates the generated native project, so review any native
changes first and do not use it to discard hand-maintained native work.

## Quality commands

```sh
npm run lint
npm run typecheck
npm test
npm run test:coverage
npx prettier --check .
npx prettier --write .
```

See [testing and code coverage](testing.md) for test structure, focused Jest
commands, and coverage thresholds.
