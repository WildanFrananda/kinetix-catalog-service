import logging

from core.infrastructure.observability.request_id_context import current_request_id


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id() or "-"
        return True
