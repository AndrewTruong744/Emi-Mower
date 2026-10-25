# Native Rust Zenoh in React Native

The app uses `app/modules/emi-zenoh`, a local Expo module, and
`src/config/nativeZenoh.ts`, its typed facade. The module currently supports
Android only. Kotlin calls JNI entry points implemented directly in
`rust/src/android.rs`; no C++ bridge is involved. Rust owns the native Zenoh
session, queries, publications, telemetry/liveliness subscriptions and transport
events.
Callbacks deliver UTF-8 JSON to JavaScript. There is no remote-API plugin or WASM
shim in this path.

## Ownership

The TypeScript adapter exposes `query`, `put`, `subscribe`, `subscribeLiveliness`, `close`,
`restoreSubscriptions` and a transport callback. Queries return one payload string
or reject their promise; samples are plain `{ key, payload, put }` values. There
are no JavaScript Zenoh configuration, encoding, reply or iterator wrappers.

| Layer | Owns |
| --- | --- |
| Rust Zenoh library | Network connections, retries, query deadlines and native declarations |
| Rust module (`lib.rs`) | Native handles, subscription keys/options for replay, and bridge payloads/errors |
| TypeScript adapter (`nativeZenoh.ts`) | Native calls and JavaScript subscription callbacks |
| App client (`zenohClient.ts`) | The active account/session, authorization expiry/renewal, reconnect sequencing and app cleanup |

A transport loss invalidates the app's authorization. After Zenoh reconnects the
same session, the app refreshes Firebase-backed authorization and asks Rust to
restore its retained declarations. Rust replays both telemetry and historical
liveliness subscriptions using the original callback IDs. JavaScript does not
retain a second list of subscription keys/options. Commands stay blocked until
authorization and replay finish; queries are not automatically resent. Account
changes and logout cancel stale results and close the old session. Native module
destruction independently releases Rust resources.

The native module permits one open or opening session. Another `connect` call
is rejected until the previous session is closed. Session IDs distinguish
successive accounts so delayed calls cannot affect a replacement session; they
do not represent a collection of concurrent sessions.

`subscribe` creates an ordinary data subscriber. `subscribeLiveliness` creates a
historical presence subscriber for mower gateway tokens. Both stay active until
closed; neither API takes an active/inactive boolean. The bridge uses an explicit
subscription kind (`data` or `liveliness`). The app chooses the keys; Rust creates,
retains and restores the declarations.

Each native call runs on Expo's shared I/O dispatcher rather than the serial
module queue. Several queries and publications can be in flight on the same
session. Every call has its own promise and returns one reply or error; replies
may complete out of order. JNI still waits synchronously on its I/O worker,
while Zenoh handles network traffic and subscription callbacks in the background.
This supports overlapping requests without introducing a reply stream or batch
error handling.

The Rust manifest uses the sibling `../zenoh/zenoh` checkout as a path dependency.
Keep the fork beside Emi-Mower in local/CI builds. `Cargo.lock` pins third-party
dependencies. Native artifacts and generated Android projects are ignored.

## Android build

Install a Java 17 JDK, Android SDK/NDK, Rust stable and Python 3. From `app/`:

```sh
npm install
npx expo prebuild --platform android --no-install
cd android
./gradlew :app:assembleDebug -PreactNativeArchitectures=arm64-v8a,x86_64
```

The Gradle task invokes `build_native.py` to install Rust Android targets and build
`libemi_zenoh_native.so` for arm64-v8a and x86_64. Gradle packages that library
through its `jniLibs` source set, and Kotlin loads it directly with
`System.loadLibrary("emi_zenoh_native")`. JNI converts UTF-8 byte arrays,
attaches Rust worker threads for callbacks, and releases the callback class
reference when the module shuts down. There are no legacy C exports.
Set `ANDROID_HOME` and optionally `ANDROID_NDK_HOME` for custom SDK/NDK locations.
The default Rust NDK is 27.1.12297006. Expo Go cannot load this custom module;
use a native development build. Android is the current verified target.

## Verification

```sh
npm run typecheck
npm run lint
npm run test:coverage
cargo +stable test --manifest-path modules/emi-zenoh/rust/Cargo.toml
# With JAVA_HOME pointing to a JDK, also exercise JNI in a desktop JVM:
cargo +stable test --manifest-path modules/emi-zenoh/rust/Cargo.toml --features jni-tests
```

Native Rust tests call the Rust transport functions against a real forked router,
including captured login, Unicode replies and command publication without reconnecting.
Facade tests cover reconnect, command gating, subscription cleanup and native
errors. Backend runtime integration tests launch a feature-gated desktop Rust
test runner, which calls the same Rust function as JNI. Requests and replies use
JSON lines over stdin/stdout; the runner closes its sessions when stdin closes.
Build it separately from `app/` with:

```sh
cargo +stable build --manifest-path modules/emi-zenoh/rust/Cargo.toml --example test-driver --features test-driver
```

The `test-driver` feature is disabled in ordinary Android builds. See
[runtime verification](../development/zenoh-runtime-verification.md) for the
backend test invocation.

The opt-in JNI test checks Unicode queries/replies, invalid requests, Java
exceptions, callbacks from Rust worker threads, listener failure recovery, shutdown and
reinitialization with the JVM's `-Xcheck:jni` enabled.
It also holds one query open while a second query and a publication complete,
then verifies that the two Unicode replies and an independent error remain
associated with their own JNI callers. It also verifies that shutdown releases
an in-flight query with an error. Facade tests verify out-of-order promise
completion and that a failed request does not affect other pending requests.
