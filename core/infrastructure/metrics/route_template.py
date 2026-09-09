import re
from typing import Optional

from django.urls import ResolverMatch

UNMATCHED_ROUTE = "unmatched"

_PARAMETER = re.compile(r"<(?:[^>:]+:)?([^>]+)>")


def route_template(resolver_match: Optional[ResolverMatch]) -> str:
    if resolver_match is None:
        return UNMATCHED_ROUTE

    return "/" + _PARAMETER.sub(r"{\1}", resolver_match.route)
