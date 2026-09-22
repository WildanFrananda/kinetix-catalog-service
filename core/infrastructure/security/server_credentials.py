import os
from pathlib import Path
from typing import Optional

import grpc

from core.infrastructure.security.mtls import _read

_DEFAULT_PKI_DIR = "/pki"


def server_credentials(directory: Optional[str] = None) -> grpc.ServerCredentials:
    pki = Path(directory or os.environ.get("KINETIX_PKI_DIR", _DEFAULT_PKI_DIR))
    return grpc.ssl_server_credentials(
        private_key_certificate_chain_pairs=[
            (
                _read(pki, "tls.key", "PRIVATE KEY"),
                _read(pki, "tls.crt", "BEGIN CERTIFICATE"),
            )
        ],
        root_certificates=_read(pki, "ca.pem", "BEGIN CERTIFICATE"),
        require_client_auth=True,
    )
