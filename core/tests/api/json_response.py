from typing import Protocol


class JsonResponse(Protocol):
    status_code: int

    def json(self) -> object: ...

    def __getitem__(self, header: str) -> str: ...
