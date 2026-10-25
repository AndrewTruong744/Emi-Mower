"""Isolated router + real backend login handler + native Rust mobile transport.

Build zenohd, its REST plugin and the Rust test-driver example before this test.
No fleet endpoints, credentials or database records are used. Firebase/ownership
repositories are deterministic stubs; connection capture and authorization are real.
"""

import asyncio
import ipaddress
import json
import os
import secrets
import socket
import subprocess
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

import zenoh
from src.config.zenoh_client import ZenohAdminClient
from src.services import user
from src.zenoh.generated import UserLoginRequest
from src.zenoh.listeners.user_login import user_login
from src.zenoh.zenoh_handler import ZenohQueryHandler

ROOT = Path(__file__).resolve().parents[2]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def tls_credentials(directory):
    # The ephemeral CA signing key stays in host memory and never enters a file,
    # repository or image. Only public CA material and test leaf keys are written.
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name(
        [x509.NameAttribute(x509.NameOID.COMMON_NAME, "Ephemeral Runtime Test CA")]
    )
    root = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    root_pem = root.public_bytes(serialization.Encoding.PEM).decode()
    (directory / "root.crt").write_text(root_pem)
    for label, common_name in [
        ("router", "Runtime Test Router"),
        ("backend", "Emi Mower Backend"),
    ]:
        key = ec.generate_private_key(ec.SECP256R1())
        leaf = (
            x509.CertificateBuilder()
            .subject_name(
                x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, common_name)])
            )
            .issuer_name(ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    ]
                ),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )
        (directory / f"{label}.crt").write_bytes(
            leaf.public_bytes(serialization.Encoding.PEM)
        )
        private_key = directory / f"{label}.key"
        private_key.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        private_key.chmod(0o600)
    return root_pem


@pytest.fixture
async def native_driver(tmp_path):
    path = os.getenv("EMI_ZENOH_TEST_DRIVER")
    if not path or not Path(path).is_file():
        pytest.skip("set EMI_ZENOH_TEST_DRIVER to the built Rust test-driver example")
    with (tmp_path / "native-driver.log").open("w+") as log:
        process = await asyncio.create_subprocess_exec(
            path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=log,
        )
        lock = asyncio.Lock()

        async def call(request):
            async with lock:
                assert process.stdin is not None
                assert process.stdout is not None
                process.stdin.write((json.dumps(request) + "\n").encode())
                await process.stdin.drain()
                response = await asyncio.wait_for(process.stdout.readline(), timeout=15)
                if not response:
                    log.seek(0)
                    pytest.fail(
                        "Rust test driver exited without a reply: " + log.read()
                    )
                return json.loads(response)

        try:
            yield call
        finally:
            # EOF makes the runner close every native session before exiting.
            assert process.stdin is not None
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                pytest.fail("Rust test driver did not shut down after stdin closed")
            assert process.returncode == 0


@pytest.mark.parametrize("tls", [False, True])
async def test_backend_captures_and_authorizes_native_connection_without_restart(
    monkeypatch, tmp_path, native_driver, tls
):
    binary = os.getenv("ZENOH_FORK_ROUTER_BIN")
    plugin = os.getenv("ZENOH_FORK_REST_PLUGIN")
    if not binary or not plugin:
        pytest.skip("set ZENOH_FORK_ROUTER_BIN and ZENOH_FORK_REST_PLUGIN")
    native = native_driver
    router_port, admin_port = free_port(), free_port()
    backend_port = free_port() if tls else router_port
    root_pem = tls_credentials(tmp_path) if tls else None
    protocol = "tls" if tls else "tcp"
    token = secrets.token_urlsafe(48)
    token_file = tmp_path / "admin-token"
    token_file.write_text(token)
    token_file.chmod(0o600)
    config = json.loads((ROOT / "zenoh-router-app.test.json5").read_text())
    config.pop("connect")
    config.pop("transport")
    config["transport"] = {"unicast": {"max_links": 1}}
    config["id"] = "1111"
    config["listen"]["endpoints"] = [f"{protocol}/127.0.0.1:{router_port}"]
    if tls:
        config["listen"]["endpoints"] = [
            f"tls/127.0.0.1:{router_port}#enable_mtls=false",
            f"tls/127.0.0.1:{backend_port}",
        ]
        config["transport"]["link"] = {
            "tls": {
                "enable_mtls": True,
                "root_ca_certificate": str(tmp_path / "root.crt"),
                "listen_certificate": str(tmp_path / "router.crt"),
                "listen_private_key": str(tmp_path / "router.key"),
            }
        }
    config["plugins"]["rest"] = {
        "http_port": f"127.0.0.1:{admin_port}",
        "__path__": [plugin],
        "runtime_access_control": {
            "token_file": str(token_file),
            "capture_query_keys": ["user/login"],
        },
    }
    # Only the in-process backend transport is trusted on the local TCP test plane.
    config["access_control"]["subjects"][1] = (
        {"id": "mesh", "cert_common_names": ["Emi Mower Backend"]}
        if tls
        else {"id": "mesh", "zids": ["2222"]}
    )
    config_file = tmp_path / "router.json"
    config_file.write_text(json.dumps(config))
    log = (tmp_path / "router.log").open("w+")
    process = subprocess.Popen([binary, "-c", str(config_file)], stdout=log, stderr=log)
    session = handler = None
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            base = f"http://127.0.0.1:{admin_port}"
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    response = await http.get(base + "/@/runtime/connections")
                    if response.status_code == 401:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.05)
            else:
                pytest.fail("forked router management did not start")
            admin = ZenohAdminClient(base, base, http, admin_token=token)
            monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)
            monkeypatch.setattr(
                user,
                "verify_firebase_id_token",
                AsyncMock(return_value={"user_id": "alice"}),
            )
            monkeypatch.setattr(
                user,
                "user_authorization_snapshot",
                AsyncMock(
                    return_value=(
                        {"id": "alice", "email": "alice@example.test", "name": "Alice"},
                        ["A"],
                    )
                ),
            )

            @asynccontextmanager
            async def database():
                yield AsyncMock()

            monkeypatch.setattr("src.zenoh.zenoh_handler.AsyncSessionLocal", database)
            backend_config = zenoh.Config.from_json5(
                json.dumps(
                    {
                        "id": "2222",
                        "mode": "client",
                        "scouting": {"multicast": {"enabled": False}},
                        "connect": {
                            "endpoints": [f"{protocol}/127.0.0.1:{backend_port}"]
                        },
                    }
                )
            )
            if tls:
                backend_config.insert_json5(
                    "transport/link/tls",
                    json.dumps(
                        {
                            "enable_mtls": True,
                            "root_ca_certificate": str(tmp_path / "root.crt"),
                            "connect_certificate": str(tmp_path / "backend.crt"),
                            "connect_private_key": str(tmp_path / "backend.key"),
                        }
                    ),
                )
            session = await asyncio.to_thread(zenoh.open, backend_config)
            handler = ZenohQueryHandler(session, asyncio.get_running_loop())
            handler.declare(
                "user/login",
                user_login,
                request_model=UserLoginRequest,
                include_connection_context=True,
            )
            commands = asyncio.Queue()
            loop = asyncio.get_running_loop()
            command_sub = session.declare_subscriber(
                "mower/*/joystick",
                lambda sample: loop.call_soon_threadsafe(
                    commands.put_nowait, str(sample.key_expr)
                ),
            )
            opened = await native(
                {
                    "op": "connect",
                    "endpoint": f"{protocol}/127.0.0.1:{router_port}",
                    "root_ca_pem": root_pem,
                },
            )
            assert opened["ok"] is True
            connection = opened["result"]

            async def put(mower):
                result = await native(
                    {
                        "op": "put",
                        "session": connection,
                        "key": f"mower/{mower}/joystick",
                        "payload": "{}",
                    },
                )
                assert result["ok"] is True

            await put("A")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(commands.get(), 0.15)
            result = await native(
                {
                    "op": "query",
                    "session": connection,
                    "key": "user/login",
                    "payload": '{"id_token":"firebase-test"}',
                    "timeout_ms": 3000,
                },
            )
            assert result["ok"] is True, result
            assert json.loads(result["result"])["authorized"] is True
            captured = [
                c
                for c in await admin.captured_connections()
                if c["principal"] == "alice"
            ]
            assert len(captured) == 1
            original_id = captured[0]["id"]
            await put("A")
            assert await asyncio.wait_for(commands.get(), 3) == "mower/A/joystick"
            await put("B")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(commands.get(), 0.15)
            # The user's existing transport immediately loses A and gains B.
            await admin.configure_user_app("alice", ["B"])
            await put("A")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(commands.get(), 0.15)
            await put("B")
            assert await asyncio.wait_for(commands.get(), 3) == "mower/B/joystick"
            assert any(
                c["id"] == original_id for c in await admin.captured_connections()
            )
            # Router and unrelated backend transport remain up throughout changes.
            assert process.poll() is None
            assert (
                await http.put(base + "/mower/A/joystick", content="{}")
            ).status_code == 401

            # Ownership transfer preserves the initiating transport and its
            # unrelated mower C, while immediately removing mower B access.
            from src.services import mower as mower_service
            from src.zenoh.generated import TransferMowerRequest
            from src.zenoh.listeners import mower_ownership

            await admin.configure_user_app("alice", ["B", "C"])
            monkeypatch.setattr(mower_service, "ZenohAdminClient", lambda: admin)
            monkeypatch.setattr(
                mower_service,
                "stage_mower_ownership",
                AsyncMock(return_value={"alice": ["C"], "bob": ["B"]}),
            )
            monkeypatch.setattr(
                mower_service, "invalidate_mower_ownership", AsyncMock()
            )
            monkeypatch.setattr(
                mower_service,
                "user_authorization_snapshot",
                AsyncMock(return_value=({}, ["B"])),
            )
            monkeypatch.setattr(
                mower_ownership,
                "verify_firebase_id_token",
                AsyncMock(return_value={"user_id": "alice"}),
            )
            # Services validate UUIDs; the router treats UUIDs as opaque keys.
            # This fixture uses short route IDs to keep transport assertions clear.
            monkeypatch.setattr(mower_service, "_parse_mower_id", lambda value: value)
            handler.declare(
                "user/transfer_mower",
                mower_ownership.transfer_mower,
                request_model=TransferMowerRequest,
            )
            await asyncio.sleep(0.1)
            transferred = await native(
                {
                    "op": "query",
                    "session": connection,
                    "key": "user/transfer_mower",
                    "payload": json.dumps(
                        {"id_token": "test", "mower_id": "B", "new_owner_id": "bob"}
                    ),
                    "timeout_ms": 3000,
                },
            )
            assert transferred["ok"], transferred
            assert json.loads(transferred["result"])["new_owner_id"] == "bob"
            await put("B")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(commands.get(), 0.15)
            await put("C")
            assert await asyncio.wait_for(commands.get(), 3) == "mower/C/joystick"
            assert any(
                c["id"] == original_id for c in await admin.captured_connections()
            )

            # Retiring a source account allows its pending completion reply,
            # then blocks its existing cached command route on the same transport.
            async def finish_switch(payload, db):
                await admin.retire_user("alice")
                return {
                    "user_id": "replacement",
                    "new_email": "replacement@example.test",
                }

            handler.declare("user/update_email", finish_switch)
            await asyncio.sleep(0.1)
            switched = await native(
                {
                    "op": "query",
                    "session": connection,
                    "key": "user/update_email",
                    "payload": "{}",
                    "timeout_ms": 3000,
                },
            )
            assert switched["ok"], switched
            assert json.loads(switched["result"])["user_id"] == "replacement"
            await put("C")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(commands.get(), 0.15)
            await admin.revoke_user("alice")
            assert all(
                c["principal"] != "alice" for c in await admin.captured_connections()
            )
            assert process.poll() is None
            command_sub.undeclare()
    finally:
        if handler:
            handler.close()
        if session:
            await asyncio.to_thread(session.close)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()
