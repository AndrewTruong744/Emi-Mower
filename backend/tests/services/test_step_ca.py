from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding

from src.services import step_ca


def test_step_ca_issuer_signs_a_csr_without_a_ca_key(monkeypatch, tmp_path):
    root = tmp_path / "root_ca.pem"
    root.write_text("public root")
    request_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "mower:test")])
        )
        .sign(request_key, hashes.SHA256())
        .public_bytes(Encoding.PEM)
        .decode()
    )
    certificate_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "mower:test")])
        )
        .issuer_name(
            x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "test-ca")])
        )
        .public_key(certificate_key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .sign(certificate_key, hashes.SHA256())
        .public_bytes(Encoding.PEM)
        .decode()
    )

    def write_certificate(command, **_):
        Path(command[-1]).write_text(certificate)

    run = Mock(side_effect=write_certificate)
    monkeypatch.setattr(step_ca.subprocess, "run", run)
    monkeypatch.setattr(step_ca.settings, "ZENOH_CA_CERT", str(root))
    monkeypatch.setattr(step_ca.settings, "STEP_CA_URL", "https://step-ca:9000")
    monkeypatch.setattr(
        step_ca.settings, "STEP_CA_PROVISIONER_PASSWORD_FILE", "/issuer/password"
    )

    issued, chain = step_ca.StepCaIssuer().sign_csr(csr)

    assert issued == certificate
    assert chain == "public root"
    command = run.call_args.args[0]
    assert command[:3] == ["step", "ca", "sign"]
    assert "/issuer/password" in command
    assert str(root) in command
    assert not any("ca.key" in part for part in command)

    compose_run = Mock(
        side_effect=[
            CompletedProcess([], 0, stdout=certificate),
            CompletedProcess([], 0, stdout="public root"),
        ]
    )
    monkeypatch.setattr(step_ca.subprocess, "run", compose_run)
    compose_file = tmp_path / "local-docker-compose.yml"
    issued, chain = step_ca.ComposeStepCaIssuer(compose_file).sign_csr(csr)

    assert issued == certificate
    assert chain == "public root"
    sign_call, root_call = compose_run.call_args_list
    assert sign_call.args[0][:8] == [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "exec",
        "-T",
        "step-ca",
        "sh",
    ]
    assert sign_call.kwargs["input"] == csr
    assert sign_call.kwargs["capture_output"] is True
    assert "/credentials/issuer/provisioner-password" in sign_call.args[0][-1]
    assert root_call.args[0][-2:] == ["cat", "/home/step/certs/root_ca.crt"]
