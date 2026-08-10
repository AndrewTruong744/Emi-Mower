from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
CONFIG = PACKAGE_ROOT / "config" / "zenoh_client.json5"
LAUNCH = PACKAGE_ROOT / "launch" / "launch_all_nodes.py"


def test_zenoh_client_config_targets_backend_mtls_router() -> None:
    text = CONFIG.read_text()
    assert 'mode: "client"' in text
    assert '"tls/192.168.1.73:7448"' in text
    assert "connect_certificate" in text
    assert "connect_private_key" in text
    assert "\n        certificate:" not in text
    assert "\n        private_key:" not in text
    assert "7447" not in text


def test_ros_and_python_zenoh_load_the_same_config() -> None:
    text = LAUNCH.read_text()
    assert 'name="RMW_IMPLEMENTATION"' in text
    assert 'value="rmw_zenoh_cpp"' in text
    assert 'name="ZENOH_SESSION_CONFIG_URI"' in text
    assert 'name="ZENOH_CONFIG"' in text
