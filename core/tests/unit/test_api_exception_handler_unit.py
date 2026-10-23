from typing import Dict

import psycopg
import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from django.db import IntegrityError, InterfaceError, OperationalError
from django.http import Http404
from psycopg import errors as pg_errors
from rest_framework.exceptions import ValidationError

from core.api.exception_handler import api_exception_handler
from core.domain.errors import CategoryInUseError, InvalidInputError

ERROR_SHAPE_KEYS = frozenset({"error", "message", "traceId", "field", "product_count"})


def _caused_by(wrapper: Exception, cause: Exception) -> Exception:
    wrapper.__cause__ = cause

    return wrapper


def _answer(exc: Exception) -> Dict[str, object]:
    response = api_exception_handler(exc, {})
    body = response.data
    assert isinstance(body, dict)
    assert set(body) <= ERROR_SHAPE_KEYS, f"keys outside the error shape: {set(body) - ERROR_SHAPE_KEYS}"
    body["status"] = response.status_code

    return body


class TestEveryRefusalKeepsTheErrorShape:
    @pytest.mark.parametrize(
        ("exc", "status", "code"),
        [
            (Http404(), 404, "NOT_FOUND"),
            (DjangoPermissionDenied(), 403, "FORBIDDEN"),
            (ValidationError({"name": ["is required"]}), 400, "BAD_REQUEST"),
            (ValidationError(["is required", "is too long"]), 400, "BAD_REQUEST"),
            (InvalidInputError("price", "must be a number"), 400, "INVALID_INPUT"),
            (CategoryInUseError(3, 2), 409, "CATEGORY_IN_USE"),
            (RuntimeError("boom"), 500, "INTERNAL_ERROR"),
        ],
    )
    def test_no_answer_carries_a_key_outside_the_shape(self, exc: Exception, status: int, code: str) -> None:
        body = _answer(exc)

        assert body["status"] == status
        assert body["error"] == code
        assert isinstance(body["message"], str) and body["message"]


class TestBodiesAndQueriesTheServiceWillNotRead:
    def test_a_body_over_the_memory_limit_is_a_413(self) -> None:
        body = _answer(RequestDataTooBig("Request body exceeded settings.DATA_UPLOAD_MAX_MEMORY_SIZE."))

        assert body["status"] == 413
        assert body["error"] == "BODY_TOO_LARGE"
        assert "settings" not in str(body["message"])

    def test_too_many_fields_is_a_400(self) -> None:
        body = _answer(TooManyFieldsSent("The number of GET/POST parameters exceeded settings.DATA_UPLOAD_MAX_NUMBER_FIELDS."))

        assert body["status"] == 400
        assert body["error"] == "TOO_MANY_FIELDS"
        assert "settings" not in str(body["message"])


class TestADatabaseThatCannotBeReached:
    @pytest.mark.parametrize(
        "exc",
        [
            _caused_by(
                OperationalError("connection failed"),
                psycopg.OperationalError("connection failed: connection to server at \"10.0.0.7\", port 5432 failed"),
            ),
            _caused_by(OperationalError("terminating connection"), pg_errors.AdminShutdown("terminating connection")),
            _caused_by(OperationalError("starting up"), pg_errors.CannotConnectNow("the database system is starting up")),
            _caused_by(OperationalError("too many"), pg_errors.TooManyConnections("too many clients already")),
            _caused_by(InterfaceError("connection already closed"), psycopg.InterfaceError("the connection is closed")),
        ],
        ids=["refused", "admin-shutdown", "starting-up", "too-many-connections", "closed"],
    )
    def test_is_a_503_that_names_no_host(self, exc: Exception) -> None:
        response = api_exception_handler(exc, {})
        body = response.data

        assert response.status_code == 503
        assert isinstance(body, dict)
        assert body["error"] == "DATABASE_UNAVAILABLE"
        assert "10.0.0.7" not in str(body["message"])
        assert response["Retry-After"]

    @pytest.mark.parametrize(
        "exc",
        [
            _caused_by(OperationalError("canceling statement"), pg_errors.QueryCanceled("canceling statement due to statement timeout")),
            _caused_by(OperationalError("deadlock"), pg_errors.DeadlockDetected("deadlock detected")),
            _caused_by(IntegrityError("duplicate key"), pg_errors.UniqueViolation("duplicate key")),
        ],
        ids=["statement-timeout", "deadlock", "unique-violation"],
    )
    def test_a_database_that_answered_with_an_error_is_still_a_500(self, exc: Exception) -> None:
        body = _answer(exc)

        assert body["status"] == 500
        assert body["error"] == "INTERNAL_ERROR"
