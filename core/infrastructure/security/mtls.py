import os
from pathlib import Path
from typing import Optional

import grpc

from core.infrastructure.security.service_identity_error import ServiceIdentityError

_DEFAULT_PKI_DIR = "/pki"


def _read(directory: Path, name: str, marker: str) -> bytes:
    path = directory / name
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ServiceIdentityError(
            f"cannot read {path}: {exc}. The service PKI is mounted at {directory}; "
            "issue it with kinetix-infrastructure/bin/kinetix-pki issue."
        ) from exc

    if marker.encode() not in data:
        raise ServiceIdentityError(f"{path} is not a PEM containing {marker}")
    return data


def channel_credentials(directory: Optional[str] = None) -> grpc.ChannelCredentials:
    pki = Path(directory or os.environ.get("KINETIX_PKI_DIR", _DEFAULT_PKI_DIR))
    return grpc.ssl_channel_credentials(
        root_certificates=_read(pki, "ca.pem", "BEGIN CERTIFICATE"),
        private_key=_read(pki, "tls.key", "PRIVATE KEY"),
        certificate_chain=_read(pki, "tls.crt", "BEGIN CERTIFICATE"),
    )
