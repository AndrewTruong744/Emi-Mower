from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1]
CONFIG = PACKAGE_ROOT / "config" / "zenoh_client.json5"
REAL_LAUNCH = PACKAGE_ROOT / "launch" / "real.launch.py"
SIM_LAUNCH = PACKAGE_ROOT / "launch" / "sim.launch.py"
COMPOSE = PACKAGE_ROOT.parents[2] / "docker-compose.yml"


def test_zenoh_client_config_is_a_tls_client_template_fallback() -> None:
    text = CONFIG.read_text()
    assert 'mode: "client"' in text
    assert '"tls/zenoh-router:7448"' in text
    assert "connect_certificate" in text
    assert "connect_private_key" in text
    assert "\n        certificate:" not in text
    assert "\n        private_key:" not in text
    assert "localhost" not in text


def test_local_ros_compose_verifies_the_host_router_certificate() -> None:
    text = COMPOSE.read_text()
    assert "tls/host.docker.internal:7448" in text
    assert "ZENOH_VERIFY_NAME_ON_CONNECT: ${ZENOH_VERIFY_NAME_ON_CONNECT:-true}" in text
    assert "tls/host.docker.internal:7449" in text
    assert (
        "ZENOH_BOOTSTRAP_VERIFY_NAME_ON_CONNECT: "
        "${ZENOH_BOOTSTRAP_VERIFY_NAME_ON_CONNECT:-true}"
    ) in text
    assert "host.docker.internal:host-gateway" in text


def test_real_and_sim_launches_share_the_zenoh_ros_transport() -> None:
    text = REAL_LAUNCH.read_text() + SIM_LAUNCH.read_text()
    assert 'name="RMW_IMPLEMENTATION"' in text
    assert 'value="rmw_zenoh_cpp"' in text
    assert 'name="ZENOH_SESSION_CONFIG_URI"' in text
    assert 'name="ZENOH_CONFIG"' in text
    assert 'EnvironmentVariable("ZENOH_SESSION_CONFIG_URI"' in text
    assert "respawn=True" in text


def test_real_uses_can_while_sim_uses_the_mujoco_command_topic() -> None:
    real = REAL_LAUNCH.read_text()
    sim = SIM_LAUNCH.read_text()
    assert 'executable="stm32_bridge"' in real
    assert 'executable="sim_command_sink"' in sim
    assert 'executable="sim_bridge"' in sim
    assert '("/teleop/cmd_vel", teleop_topic)' in sim
    assert '("/sim/cmd_vel", sim_topic)' in sim
    assert "depthai_ros_driver" not in sim
    assert "sllidar_ros2" not in sim


def test_launches_use_the_single_native_zenoh_gateway() -> None:
    real = REAL_LAUNCH.read_text()
    sim = SIM_LAUNCH.read_text()
    assert 'package="emi_mower_zenoh_gateway"' in real
    assert 'package="emi_mower_zenoh_gateway"' in sim
    assert 'executable="zenoh_gateway"' in real
    assert 'executable="zenoh_gateway"' in sim
    assert "teleop_gateway" not in real + sim
    assert 'package="emi_mower_boundary"' in real
    assert 'package="emi_mower_boundary"' in sim
    assert 'executable="boundary_cutout_node"' in real + sim
