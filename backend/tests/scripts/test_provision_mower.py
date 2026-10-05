import argparse
import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from src.scripts import provision_mower


def test_simulated_router_acl_preserves_internal_access_and_scopes_each_mower(
    monkeypatch, tmp_path
):
    base = provision_mower.BACKEND_ROOT / "zenoh-router-mtls.json5"
    (tmp_path / "zenoh-router-mtls.json5").write_text(base.read_text())
    env_file = tmp_path / ".env"
    env_file.write_text("JWT_SECRET=local-test\nZENOH_MTLS_CONFIG_FILE=old.json5\n")
    monkeypatch.setattr(provision_mower, "BACKEND_ROOT", tmp_path)
    run = Mock()
    monkeypatch.setattr(provision_mower.subprocess, "run", run)
    identities = [
        "b688f3ea-b8df-4112-8ffe-63da14f851a5",
        "0a35e3e0-ff31-4b58-bc88-31f6e288fdb2",
    ]
    provision_mower.configure_simulated_router_acl(identities)
    config_file = tmp_path / ".sim" / "zenoh-router-mtls.json5"
    acl = json.loads(config_file.read_text())["access_control"]
    assert acl["enabled"] is True and acl["default_permission"] == "deny"
    assert acl["policies"][0]["subjects"] == ["fastapi_admin", "router_b_peer"]
    for identity in identities:
        rule = next(
            item for item in acl["rules"] if item["id"] == f"rule_mower_{identity}"
        )
        assert rule["key_exprs"] == [f"mower/{identity}/**"]
        subject = next(
            item
            for item in acl["subjects"]
            if item["id"] == f"subject_mower_{identity}"
        )
        assert subject["cert_common_names"] == [f"mower:{identity}"]
    assert config_file.stat().st_mode & 0o777 == 0o600
    assert env_file.read_text() == (
        "JWT_SECRET=local-test\nZENOH_MTLS_CONFIG_FILE=.sim/zenoh-router-mtls.json5\n"
    )
    assert run.call_args.args[0][-4:] == [
        "-d",
        "--force-recreate",
        "--no-deps",
        "zenoh-mtls",
    ]
    provision_mower.configure_simulated_router_acl(identities)
    assert len(json.loads(config_file.read_text())["access_control"]["rules"]) == 3


def test_provisioner_uses_a_mower_scoped_certificate_subject():
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    assert provision_mower.mower_certificate_common_name(mower_id) == (
        f"mower:{mower_id}"
    )


def test_initial_credentials_use_p256_and_match_the_signed_csr(monkeypatch, tmp_path):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    issuer_key = ec.generate_private_key(ec.SECP256R1())

    def sign_csr(csr_pem):
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        assert csr.is_signature_valid
        assert isinstance(csr.public_key(), ec.EllipticCurvePublicKey)
        assert isinstance(csr.public_key().curve, ec.SECP256R1)
        assert (
            csr.signature_algorithm_oid == x509.SignatureAlgorithmOID.ECDSA_WITH_SHA256
        )
        assert csr.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
            0
        ].value == (f"mower:{mower_id}")
        assert (
            x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
            in csr.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        )
        certificate = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(csr.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC))
            .not_valid_after(datetime.now(UTC) + timedelta(days=90))
            .sign(issuer_key, hashes.SHA256())
        )
        return certificate.public_bytes(serialization.Encoding.PEM).decode(), "test CA"

    issuer = Mock()
    issuer.sign_csr.side_effect = sign_csr
    monkeypatch.setattr(provision_mower, "StepCaIssuer", Mock(return_value=issuer))
    provision_mower.issue_certificate(mower_id=mower_id, output_dir=tmp_path)

    active = tmp_path / "current"
    key = serialization.load_pem_private_key((active / "mower.key").read_bytes(), None)
    certificate = x509.load_pem_x509_certificate((active / "mower.crt").read_bytes())
    assert isinstance(key, ec.EllipticCurvePrivateKey)
    assert isinstance(key.curve, ec.SECP256R1)
    assert (
        key.public_key().public_numbers() == certificate.public_key().public_numbers()
    )
    assert (active / "mower.key").stat().st_mode & 0o777 == 0o600
    assert (active / "root_ca.pem").read_text() == "test CA"

    with pytest.raises(RuntimeError, match="credentials already exist"):
        provision_mower.issue_certificate(mower_id=mower_id, output_dir=tmp_path)
    assert (active / "mower.key").read_bytes() == key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def test_write_jetson_env_contains_only_runtime_configuration(tmp_path):
    env_file = tmp_path / ".env"
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")

    provision_mower.write_jetson_env(
        env_file,
        mower_id=mower_id,
        mower_cert_dir="/opt/emi-mower/certs",
        router_endpoint="tls/zenoh.example.internal:7448",
        verify_name_on_connect=True,
        mower_launch="real",
    )

    assert env_file.read_text() == (
        "# Generated by backend/src/scripts/provision_mower.py.\n"
        "# Credentials are mounted separately from MOWER_CERT_DIR.\n"
        f"MOWER_ID={mower_id}\n"
        "MOWER_CERT_DIR=/opt/emi-mower/certs\n"
        "MOWER_CREDENTIAL_DIR=/opt/emi-mower/certs\n"
        "ZENOH_ROUTER_ENDPOINT=tls/zenoh.example.internal:7448\n"
        "ZENOH_BOOTSTRAP_ENDPOINT=tls/host.docker.internal:7449\n"
        "ZENOH_VERIFY_NAME_ON_CONNECT=true\n"
        "ZENOH_BOOTSTRAP_VERIFY_NAME_ON_CONNECT=true\n"
        "MOWER_LAUNCH=real\n"
        "STM32_CAN_INTERFACE=can0\n"
        "RPLIDAR_DEVICE=/dev/rplidar\n"
    )
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_write_jetson_env_includes_simulated_tpm_state(tmp_path):
    env_file = tmp_path / "mower.env"
    tpm_state_dir = tmp_path / "swtpm-state"
    provision_mower.write_jetson_env(
        env_file,
        mower_id=uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2"),
        mower_cert_dir=str(tmp_path / "credentials"),
        router_endpoint="tls/host.docker.internal:7448",
        verify_name_on_connect=True,
        mower_launch="sim",
        tpm_state_dir=tpm_state_dir,
    )

    assert env_file.read_text().endswith(
        f"MOWER_LAUNCH=sim\nSTM32_CAN_INTERFACE=can0\nRPLIDAR_DEVICE=/dev/rplidar\n"
        f"TPM_TRANSPORT=swtpm\nSWTPM_STATE_DIR={tpm_state_dir}\n"
    )
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_parse_args_requires_output_only_for_physical_mower():
    simulated = provision_mower.parse_args(["--simulated", "--nickname", "Test"])
    assert simulated.simulated is True
    assert simulated.output_dir is None

    physical = provision_mower.parse_args(
        ["--nickname", "Test", "--output-dir", "/tmp/mower-credentials"]
    )
    assert physical.simulated is False
    assert physical.verify_name_on_connect is True
    assert physical.mower_launch == "real"

    with pytest.raises(SystemExit, match="2"):
        provision_mower.parse_args(["--nickname", "Test"])
    with pytest.raises(SystemExit, match="2"):
        provision_mower.parse_args(
            ["--simulated", "--nickname", "Test", "--output-dir", "/tmp/bundle"]
        )


def test_initialize_simulated_mower_orders_compose_and_provisioning(
    monkeypatch, tmp_path
):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    backend_root = tmp_path / "backend"
    backend_root.mkdir()
    (backend_root / ".env").write_text("JWT_SECRET=test\n")
    jetson_root = tmp_path / "nvidia_jetson"
    monkeypatch.setattr(provision_mower, "BACKEND_ROOT", backend_root)
    monkeypatch.setattr(provision_mower, "JETSON_ROOT", jetson_root)
    monkeypatch.setattr(
        provision_mower, "SIMULATED_MOWERS_ROOT", jetson_root / ".sim" / "mowers"
    )
    calls = []

    def run_compose(command, *, check, env):
        calls.append((command[-1], command, env))
        assert check is True

    async def provision_identity(args):
        calls.append(("provision", args, None))
        assert args.mower_id == mower_id
        assert args.mower_launch == "sim"
        assert args.verify_name_on_connect is True
        assert args.device_root_public_key == (
            jetson_root
            / ".sim"
            / "mowers"
            / str(mower_id)
            / "swtpm-state"
            / "device-root-public.pem"
        )

    monkeypatch.setattr(provision_mower.subprocess, "run", run_compose)
    monkeypatch.setattr(
        provision_mower, "provision_with_local_database", provision_identity
    )

    result = provision_mower.initialize_simulated_mower(
        argparse.Namespace(mower_id=mower_id, nickname="Test")
    )

    assert result == mower_id
    assert [call[0] for call in calls] == ["swtpm", "tpm-init", "provision", "ros"]
    env_file = jetson_root / ".sim" / "mowers" / str(mower_id) / "mower.env"
    assert env_file.stat().st_mode & 0o777 == 0o600
    assert f"SWTPM_STATE_DIR={env_file.parent / 'swtpm-state'}" in env_file.read_text()
    for _, command, env in (calls[0], calls[1], calls[3]):
        assert command[3] == f"mower-{str(mower_id)[:8]}"
        assert command[5] == str(env_file)
        assert env["MOWER_ENV_FILE"] == str(env_file)


def test_initialize_simulated_mower_preserves_existing_credentials(
    monkeypatch, tmp_path
):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    mower_root = tmp_path / "mowers" / str(mower_id)
    credential_dir = mower_root / "credentials" / "versions" / "initial"
    credential_dir.mkdir(parents=True)
    env_file = mower_root / "mower.env"
    env_file.write_text("existing configuration\n")
    monkeypatch.setattr(provision_mower, "SIMULATED_MOWERS_ROOT", tmp_path / "mowers")
    run = Mock()
    monkeypatch.setattr(provision_mower.subprocess, "run", run)

    with pytest.raises(RuntimeError, match="already provisioned"):
        provision_mower.initialize_simulated_mower(
            argparse.Namespace(mower_id=mower_id, nickname="Test")
        )

    assert env_file.read_text() == "existing configuration\n"
    run.assert_not_called()


@pytest.mark.asyncio
async def test_simulation_uses_local_compose_postgres_port(monkeypatch):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    engine = Mock()
    engine.dispose = AsyncMock()
    create_engine = Mock(return_value=engine)
    session_factory = object()
    monkeypatch.setattr(provision_mower, "create_async_engine", create_engine)
    monkeypatch.setattr(
        provision_mower,
        "async_sessionmaker",
        Mock(return_value=session_factory),
    )
    provision = AsyncMock(return_value=mower_id)
    monkeypatch.setattr(provision_mower, "provision_mower", provision)
    monkeypatch.setenv("LOCAL_POSTGRES_PORT", "15433")

    result = await provision_mower.provision_with_local_database(
        argparse.Namespace(mower_id=mower_id)
    )

    assert result == mower_id
    database_url = create_engine.call_args.args[0]
    assert database_url.host == "127.0.0.1"
    assert database_url.port == 15433
    provision.assert_awaited_once()
    assert provision.await_args.kwargs == {"session_factory": session_factory}
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_provision_mower_creates_record_acl_certificate_and_env(
    monkeypatch, tmp_path
):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    db = object()

    @asynccontextmanager
    async def fake_session():
        yield db

    mower = SimpleNamespace(id=mower_id)
    create = AsyncMock(return_value=mower)
    register = AsyncMock()
    client = Mock()
    client.configure_mower_device = AsyncMock()
    issue = Mock()
    write_env = Mock()
    close = AsyncMock()
    monkeypatch.setattr(provision_mower, "AsyncSessionLocal", fake_session)
    monkeypatch.setattr(provision_mower, "create_mower", create)
    monkeypatch.setattr(provision_mower, "register_mower_identity", register)
    monkeypatch.setattr(provision_mower, "ZenohAdminClient", Mock(return_value=client))
    monkeypatch.setattr(provision_mower, "issue_certificate", issue)
    monkeypatch.setattr(provision_mower, "write_jetson_env", write_env)
    monkeypatch.setattr(provision_mower, "close_http_client", close)
    public_key = tmp_path / "device-root-public.pem"
    public_key.write_text("public key")
    args = SimpleNamespace(
        mower_id=mower_id,
        nickname="Front yard",
        output_dir=tmp_path / "bundle",
        jetson_env_file=tmp_path / ".env",
        mower_cert_dir="/opt/emi-mower/certs",
        router_endpoint="tls/zenoh.example.internal:7448",
        verify_name_on_connect=True,
        mower_launch="sim",
        device_root_public_key=public_key,
    )

    result = await provision_mower.provision_mower(args)

    assert result == mower_id
    create.assert_awaited_once()
    assert create.await_args.kwargs == {
        "mower_id": mower_id,
        "nickname": "Front yard",
        "db": db,
    }
    register.assert_awaited_once_with(mower_id, "public key", db)
    client.configure_mower_device.assert_awaited_once_with(
        str(mower_id), f"mower:{mower_id}"
    )
    issue.assert_called_once_with(
        mower_id=mower_id,
        output_dir=args.output_dir,
    )
    write_env.assert_called_once_with(
        args.jetson_env_file,
        mower_id=mower_id,
        mower_cert_dir="/opt/emi-mower/certs",
        router_endpoint="tls/zenoh.example.internal:7448",
        verify_name_on_connect=True,
        mower_launch="sim",
    )
    close.assert_awaited_once()
