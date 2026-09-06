# Google/Firebase and Zenoh authentication

The app has two linked authentication layers:

1. Google Sign-In establishes a native Firebase user session on the device.
2. The app exchanges that Firebase ID token through Zenoh and reconnects with
   the returned user-scoped Zenoh credentials.

The implementation lives in
[`useGoogleAuth.ts`](../../app/src/hooks/useGoogleAuth.ts),
[`useAuthSessionBootstrap.ts`](../../app/src/hooks/auth/useAuthSessionBootstrap.ts),
and [`UserLogin.ts`](../../app/src/zenoh/UserLogin.ts).

## Sign-in lifecycle

```text
Google Sign-In → Google ID/access tokens → Firebase credential
    → Firebase auth-state listener → Firebase ID token
    → guest Zenoh query: user/login → user data + short-lived Zenoh token
    → authenticated Zenoh session → owned-mower telemetry subscription
```

`useGoogleAuth` configures Google Sign-In with
`EXPO_PUBLIC_WEB_CLIENT_ID`, checks Play Services on Android, obtains the
Google tokens, and signs into Firebase with a Google credential. It does not
directly mark the app signed in. The Firebase auth-state listener owns the
transition so the app becomes `authenticated` only after the Zenoh exchange,
user state, mower state, and telemetry subscription have succeeded.

## Zenoh session lifecycle

The app initially opens the configured remote-API WebSocket without user
credentials and queries `user/login` with Firebase's ID token. The response
contains user data, a user ID, and a one-time/short-lived Zenoh password. The
client immediately closes or replaces the guest session and reconnects with
those credentials embedded only in the in-memory WebSocket URL. Subsequent
queries, publications, and subscriptions reuse that authenticated session.

The session generation stored in Zustand prevents stale asynchronous work from
an old login from updating a new session. On sign-out or a missing Firebase
user, the app clears authenticated React Query data, tears down subscriptions,
closes Zenoh, and resets user-scoped store state before exposing the login
route.

## Configuration and secrets

The app requires these Expo public build-time settings:

```env
EXPO_PUBLIC_ZENOH_URL=wss://example.invalid:10000
EXPO_PUBLIC_WEB_CLIENT_ID=your-google-web-client-id
```

`EXPO_PUBLIC_ZENOH_URL` must be a `ws://` or `wss://` URL with no username or
password. `EXPO_PUBLIC_WEB_CLIENT_ID` identifies the OAuth client and is not a
client secret. Never place a Google client secret, Firebase service-account
key, Zenoh user password, router administrator credential, certificate private
key, or CA private key in the mobile app, its `.env` file, or its build output.

For local Android connection details, see [development](development.md).

## Failure handling

Sign-in/session failures are reported through the global error system as
blocking authentication errors. Logout and session replacement deliberately
cancel outstanding Zenoh work; those cancellations are ignored rather than
shown as errors. See [global error handling](error-handling.md) for the queue
and presentation rules.
