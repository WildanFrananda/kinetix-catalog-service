import json
import logging
from typing import Dict, List, Optional

import pytest
from prometheus_client import REGISTRY
from rest_framework.test import APIClient

from core.infrastructure.observability import JsonLogFormatter
from core.infrastructure.repositories import DjangoProductRepository
from core.tests.api.api_fixtures import (
    ADMIN,
    KEYS,
    SELLER,
    TRACE,
    category_named,
    product_listed,
    signed_in_as,
)

ACTIONS = ("catalog.category_create", "catalog.category_update", "catalog.category_delete")
OUTCOMES = ("done", "refused", "failed")


def _count(action: str, outcome: str) -> float:
    value = REGISTRY.get_sample_value("kinetix_admin_actions_total", {"action": action, "outcome": outcome})

    return 0.0 if value is None else value


def _audit_lines(caplog: pytest.LogCaptureFixture) -> List[Dict[str, object]]:
    formatter = JsonLogFormatter()
    lines: List[Dict[str, object]] = []
    for record in caplog.records:
        if getattr(record, "event", None) != "admin_action":
            continue
        line = json.loads(formatter.format(record))
        assert isinstance(line, dict)
        lines.append(line)

    return lines


def _the_one_audit_line(caplog: pytest.LogCaptureFixture) -> Dict[str, object]:
    lines = _audit_lines(caplog)
    assert len(lines) == 1, lines

    return lines[0]


def _expect(
    line: Dict[str, object],
    action: str,
    target: Optional[str],
    outcome: str,
) -> None:
    assert line["level"] == "INFO"
    assert line["event"] == "admin_action"
    assert line["actor"] == ADMIN.principal_id
    assert line["action"] == action
    assert line["target"] == target
    assert line["outcome"] == outcome
    assert line["request_id"] == TRACE


@pytest.fixture
def audit_log(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO)

    return caplog


@pytest.mark.django_db
class TestEveryCategoryWriteByAnAdminIsAudited:
    def test_a_create_is_done_on_the_new_category(self, audit_log: pytest.LogCaptureFixture) -> None:
        before = _count("catalog.category_create", "done")

        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": "Bags", "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        assert response.status_code == 201
        _expect(_the_one_audit_line(audit_log), "catalog.category_create", str(response.json()["id"]), "done")
        assert _count("catalog.category_create", "done") == before + 1

    def test_an_update_is_done_on_the_category_in_the_path(self, audit_log: pytest.LogCaptureFixture) -> None:
        shelf = category_named()
        before = _count("catalog.category_update", "done")

        response = signed_in_as(ADMIN).put(
            f"/api/categories/{shelf.id}",
            {"name": "Sneakers", "slug": "sneakers"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        assert response.status_code == 200
        _expect(_the_one_audit_line(audit_log), "catalog.category_update", str(shelf.id), "done")
        assert _count("catalog.category_update", "done") == before + 1

    def test_a_delete_is_done(self, audit_log: pytest.LogCaptureFixture) -> None:
        shelf = category_named()
        before = _count("catalog.category_delete", "done")

        response = signed_in_as(ADMIN).delete(f"/api/categories/{shelf.id}/", HTTP_X_REQUEST_ID=TRACE)

        assert response.status_code == 204
        _expect(_the_one_audit_line(audit_log), "catalog.category_delete", str(shelf.id), "done")
        assert _count("catalog.category_delete", "done") == before + 1

    def test_a_create_refused_names_no_target(self, audit_log: pytest.LogCaptureFixture) -> None:
        before = _count("catalog.category_create", "refused")

        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": "Bags", "slug": "not a slug"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        assert response.status_code == 400
        _expect(_the_one_audit_line(audit_log), "catalog.category_create", None, "refused")
        assert _count("catalog.category_create", "refused") == before + 1

    def test_an_update_of_a_category_that_does_not_exist_is_refused(self, audit_log: pytest.LogCaptureFixture) -> None:
        before = _count("catalog.category_update", "refused")

        response = signed_in_as(ADMIN).put(
            "/api/categories/999999/",
            {"name": "Bags", "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        assert response.status_code == 404
        _expect(_the_one_audit_line(audit_log), "catalog.category_update", "999999", "refused")
        assert _count("catalog.category_update", "refused") == before + 1

    def test_a_delete_of_a_category_in_use_is_refused(self, audit_log: pytest.LogCaptureFixture) -> None:
        shelf = category_named()
        product_listed("SHOE-1", shelf)
        before = _count("catalog.category_delete", "refused")

        response = signed_in_as(ADMIN).delete(f"/api/categories/{shelf.id}/", HTTP_X_REQUEST_ID=TRACE)

        assert response.status_code == 409
        _expect(_the_one_audit_line(audit_log), "catalog.category_delete", str(shelf.id), "refused")
        assert _count("catalog.category_delete", "refused") == before + 1

    def test_a_write_that_failed_is_failed(
        self,
        audit_log: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shelf = category_named()

        def broken(*args: object, **kwargs: object) -> None:
            raise RuntimeError("the database fell over")

        monkeypatch.setattr(DjangoProductRepository, "delete_category", broken)
        before = _count("catalog.category_delete", "failed")

        response = signed_in_as(ADMIN).delete(f"/api/categories/{shelf.id}/", HTTP_X_REQUEST_ID=TRACE)

        assert response.status_code == 500
        _expect(_the_one_audit_line(audit_log), "catalog.category_delete", str(shelf.id), "failed")
        assert _count("catalog.category_delete", "failed") == before + 1

    def test_the_line_carries_no_token(self, audit_log: pytest.LogCaptureFixture) -> None:
        token = KEYS.sign(ADMIN)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        client.post("/api/categories/", {"name": "Bags", "slug": "bags"}, format="json", HTTP_X_REQUEST_ID=TRACE)

        assert token not in json.dumps(_the_one_audit_line(audit_log))


@pytest.mark.django_db
class TestWhatIsNotAnAdminAction:
    def test_a_seller_refused_at_the_role_check_is_not_recorded(self, audit_log: pytest.LogCaptureFixture) -> None:
        before = {(action, outcome): _count(action, outcome) for action in ACTIONS for outcome in OUTCOMES}

        response = signed_in_as(SELLER).post(
            "/api/categories/",
            {"name": "Bags", "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        assert response.status_code == 403
        assert _audit_lines(audit_log) == []
        assert {(action, outcome): _count(action, outcome) for action in ACTIONS for outcome in OUTCOMES} == before

    def test_a_write_without_a_token_is_not_recorded(self, audit_log: pytest.LogCaptureFixture) -> None:
        response = APIClient().delete("/api/categories/1/", HTTP_X_REQUEST_ID=TRACE)

        assert response.status_code == 401
        assert _audit_lines(audit_log) == []

    def test_an_admin_reading_categories_is_not_recorded(self, audit_log: pytest.LogCaptureFixture) -> None:
        shelf = category_named()
        client = signed_in_as(ADMIN)

        client.get("/api/categories/", HTTP_X_REQUEST_ID=TRACE)
        client.get(f"/api/categories/{shelf.id}/", HTTP_X_REQUEST_ID=TRACE)

        assert _audit_lines(audit_log) == []


@pytest.mark.django_db
class TestTheCounterIsPublishedBeforeAnyAction:
    def test_every_action_and_outcome_has_a_sample(self) -> None:
        APIClient().get("/api/categories/")

        missing = [
            (action, outcome)
            for action in ACTIONS
            for outcome in OUTCOMES
            if REGISTRY.get_sample_value("kinetix_admin_actions_total", {"action": action, "outcome": outcome}) is None
        ]

        assert missing == []
