import logging
from typing import Literal, Optional, Sequence, Tuple

from core.infrastructure.metrics import ADMIN_ACTIONS_TOTAL
from core.infrastructure.observability.json_log_formatter import NO_REQUEST_ID
from core.infrastructure.observability.request_id_context import current_request_id

ADMIN_ACTION_EVENT = "admin_action"

AdminActionOutcome = Literal["done", "refused", "failed"]

ADMIN_ACTION_OUTCOMES: Tuple[AdminActionOutcome, ...] = ("done", "refused", "failed")

logger = logging.getLogger(__name__)


def declare_admin_actions(actions: Sequence[str]) -> None:
    for action in actions:
        for outcome in ADMIN_ACTION_OUTCOMES:
            ADMIN_ACTIONS_TOTAL.labels(action=action, outcome=outcome)


def record_admin_action(actor: str, action: str, target: Optional[str], outcome: AdminActionOutcome) -> None:
    logger.info(
        ADMIN_ACTION_EVENT,
        extra={
            "event": ADMIN_ACTION_EVENT,
            "actor": actor,
            "action": action,
            "target": target,
            "outcome": outcome,
            "request_id": current_request_id() or NO_REQUEST_ID,
        },
    )

    try:
        ADMIN_ACTIONS_TOTAL.labels(action=action, outcome=outcome).inc()
    except Exception as failure:
        logger.error("could not count admin action %s (%s): %s", action, outcome, failure)
