from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]


def test_rust_package_pins_zenoh_to_router_baseline() -> None:
    cargo = (PACKAGE_ROOT / "Cargo.toml").read_text()
    assert 'zenoh = "=1.9.0"' in cargo
    assert 'rclrs = "0.7"' in cargo
    assert 'serialport = "4"' in cargo


def test_rust_package_exposes_the_control_executables() -> None:
    cargo = (PACKAGE_ROOT / "Cargo.toml").read_text()
    for executable in ("teleop_gateway", "stm32_bridge", "sim_command_sink"):
        assert f'name = "{executable}"' in cargo
    assert (PACKAGE_ROOT / "tests" / "control_flow.rs").is_file()
