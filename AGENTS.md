# AGENTS.md

This file guides AI coding agents (Claude Code, Copilot, Cursor, etc.) working in this Django repository. Follow these conventions strictly — they are not optional style suggestions.

## Architecture

This project uses **Hexagonal Architecture (Ports & Adapters)** with a strict
**Controller → Service → Repository → Model** layering, adapted from an
Angular/Next.js/Rails-Sorbet background. The core rule: **business logic never
touches Django's ORM directly, and domain code never imports from Django.**

```
<app_name>/
├── domain/
│   ├── entities.py        # Pure Python dataclasses. Zero Django imports.
│   └── repositories.py    # Abstract interfaces (ports) — ABC + type hints
├── application/
│   ├── services.py        # Business logic / use cases. Only layer with logic.
│   └── dto.py              # Input/output data classes for services
├── infrastructure/
│   ├── models.py           # Django ORM models (adapters)
│   └── repositories.py     # Concrete repo implementations of domain interfaces
├── api/
│   ├── views.py             # Thin. Orchestration only — no business logic.
│   ├── serializers.py
│   └── di.py                 # Manual DI wiring (constructor injection)
└── urls.py
```

## Layer Responsibilities

| Layer | Allowed to import | Forbidden |
|---|---|---|
| `domain/` | stdlib only (`dataclasses`, `decimal`, `datetime`, `abc`) | Django, ORM, other layers |
| `application/` | `domain/` | `infrastructure/`, Django ORM, `api/` |
| `infrastructure/` | `domain/`, Django | `application/`, `api/` |
| `api/` | `application/`, `infrastructure/` (only in `di.py`), DRF | Direct ORM calls, business logic |

Agents must **not** collapse these layers "for convenience" — e.g. do not put
`.objects.filter(...)` calls inside a service, and do not put validation or
business rules inside a view or serializer.

## Conventions

- **Entities are immutable dataclasses** (`@dataclass(frozen=True)`), never
  Django model instances leaking into `application/` or `domain/`.
- **Repositories are `abc.ABC` interfaces** in `domain/repositories.py`, with
  concrete Django implementations in `infrastructure/repositories.py`. Method
  signatures must be fully type-hinted (params and return types).
- **Services receive repositories via constructor injection**, never
  instantiate them internally:
  ```python
  class OrderService:
      def __init__(self, repo: OrderRepository):
          self._repo = repo
  ```
- **DI wiring lives only in `api/di.py`**, using simple factory functions
  (e.g. `get_order_service() -> OrderService`). Don't introduce a DI
  framework/container unless explicitly asked.
- **Views are thin.** A view method should be ~3-6 lines: get the service from
  `di.py`, call one service method, return the response. No conditionals with
  business meaning in views.
- **Strict typing everywhere.** All function signatures need full type hints.
  Treat this repo as if it were under Sorbet-level strictness — no bare
  `Any`, no untyped `**kwargs` passthrough without a reason.
- **Composition over inheritance.** Don't build deep model/service class
  hierarchies; prefer small composable services and repositories.
- **Errors as exceptions from the domain/application layer**, not as
  `None`/silent failures. Let `api/views.py` translate exceptions to HTTP
  responses (e.g. via DRF exception handler), not the service.

## Testing Expectations

- `application/services.py` must be unit-testable with a fake/in-memory
  repository (implementing the same `domain/repositories.py` interface) —
  no DB or Django test client required for service-level tests.
- `infrastructure/repositories.py` gets integration tests against the real
  Django ORM (`pytest-django` / `TestCase`).
- `api/views.py` gets thin integration tests (status codes, request/response
  shape) — not business logic assertions; those belong at the service level.

## When Adding a New Feature/Module

1. Define the entity in `domain/entities.py`.
2. Define the repository interface in `domain/repositories.py`.
3. Implement the Django model + concrete repository in `infrastructure/`.
4. Implement the use case in `application/services.py`.
5. Wire it in `api/di.py`.
6. Add the thin view + serializer + URL route.

Do not skip straight to step 6. If an agent is asked to "add an endpoint for
X," it should still produce entity → repository → service → view, in that
order, even for simple CRUD.

## Anti-Patterns to Reject

- ❌ `OrderModel.objects.filter(...)` inside `application/services.py`
- ❌ Business rules (validation, calculations, state transitions) inside
  `api/views.py` or `api/serializers.py`
- ❌ Services importing Django models directly instead of depending on the
  repository interface
- ❌ Fat models with business logic methods (`OrderModel.calculate_total()`)
  — that logic belongs in `application/services.py`
- ❌ Passing Django `QuerySet` objects out of the repository layer — always
  convert to domain entities (typically `list[Entity]`) before returning