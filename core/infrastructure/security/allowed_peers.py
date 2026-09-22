import os
from typing import FrozenSet, Optional

from core.infrastructure.security.service_identity_error import ServiceIdentityError

_VARIABLE = "KINETIX_GRPC_ALLOWED_PEERS"


def allowed_peers(raw: Optional[str] = None) -> FrozenSet[str]:
    value = raw if raw is not None else os.environ.get(_VARIABLE, "")
    names = frozenset(part.strip() for part in value.split(",") if part.strip())

    if not names:
        raise ServiceIdentityError(
            f"{_VARIABLE} must name at least one caller. An empty list is read as "
            "'no caller is expected', and an unset one would be read as 'allow all'."
        )

    return names
