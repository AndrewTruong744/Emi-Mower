# Emi-Mower shared agent resources

This directory holds version-controlled, agent-neutral task procedures. The
authoritative technical content remains in [`docs/`](../docs/README.md); each
skill routes a specific workflow to the documentation and checks that matter.

Agent runtimes differ in how they discover skills. The root
[`AGENTS.md`](../AGENTS.md) instructs agents working in this repository to read
the relevant skill. Configure or package these folders separately when a
runtime requires installed skills.

Do not store credentials, certificates, logs, sessions, or personal agent
configuration here.
