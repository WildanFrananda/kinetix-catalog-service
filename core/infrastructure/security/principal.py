from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    principal_id: str
    user_id: int
    email: str
    role: str

    @property
    def is_authenticated(self) -> bool:
        return True

    def __str__(self) -> str:
        return self.principal_id
