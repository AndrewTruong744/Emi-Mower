# Verification matrix

| Change area | Primary checks |
| --- | --- |
| Mobile app | `npm run lint`, `npm test`, and `npm run typecheck` from `app/` as applicable |
| Backend | Ruff and the relevant pytest scope from `backend/`; use `--run-integration` for integration changes |
| Zenoh contract | Regenerate from `backend/zenoh_asyncapi.yaml`; run backend contract tests plus affected app and gateway tests |
| Jetson / ROS | `nvidia_jetson/scripts/test.sh`; run containerized Rust checks for Rust/ROS changes |
| STM32 | Host protocol tests, formatting, and firmware build described in `stm32/README.md` |
| Infrastructure | Run the documented Terraform validation/plan workflow before applying changes |

Select the smallest meaningful checks for a local change. Any alteration to
motion behaviour, fleet identity, a wire contract, or deployment configuration
requires cross-layer evidence.
