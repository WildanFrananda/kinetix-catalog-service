from typing import Dict, List, Optional

from django.core.files.uploadhandler import FileUploadHandler
from django.http import HttpRequest


class RecordingUploadHandler(FileUploadHandler):
    def __init__(self, request: Optional[HttpRequest] = None) -> None:
        super().__init__(request)
        self._files_opened: List[str] = []
        self._bytes_received = 0

    def new_file(
        self,
        field_name: str,
        file_name: str,
        content_type: str,
        content_length: Optional[int],
        charset: Optional[str] = None,
        content_type_extra: Optional[Dict[str, bytes]] = None,
    ) -> None:
        super().new_file(field_name, file_name, content_type, content_length, charset, content_type_extra)
        self._files_opened.append(file_name)

    def receive_data_chunk(self, raw_data: bytes, start: int) -> Optional[bytes]:
        self._bytes_received += len(raw_data)

        return None

    def file_complete(self, file_size: int) -> None:
        return None

    @property
    def files_opened(self) -> List[str]:
        return list(self._files_opened)

    @property
    def bytes_received(self) -> int:
        return self._bytes_received
