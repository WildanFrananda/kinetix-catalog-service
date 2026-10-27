from typing import Dict

import pytest
from django.core.exceptions import TooManyFilesSent
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory, override_settings
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from core.tests.unit.recording_upload_handler import RecordingUploadHandler

RECORDING_HANDLER = "core.tests.unit.recording_upload_handler.RecordingUploadHandler"
A_MEBIBYTE = 1024 * 1024


def _posted(form: Dict[str, object]) -> WSGIRequest:
    return RequestFactory().post("/api/products/create/", form)


class TestAMultipartForm:
    def test_its_text_fields_are_read(self) -> None:
        form = Request(_posted({"sku": "SHOE-1", "weight_grams": "300"}), parsers=[MultiPartParser()])

        data = form.data

        assert isinstance(data, dict)
        assert data.get("sku") == "SHOE-1"
        assert data.get("weight_grams") == "300"

    def test_a_file_part_is_refused_before_an_upload_handler_opens_it_or_the_body_is_read(self) -> None:
        posted = _posted({"sku": "SHOE-1", "photo": SimpleUploadedFile("photo.jpg", b"x" * A_MEBIBYTE)})
        form = Request(posted, parsers=[MultiPartParser()])

        with override_settings(FILE_UPLOAD_HANDLERS=[RECORDING_HANDLER]):
            with pytest.raises(TooManyFilesSent):
                form.data

        handler = posted.upload_handlers[0]
        assert isinstance(handler, RecordingUploadHandler)
        assert handler.files_opened == []
        assert handler.bytes_received == 0
        assert len(posted.environ["wsgi.input"]) > A_MEBIBYTE // 2
