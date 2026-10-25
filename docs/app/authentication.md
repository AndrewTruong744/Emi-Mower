# Google/Firebase and Zenoh authentication

Google Sign-In establishes the native Firebase session. The app then opens one
native Rust Zenoh session and queries `user/login` with its Firebase ID token.
The app router captures that connection; the backend verifies identity and
ownership and authorizes the existing transport through protected REST.

```text
Google → Firebase → guest native Zenoh session → user/login
    → backend validates identity → router applies permissions
    → authorized response → subscriptions and commands on the same session
```

`UserLogin.ts` coalesces overlapping login requests. `zenohClient.ts` owns renewal
at 80% of the returned lifetime, expiry and reconnect sequencing. Transport
reconnect events trigger a fresh login, followed by Rust replaying its retained
subscriptions on the same native session. Commands are blocked while the
transport is disconnected, unauthenticated or restoring subscriptions. The router independently
enforces expiry, so suspended apps do not retain expired privileges.

The Zustand auth generation cancels stale asynchronous operations. Changing
Firebase identity closes the previous native session before opening another;
authorization refreshes for the same identity retain its existing connection. Logout closes
subscriptions and the native session and clears user state. No Zenoh password or
JWT grant is returned to the app; `UserLoginResponse` contains `authorized`,
`expires_in`, `user_id` and `user_data`.

## Configuration

```env
EXPO_PUBLIC_ZENOH_URL=tls/zenoh.example.com:7447
EXPO_PUBLIC_WEB_CLIENT_ID=your-google-web-client-id
```

Use native `tls/host:port` endpoints. `tcp/host:port` is supported for isolated
local development/tests. For a private development CA, supply its **public** root
PEM through `EXPO_PUBLIC_ZENOH_CA_PEM`. The hostname must match the router's
certificate SAN. With a publicly trusted server certificate, bundled Web PKI roots are
used. Never disable verification to accommodate a hostname mismatch.

The management token, Firebase service account, mower keys and CA private key
must never enter the app or its build. See [native Zenoh](zenoh-wasm-react-native.md)
and [development](development.md) for Android builds.


## Settings: name and Google account

Display names support spaces and punctuation, are trimmed, and must be 1–64
characters without control characters. The backend stores the app display name.
Settings shows “Saving name…” while waiting for the backend, followed by an
inline success or failure message. The displayed profile changes only after the
backend confirms the saved name.

**Change Google Account** replaces the application's Google login and moves all
mowers to the selected account. It does not edit the Google account's Gmail
address. The app obtains the replacement Firebase token through a temporary
secondary Firebase app, keeping the original Firebase and Zenoh sessions active
until the backend confirms the transfer. It clears Google's saved selection
before sign-in so the account chooser opens again, without signing out the
active Firebase user. The temporary Firebase app normalizes absent Database,
Storage and Messaging options to empty strings required by RNFirebase's Android
initializer; Realtime Database is not required. Cancelling cleans up that
temporary app and leaves ownership and the active session unchanged.
Choosing the same Google account is
rejected without changing anything.

The backend verifies both identities, requires a verified Google destination,
and performs the ownership changes and removal of the original account in one
PostgreSQL transaction. It preserves mower UUIDs, certificates, telemetry and
any mowers already owned by the destination. A new destination inherits the
source display name; an existing destination retains its own profile.

Old-account sessions lose their query, publication and subscription permissions
before commit. Only the pending switch confirmation may leave the old transport.
Profile, mower-list, mower-detail and retired credential-registry caches are
cleared. Login and ACL reconciliation use locked PostgreSQL ownership snapshots,
so cached ownership or a concurrent login cannot restore the old permissions.
Failure before commit rolls back the database transfer.

After confirmation, the app signs Firebase into the replacement account. Its
auth-state listener closes the old Zenoh session and logs in the replacement UID.
The original backend account/email record has been removed. Signing in through
the original Google account later creates a fresh backend account with no mowers.
External Google/Firebase identities are not deleted by this operation.

If Firebase handoff fails after the backend has confirmed the transfer, sign in
with the selected destination account to finish; its mower ownership is already
saved. No second transfer is needed.
