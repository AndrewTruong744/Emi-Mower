"""Smallstep CA client used after backend authorization has succeeded."""

import subprocess
import tempfile
from pathlib import Path

from cryptography import x509

from src.config.settings import settings


class StepCaIssuer:
    """Sign CSRs without exposing a CA private key to backend code."""

    def sign_csr(self, csr_pem: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory(prefix="emi-step-ca-") as directory:
            request = Path(directory) / "request.csr"
            certificate = Path(directory) / "certificate.crt"
            request.write_text(csr_pem)
            subprocess.run(
                [
                    "step",
                    "ca",
                    "sign",
                    "--provisioner-password-file",
                    settings.STEP_CA_PROVISIONER_PASSWORD_FILE,
                    "--ca-url",
                    settings.STEP_CA_URL,
                    "--root",
                    settings.ZENOH_CA_CERT,
                    "--not-after",
                    "2160h",
                    str(request),
                    str(certificate),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            certificate_pem = certificate.read_text()
            # Fail here rather than returning unparseable material to a mower.
            x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
            return certificate_pem, Path(settings.ZENOH_CA_CERT).read_text()
