# Testing, coverage, and code quality

Run commands from the [`app/`](../../app/) directory. The minimum checks for a
typical app change are lint, the affected Jest tests, and TypeScript checking;
the repository verification matrix is in
[`docs/development/verification.md`](../development/verification.md).

## Commands

| Command                                                     | Purpose                                             |
| ----------------------------------------------------------- | --------------------------------------------------- |
| `npm run lint`                                              | Runs Expo's ESLint configuration.                   |
| `npm run typecheck`                                         | Runs `tsc --noEmit`.                                |
| `npm test`                                                  | Runs the full Jest suite serially.                  |
| `npm run test:coverage`                                     | Runs the full suite and writes the coverage report. |
| `npx jest tests/hooks/useMowerCommand.test.tsx --runInBand` | Runs one focused test file.                         |
| `npx prettier --check .`                                    | Checks formatting without changing files.           |
| `npx prettier --write .`                                    | Formats app files in place.                         |
| `npm run start`                                             | Starts Expo/Metro.                                  |
| `npm run android`                                           | Builds and runs the Android native app.             |
| `npm run ios`                                               | Builds and runs the iOS native app.                 |

Run `npm install` once after checking out or when `package-lock.json` changes.
The test setup supplies safe test values for the required Expo public
environment variables, so Jest does not require a real service connection.

## Test layout

Jest discovers `tests/**/*.test.[jt]s?(x)`. Tests are grouped by the code they
exercise:

- `tests/components/` for rendered UI and interaction behavior;
- `tests/hooks/` for feature and API hooks;
- `tests/store/` for Zustand slice behavior and resets;
- `tests/zenoh/` for session, telemetry, and compatibility-shim behavior; and
- `tests/config/` for configuration validation.

`tests/mocks/` replaces native Firebase, Google Sign-In, MapLibre, gesture,
animation, and Zenoh dependencies. Keep unit tests deterministic: do not use a
real Zenoh router, Firebase project, or device service in the Jest suite.

## Coverage

The Jest configuration collects coverage from hooks, store code, Zenoh code,
the Zenoh client and compatibility shims, and most components. Generated files
and selected platform-only or purely typed files are excluded. The enforced
global threshold is 80% for branches, functions, lines, and statements.

Use `npm run test:coverage` before handing off behavior changes. If a new
source area is intentionally excluded, document why in `jest.config.js` rather
than silently weakening the global threshold.

## Choosing checks

Run the smallest relevant test first while iterating, then the appropriate
full checks before handoff. Changes to a Zenoh route or generated model need
regeneration plus contract and affected app tests; command-path changes require
the wider cross-layer checks described in the interface documentation.
