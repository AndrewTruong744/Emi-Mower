from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]


def test_rust_package_pins_zenoh_to_router_baseline() -> None:
    cargo = (PACKAGE_ROOT / "Cargo.toml").read_text()
    assert 'zenoh = "=1.9.0"' in cargo


def test_rust_package_has_integration_tests() -> None:
    assert (PACKAGE_ROOT / "tests" / "zenoh_compatibility.rs").is_file()
