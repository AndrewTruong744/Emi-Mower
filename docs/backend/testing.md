# Backend testing, coverage, linting, and formatting

Run commands from `backend/`. Install the locked Python environment first:

```sh
uv sync
```

## Quality commands

| Command                                                                   | Purpose                                                                                    |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `uv run ruff check .`                                                     | Lints Python with pyflakes, pycodestyle, and import-order rules.                           |
| `uv run ruff check . --fix`                                               | Applies safe Ruff lint fixes. Review the diff.                                             |
| `uv run ruff format --check .`                                            | Checks Ruff formatting without changing files.                                             |
| `uv run ruff format .`                                                    | Formats Python files in place.                                                             |
| `uv run pytest -m 'not repository and not api and not zenoh_integration'` | Runs the fast Docker-free unit/service/handler test scope.                                 |
| `uv run pytest --run-integration`                                         | Runs the full suite, including Docker-backed repository, API, and Zenoh integration tests. |

## Test modes

By default, tests marked `repository`, `api`, or `zenoh_integration` are
skipped. This keeps the normal test loop Docker-free. Passing
`--run-integration` starts disposable Testcontainers PostgreSQL and Valkey,
runs migrations, and enables those marks.

API and Zenoh integration tests additionally use the session-scoped
`compose_stack` fixture. It starts `docker-compose.test.yml` with `up --build
--wait`, then tears it down with volumes and orphan containers removed. The
test stack is isolated on a bridge network and should not use local development
volumes or ports for persistent data.

Tests live under `tests/` by boundary: `services`, `repositories`, `zenoh`,
`routes`, `scripts`, `config`, and `unit`. Shared fixtures reset the disposable
database tables and Valkey database for each integration test.

## Coverage

Pytest always enables branch coverage for `src/`, prints missing lines, and
fails below 80%. It excludes package initializers, Alembic migrations, ORM
models, and scripts from the coverage source set. The threshold applies to both
the focused and integration invocations, so run a scope that exercises the code
you changed and add tests rather than weakening coverage.

For a route, telemetry schema, identity, provisioning, or Zenoh contract
change, run the affected integration tests and the relevant cross-layer checks
in addition to the local fast suite. See the repository
[verification matrix](../development/verification.md).
