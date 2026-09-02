from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]


def test_control_package_has_no_native_zenoh_dependency() -> None:
    cargo = (PACKAGE_ROOT / "Cargo.toml").read_text()
    assert "zenoh" not in cargo
    assert 'rclrs = "0.7"' in cargo
    assert 'socketcan = "3.6"' in cargo


def test_rust_package_exposes_the_control_executables() -> None:
    cargo = (PACKAGE_ROOT / "Cargo.toml").read_text()
    for executable in ("stm32_bridge", "sim_command_sink"):
        assert f'name = "{executable}"' in cargo
    assert (PACKAGE_ROOT / "tests" / "control_flow.rs").is_file()
