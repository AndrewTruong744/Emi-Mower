# AsyncAPI-based Zenoh generation

**Source of truth:** [`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml).
It defines native Zenoh channel addresses, operations, messages, and schemas
shared by the backend, mobile app, and Jetson gateway. It is not a REST/OpenAPI
document and does not define ROS IDL.

## Regeneration workflow

From `backend/`, install the AsyncAPI CLI once, then run:

```sh
npm install --global @asyncapi/cli
sh tools/generate_types.sh
```

The script validates Python and TypeScript model generation in a temporary
directory, then runs the repository's checked-in generators. It also formats
the gateway Rust crate if `cargo` is installed. Review every generated diff and
commit compatible updates across all affected consumers.

## Generated outputs

| Generator                                 | Outputs                                                                                                                             |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `tools/generate_zenoh_paths.mjs`          | Backend Python paths, app TypeScript paths, gateway Rust paths, and Jetson ROS-launch Python paths.                                 |
| `tools/generate_rust_zenoh_types.mjs`     | Rust structures for native Zenoh payloads used by the gateway.                                                                      |
| `tools/generate_renewal_python_types.mjs` | Bootstrap-renewal Pydantic and app TypeScript types derived from the renewal schemas.                                               |
| AsyncAPI CLI validation                   | Transient Pydantic and TypeScript models used to validate the document; it does not copy those temporary files into the repository. |

Committed generated locations include `backend/src/zenoh/generated/`,
`app/src/generated/`, and the Jetson gateway/bringup generated directories.
Do not hand-edit generated path or type outputs. If a schema needs an output
that the current generator does not cover, change the generator and add a
contract test rather than patching one consumer's generated file.

## Safe contract changes

1. Edit `zenoh_asyncapi.yaml` first and consider compatibility for every
   producer and consumer.
2. Regenerate all bindings from `backend/`.
3. Update handlers, services, ACL assumptions, app code, and gateway code as
   needed.
4. Run backend contract tests and affected app/gateway tests. A command,
   telemetry, identity, or deployment change requires cross-layer verification.

The backend telemetry contract tests intentionally detect drift between the
AsyncAPI schema and generated/runtime payload models.
