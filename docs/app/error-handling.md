# Global error handling

The app uses one product-level error queue so operational failures are visible
above every route. The host is mounted in the root layout, inside the React
Native Paper provider, in
[`app/src/errors/GlobalErrorHost.tsx`](../../app/src/errors/GlobalErrorHost.tsx).
It is not a React error boundary: rendering/programming exceptions still need
to be fixed or handled close to the component that owns them.

## Reporting flow

Feature code reports an operational failure with `reportAppError(code, error)`
from [`reporter.ts`](../../app/src/errors/reporter.ts). The error catalog maps
the typed code to a title, priority, retryability, and presentation:

1. `reportAppError` turns the failure into an `AppError` and sends it to the
   Zustand error slice.
2. The slice ignores `silent` errors, merges matching dedupe keys occurring
   within 10 seconds, sorts the queue by priority, and retains at most five
   items.
3. `GlobalErrorHost` renders the first queued item. A `modal` remains until
   dismissed; a `toast` automatically dismisses after six seconds.

`OperationCancelled` is deliberately ignored. Cancellation during logout or a
session change is normal control flow, not an error a user should see.

## Presentation rules

| Presentation | Use it for                                        | Current examples                                                         |
| ------------ | ------------------------------------------------- | ------------------------------------------------------------------------ |
| `modal`      | Authentication failures that block use of the app | `auth.sign_in_failed`, `auth.session_failed`                             |
| `toast`      | Recoverable operational failures                  | Zenoh requests, mower commands, cutout upload, and livestream connection |
| `silent`     | Bad background data that is safely dropped        | Invalid telemetry payload                                                |

The canonical codes are in
[`app/src/errors/types.ts`](../../app/src/errors/types.ts), and their
presentation policy is in
[`app/src/errors/catalog.ts`](../../app/src/errors/catalog.ts). Add a new code
there before reporting it from a feature; do not invent string literals at the
call site.

## Local versus global failures

Expected input failures use `InputValidationError` and stay next to the input.
For example, a missing mower selection or an out-of-range joystick coordinate
does not enter the global queue. Network, protocol, service, and asynchronous
command failures do enter it.

React Query hooks should set `retry: false` for commands that must not be
automatically replayed, then report unexpected failures in `onError`. This is
especially important for mower commands: a failed request must not cause a
second command to be sent automatically.

## Adding a new globally handled failure

1. Add an `ErrorCode` and catalog entry with the smallest appropriate
   presentation and priority.
2. Report the failure at the transport or feature boundary with
   `reportAppError`.
3. Provide a feature-specific `dedupeKey` when distinct resources should be
   reported independently, for example one key per mower.
4. Keep user-safe validation errors local, and do not report expected session
   cancellation.
5. Add or update tests for the slice and the reporting feature.
