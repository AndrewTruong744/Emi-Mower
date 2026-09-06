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
- Zenoh TypeScript over the remote-API WebSocket
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

Create a local `app/.env` file with the remote-API WebSocket URL and Google
web OAuth client ID:

```env
EXPO_PUBLIC_ZENOH_URL=ws://10.0.2.2:10000
EXPO_PUBLIC_WEB_CLIENT_ID=your-google-web-client-id
```

`EXPO_PUBLIC_ZENOH_URL` must use `ws://` or `wss://` and must not contain
credentials. Android emulators can reach the host through `10.0.2.2`; on a
physical Android device, use the development computer's LAN IP, for example
`ws://192.168.1.73:10000`. Port `10000` is the Zenoh remote-API WebSocket. Do
not use `0.0.0.0` (a server bind address) or the normal router port `7447`.

The app signs in with Firebase, queries `user/login` using the Firebase ID
token, then reconnects Zenoh with the short-lived user-scoped credentials it
receives. Never put Zenoh credentials or private keys in `.env`. See
[authentication](authentication.md) and [APIs and Zenoh routes](apis-and-zenoh.md)
for the full flow.

## Run the app

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
