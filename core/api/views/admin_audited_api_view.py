from typing import Mapping, Optional, Tuple

from rest_framework.request import Request
from rest_framework.response import Response

from core.api.views.public_read_api_view import PublicReadApiView
from core.infrastructure.observability.admin_action_audit import AdminActionOutcome, record_admin_action
from core.infrastructure.security import Principal


class AdminAuditedApiView(PublicReadApiView):
    _admin_action: Optional[Tuple[str, Principal]] = None

    def begin_admin_action(self, action: str, admin: Principal) -> None:
        self._admin_action = (action, admin)

    def finalize_response(self, request: Request, response: Response, *args: object, **kwargs: object) -> Response:
        finalized = super().finalize_response(request, response, *args, **kwargs)
        if self._admin_action is None:
            return finalized

        action, admin = self._admin_action
        record_admin_action(
            actor=admin.principal_id,
            action=action,
            target=_target_of(finalized, kwargs),
            outcome=_outcome_of(finalized.status_code),
        )

        return finalized


def _target_of(response: Response, path: Mapping[str, object]) -> Optional[str]:
    named = next(iter(path.values()), None)
    if named is not None:
        return str(named)

    data = response.data
    created = data.get("id") if isinstance(data, dict) else None

    return None if created is None else str(created)


def _outcome_of(status_code: int) -> AdminActionOutcome:
    if status_code < 400:
        return "done"

    if status_code < 500:
        return "refused"

    return "failed"
