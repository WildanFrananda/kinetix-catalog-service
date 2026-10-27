from typing import Dict, Iterator, List

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.test import override_settings
from rest_framework.test import APIClient

from core.domain.entities import Category
from core.infrastructure.repositories import DjangoProductRepository
from core.tests.api.api_fixtures import (
    ADMIN,
    SELLER,
    TRACE,
    category_named,
    product_listed,
    refusal,
    signed_in_as,
)
from core.tests.unit.recording_upload_handler import RecordingUploadHandler

RECORDING_HANDLER = "core.tests.unit.recording_upload_handler.RecordingUploadHandler"
A_MEBIBYTE = 1024 * 1024


def _too_many_fields() -> Dict[str, str]:
    return {f"field{n}": "x" for n in range(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS + 1)}


def _larger_than_the_limit() -> str:
    return "x" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)


def _product_form(shelf: Category) -> Dict[str, object]:
    return {"sku": "SHOE-FORM", "title": "Shoe", "price": "1000.00", "category_id": shelf.id, "weight_grams": 300}


def _photo(name: str, size: int) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"x" * size, content_type="image/jpeg")


def _files_opened(request: WSGIRequest) -> List[str]:
    handler = request.upload_handlers[0]
    assert isinstance(handler, RecordingUploadHandler)

    return handler.files_opened


def _share_of_the_body_left_unread(request: WSGIRequest) -> float:
    return len(request.environ["wsgi.input"]) / int(request.META["CONTENT_LENGTH"])


@pytest.mark.django_db
class TestBodiesTooLargeToRead:
    def test_a_json_product_larger_than_the_limit_is_a_413_and_not_created(self) -> None:
        shelf = category_named()

        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {
                "sku": "SHOE-HUGE",
                "title": "Shoe",
                "description": _larger_than_the_limit(),
                "price": "1000.00",
                "category_id": shelf.id,
                "weight_grams": 300,
            },
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")
        assert DjangoProductRepository().find_by_sku("SHOE-HUGE") is None

    def test_a_json_category_larger_than_the_limit_is_a_413(self) -> None:
        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": _larger_than_the_limit(), "slug": "bags"},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")

    def test_a_multipart_body_larger_than_the_limit_is_a_413_not_a_500(self) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {"sku": "SHOE-FORM", "description": _larger_than_the_limit()},
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")

    def test_a_product_update_larger_than_the_limit_is_a_413(self) -> None:
        product = product_listed("SHOE-1", category_named())

        response = signed_in_as(SELLER).put(
            f"/api/products/manage/{product.id}/",
            {"description": _larger_than_the_limit()},
            format="json",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 413, "BODY_TOO_LARGE")
        assert DjangoProductRepository().find_by_id(product.id or 0) == product


@pytest.mark.django_db
class TestRequestsWithTooManyFields:
    def test_a_form_body_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            _too_many_fields(),
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "TOO_MANY_FIELDS")

    def test_an_urlencoded_body_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        body = "&".join(f"{name}={value}" for name, value in _too_many_fields().items())

        response = signed_in_as(ADMIN).generic(
            "POST",
            "/api/categories/",
            body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "TOO_MANY_FIELDS")

    def test_a_listing_query_with_too_many_fields_is_a_400_not_a_500(self) -> None:
        response = APIClient().get("/api/products/", _too_many_fields(), HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 400, "TOO_MANY_FIELDS")


@pytest.mark.django_db
class TestFilePartsAreRefusedBeforeTheyAreRead:
    @pytest.fixture(autouse=True)
    def uploads_are_recorded(self) -> Iterator[None]:
        with override_settings(FILE_UPLOAD_HANDLERS=[RECORDING_HANDLER]):
            yield

    def test_a_product_form_with_one_file_part_is_a_400_and_not_created(self) -> None:
        response = signed_in_as(SELLER).post(
            "/api/products/create/",
            {**_product_form(category_named()), "photo": _photo("photo.jpg", A_MEBIBYTE)},
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "FILES_NOT_ACCEPTED")
        assert DjangoProductRepository().find_by_sku("SHOE-FORM") is None
        assert _files_opened(response.wsgi_request) == []
        assert _share_of_the_body_left_unread(response.wsgi_request) > 0.5

    def test_a_product_update_with_a_file_part_is_a_400_and_changes_nothing(self) -> None:
        product = product_listed("SHOE-1", category_named())

        response = signed_in_as(SELLER).put(
            f"/api/products/manage/{product.id}/",
            {"title": "Shoe, renamed", "photo": _photo("photo.jpg", 1)},
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "FILES_NOT_ACCEPTED")
        assert DjangoProductRepository().find_by_id(product.id or 0) == product
        assert _files_opened(response.wsgi_request) == []

    def test_a_form_with_101_file_parts_is_a_400_not_a_500(self) -> None:
        response = signed_in_as(ADMIN).post(
            "/api/categories/",
            {"name": "Bags", "slug": "bags", "photos": [_photo(f"photo{n}.jpg", 8 * 1024) for n in range(101)]},
            format="multipart",
            HTTP_X_REQUEST_ID=TRACE,
        )

        refusal(response, 400, "FILES_NOT_ACCEPTED")
        assert APIClient().get("/api/categories/").json() == []
        assert _files_opened(response.wsgi_request) == []
        assert _share_of_the_body_left_unread(response.wsgi_request) > 0.5


@pytest.mark.django_db
class TestTheTextFieldsOfAMultipartForm:
    def test_create_a_product(self) -> None:
        response = signed_in_as(SELLER).post("/api/products/create/", _product_form(category_named()), format="multipart")

        assert response.status_code == 201
        assert response.json()["sku"] == "SHOE-FORM"
        assert response.json()["weight_grams"] == 300

    def test_update_a_product(self) -> None:
        product = product_listed("SHOE-1", category_named())

        response = signed_in_as(SELLER).put(f"/api/products/manage/{product.id}/", {"title": "Shoe, renamed"}, format="multipart")

        assert response.status_code == 200
        assert response.json()["title"] == "Shoe, renamed"

    def test_create_a_category(self) -> None:
        response = signed_in_as(ADMIN).post("/api/categories/", {"name": "Bags", "slug": "bags"}, format="multipart")

        assert response.status_code == 201
        assert response.json()["slug"] == "bags"


@pytest.mark.django_db
class TestTheFormatParameterIsNotAnOverride:
    @pytest.mark.parametrize("value", ["xml", "api", "yaml", "json"])
    def test_a_listing_answers_the_same_whatever_format_is_named(self, value: str) -> None:
        product_listed("SHOE-1", category_named())
        client = APIClient()

        plain = client.get("/api/products/")
        named = client.get("/api/products/", {"format": value})

        assert named.status_code == 200
        assert named.json() == plain.json()

    def test_a_product_page_answers_whatever_format_is_named(self) -> None:
        product_listed("SHOE-1", category_named())

        response = APIClient().get("/api/products/SHOE-1/", {"format": "xml"})

        assert response.status_code == 200
        assert response.json()["sku"] == "SHOE-1"

    def test_a_refusal_with_a_format_named_keeps_the_error_shape(self) -> None:
        response = APIClient().get("/api/categories/999999/", {"format": "xml"}, HTTP_X_REQUEST_ID=TRACE)

        refusal(response, 404, "CATEGORY_NOT_FOUND")
