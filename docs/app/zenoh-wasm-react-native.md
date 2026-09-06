# Zenoh WASM compatibility in React Native

`@eclipse-zenoh/zenoh-ts` brings browser-oriented WASM dependencies. Metro
treats `.wasm` files as Android assets, and the package's wrappers are loaded
during route discovery or query serialization. That can fail before the app
renders even when the app only uses the remote-API WebSocket.

The app therefore replaces the two WASM-backed dependency surfaces with
small TypeScript implementations:

| Shim                                                    | Replaces                            | Why it is needed                                                                                                                                  |
| ------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`keyExprShim.ts`](../../app/src/config/keyExprShim.ts) | Zenoh's key-expression WASM wrapper | The app sends fixed remote-API key expressions and only needs string-level key-expression helpers.                                                |
| [`leb128Shim.ts`](../../app/src/config/leb128Shim.ts)   | `@thi.ng/leb128`                    | Zenoh needs integer encode/decode helpers when serializing requests, but the package's embedded WASM module is unavailable in the Android bundle. |

[`app/metro.config.js`](../../app/metro.config.js) redirects the exact package
module requests to these source files. This mapping is deliberately narrow:
it applies the key-expression replacement only when the importer is the Zenoh
package, and aliases `@thi.ng/leb128` (including its subpaths) to the LEB128
shim.

## Creating or changing a shim

1. Identify the exact module name Metro resolves and the exact exported API
   Zenoh calls. Inspect the installed package and its call sites; do not guess
   an API from a `.wasm` filename.
2. Create a typed `.ts` module in `app/src/config/` that matches only that
   required export surface. Preserve input validation and return types.
3. Add a targeted `resolveRequest` branch in `app/metro.config.js`. Keep its
   importer/module conditions as narrow as possible so unrelated packages are
   not redirected.
4. Add focused Jest coverage under `app/tests/zenoh/` for normal values,
   boundary values, and invalid input. Update mocks only if a test imports the
   Zenoh package itself.
5. Run `npm run typecheck`, the new focused test, `npm test`, and an Android
   development build (`npm run android`) when native bundling changed.

## LEB128 contract

The TypeScript LEB128 shim exposes the six functions Zenoh needs:
`encodeULEB128`, `encodeSLEB128`, `encodeULEB128Into`, `encodeSLEB128Into`,
`decodeULEB128`, and `decodeSLEB128`. It uses bounded 64-bit `bigint` values
and limits encodings to ten bytes. Maintain those semantics rather than using
JavaScript `number` arithmetic, which would lose precision for larger values.

## Key-expression contract

The key-expression shim validates non-empty, NUL-free strings and implements
the `new_key_expr`, `join`, `concat`, `includes`, `intersects`, and
`autocanonize` calls used by the current Zenoh client. It is intentionally not
a general replacement for every Zenoh key-expression feature. If a future
Zenoh release calls another API or requires richer semantics, add only the
needed behavior with tests, or use a React-Native-compatible upstream package
when one is available.

When upgrading `@eclipse-zenoh/zenoh-ts`, re-run the Zenoh tests and validate a
native bundle: a changed internal import path can bypass Metro's redirect.
