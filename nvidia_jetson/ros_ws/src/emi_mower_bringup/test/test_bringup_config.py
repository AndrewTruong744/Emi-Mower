from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
CONFIG = PACKAGE_ROOT / "config" / "zenoh_client.json5"
REAL_LAUNCH = PACKAGE_ROOT / "launch" / "real.launch.py"
SIM_LAUNCH = PACKAGE_ROOT / "launch" / "sim.launch.py"


def test_zenoh_client_config_is_a_tls_client_template_fallback() -> None:
    text = CONFIG.read_text()
    assert 'mode: "client"' in text
    assert '"tls/zenoh-router:7448"' in text
    assert "connect_certificate" in text
    assert "connect_private_key" in text
    assert "\n        certificate:" not in text
    assert "\n        private_key:" not in text
    assert "localhost" not in text


def test_real_and_sim_launches_share_the_zenoh_ros_transport() -> None:
    text = REAL_LAUNCH.read_text() + SIM_LAUNCH.read_text()
    assert 'name="RMW_IMPLEMENTATION"' in text
    assert 'value="rmw_zenoh_cpp"' in text
    assert 'name="ZENOH_SESSION_CONFIG_URI"' in text
    assert 'name="ZENOH_CONFIG"' in text
    assert 'EnvironmentVariable("ZENOH_SESSION_CONFIG_URI"' in text
    assert "respawn=True" in text


def test_real_uses_uart_while_sim_uses_the_mujoco_command_topic() -> None:
    real = REAL_LAUNCH.read_text()
    sim = SIM_LAUNCH.read_text()
    assert 'executable="stm32_bridge"' in real
    assert 'executable="sim_command_sink"' in sim
    assert "depthai_ros_driver" not in sim
    assert "sllidar_ros2" not in sim
