# Zenoh runtime authorization verification

Verified locally on 2026-10-11. The sibling `../zenoh` checkout is based on
Zenoh 1.10.1, original revision `74051d0c`. Android is the verified mobile target.
See [router administration](../backend/zenoh-routers.md) and
[Android build instructions](../app/zenoh-wasm-react-native.md).

## Results

| Layer | Check | Result |
| --- | --- | --- |
| Zenoh fork | Library tests with `internal,unstable` | 45 passed |
| Zenoh fork | Existing `acl` integration tests | 10 passed |
| REST plugin | Library and management authentication tests | 11 passed |
| Mobile Rust | Native bridge tests | 2 passed |
| Android app | Jest coverage suite | 48 suites, 127 tests passed; coverage gates passed |
| Backend | Full pytest suite with `--run-integration` | 232 passed; 92.42% coverage |
| Jetson gateway | Containerized `gateway_contract` suite | 6 passed |
| Code checks | Rust format/Clippy, changed Python Ruff, TypeScript typecheck | Passed |
| App lint | Expo lint | Passed with one existing `useLivestream` hook dependency warning |
| Contract | AsyncAPI validation and generated binding `--check` | Passed |
| Android build | Gradle `:app:assembleDebug`, arm64-v8a and x86_64 | Passed |
| Android bundle | Expo Android Hermes export | Passed |

The debug APK is generated at
`app/android/app/build/outputs/apk/debug/app-debug.apk`. Both architectures
contain `libemi_zenoh_native.so` and `libemi_zenoh_bridge.so`.

Those artifacts describe the earlier C++ JNI adapter. The current Android
module implements JNI in Rust and packages only `libemi_zenoh_native.so`;
see the [current native module build instructions](../app/zenoh-wasm-react-native.md).

## Cross-layer tests

`backend/tests/zenoh/test_fork_runtime.py` runs the actual backend login handler,
protected REST management API and mobile Rust transport against isolated fork
routers, using both TCP and TLS. It verifies guest denial, login authorization, owned mower
command access, foreign mower denial, changing the mower scope on the same live
connection, REST bypass rejection and revocation. Firebase and ownership
repositories use deterministic stubs; router capture and authorization are real.
Python launches the Rust `test-driver` example and exchanges JSON lines over
stdin/stdout. The runner calls the transport's Rust functions directly; the
mobile library no longer exports a C interface for tests.
The TLS test uses a server-authenticated public app listener and a separate mTLS
backend listener. Its ephemeral CA signing key remains only in host memory.

Set these artifact paths when running the backend suite:

```sh
export ZENOH_FORK_ROUTER_BIN=/path/to/zenoh/target/debug/zenohd
export ZENOH_FORK_REST_PLUGIN=/path/to/zenoh/target/debug/libzenoh_plugin_rest.dylib
export EMI_ZENOH_TEST_DRIVER=/path/to/Emi-Mower/app/modules/emi-zenoh/rust/target/debug/examples/test-driver
.venv/bin/pytest --run-integration -q
```

On Linux use `.so` for the REST plugin. Build the router and REST plugin
**together** with `cargo build -p zenohd -p zenoh-plugin-rest`. Build the desktop
runner from the mobile Rust crate with
`cargo build --example test-driver --features test-driver`. The artifact tests
skip when these paths are absent.

Fork tests also cover single-use nonces, foreign connection binding, expiry,
existing subscription delivery, invalid policy replacement, cached publisher
revocation, reusing a Zenoh ID without inheriting authorization, and concurrent
policy updates with unrelated heartbeat traffic.

## Scope and limits

This establishes local functional behavior and Android build compatibility.
Physical Android devices, physical mowers, and production fleet endpoints were
not exercised. The automated cross-layer tests use Firebase stubs; the additional
emulator check below used an existing real Firebase session. No throughput or latency benchmark was run.
Policies are in memory and require reconciliation after router restart. Previously
denied declarations need redeclaration after permission additions. Listener TLS
certificate/trust-root hot reload is outside this implementation; certificate-CN
permission changes are supported live. See the router documentation for expiry,
revocation and routing metadata behavior.


## Local Android startup — 2026-10-15

Started the persistent local Docker stack and the `Medium_Phone` ARM64 emulator
with `scripts/dev.sh`. The native app rendered its dashboard, restored its saved
Firebase login, and completed backend authorization. The protected app-router
management API confirmed an authorized live transport. Backend health and both
management API authentication gates were checked.

Launch verification exposed and fixed an Android ELF dependency containing an
absolute host build path. The native Rust build now emits
`SONAME=libemi_zenoh_native.so`; both ARM64 and x86_64 JNI bridge dependencies
were inspected to confirm they reference that packaged name. Expo development
configuration is synchronized through a marked block in ignored `.env.local`.
Firebase Admin now receives the configured project ID explicitly, because a
mounted user ADC document may not provide one. ADC remains mounted read-only
from the developer's host file.

After these startup fixes, all 127 app tests, TypeScript typecheck, and the 12
focused backend service/startup tests passed. Rust formatting, changed Python
Ruff checks, shell syntax and diff whitespace checks passed. The emulator and
Metro remain available for interactive use; no physical mower commands were sent.
