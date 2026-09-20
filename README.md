# 🛒 Kinetix Catalog Service (`kinetix-catalog-service`)

Products, categories and search, plus a live stock reading taken from warehouse over gRPC. Built with
**Python**, **Django** + **DRF**, **PostgreSQL** and **strict typing (mypy)**, following hexagonal
architecture.

**Not** checkout, and **not** the public entrypoint. Orders belong to `kinetix-order-service`, the
buyer behind them to `kinetix-identity-service`, and the single public door is
`kinetix-api-gateway`.

---

## 🏛️ What this service does, and what it does not

**Does:** serve the product and category API; read live stock from warehouse's `BinStockService` over
gRPC so a listing does not advertise what is not on a shelf; verify identity's access token on every
authenticated request and resolve it to a `Principal`.

**Does not:** hold a buyer, an address, an order, a price decision, or an account. Until 2026-09-20 it
held an `orders` table with `buyer_name`, `buyer_phone`, `street_address`, `city` and `postal_code`,
and `django.contrib.auth` gave it `auth_user` — a third place in this estate where someone could have
a password. Both are gone. (docs/BOUNDARY-DEBT.md C1, C3, C5, C10)

**Kept from the earlier audit work:**

1. **Fail-fast secret validation**: `config/settings.py` demands an explicit `SECRET_KEY` of at least
   32 characters outside DEBUG, failing at boot rather than serving with a default.
2. **Parallel stock reads with channel reuse**: `ProductService.list_products` queries stock
   concurrently, and `BinStockGrpcClient` reuses its gRPC channel across requests.

---

## 📂 Complete File Directory Structure (Hexagonal Architecture)

```
kinetix-catalog-service/
├── core/
│   ├── api/
│   │   ├── di.py                       # Dependency Injection Container
│   │   ├── serializers/                # REST API Serializers
│   │   └── views/                      # Clean REST Views
│   │       ├── product_view.py
│   │       ├── category_view.py
│   │       ├── health_view.py
│   │       ├── readiness_view.py
│   │       └── metrics_view.py
│   ├── application/
│   │   ├── dto/                        # Data Transfer Objects
│   │   └── services/                   # Use Case Services (Product & Category)
│   ├── domain/
│   │   ├── entities/                   # Pure Domain Entities
│   │   └── repositories/               # Repository Port Interfaces
│   └── infrastructure/
│       ├── models/                     # Django ORM Models: CategoryModel, ProductModel
│       ├── repositories/               # Django Repository Adapters
│       ├── security/                   # Identity token verification, Principal, mTLS
│       └── grpc/                       # gRPC Client Adapters (Channel Reuse)
│           ├── bin_stock_client.py     # warehouse stock
│           ├── pricing_client.py       # pricing
│           └── identity_client.py
├── manage.py
├── pytest.ini
└── requirements.txt
```

---

## ⚡ Local Setup & Verification Guide

```bash
# 1. Run MyPy Strict Static Type Checking
venv/bin/mypy core

# 2. Run PyTest Test Suite (12/12 Passed)
venv/bin/pytest -v
```
