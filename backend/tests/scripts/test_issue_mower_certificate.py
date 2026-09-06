import subprocess
import uuid
from pathlib import Path

from src.scripts import provision_mower


def _run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def test_issuer_creates_a_90_day_certificate_for_each_output_directory(tmp_path):
    ca_key = tmp_path / "ca.key"
    ca_cert = tmp_path / "ca.crt"
    _run(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(ca_key),
        "-out",
        str(ca_cert),
        "-days",
        "2",
        "-subj",
        "/CN=test-ca",
        cwd=tmp_path,
    )
    mower_id = str(uuid.uuid4())
    output = tmp_path / mower_id
    _run(
        "bash",
        str(provision_mower.CERTIFICATE_SCRIPT),
        "--mower-id",
        mower_id,
        "--output-dir",
        str(output),
        "--ca-cert",
        str(ca_cert),
        "--ca-key",
        str(ca_key),
        cwd=tmp_path,
    )

    subject = _run(
        "openssl",
        "x509",
        "-in",
        str(output / "mower.crt"),
        "-noout",
        "-subject",
        cwd=tmp_path,
    )
    assert f"CN=mower:{mower_id}" in subject.stdout
    assert (output / "mower.key").stat().st_mode & 0o777 == 0o600
    assert _run(
        "openssl",
        "x509",
        "-checkend",
        str(89 * 24 * 60 * 60),
        "-noout",
        "-in",
        str(output / "mower.crt"),
        cwd=tmp_path,
    ).returncode == 0

    too_long = subprocess.run(
        [
            "openssl",
            "x509",
            "-checkend",
            str(91 * 24 * 60 * 60),
            "-noout",
            "-in",
            str(output / "mower.crt"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert too_long.returncode == 1
