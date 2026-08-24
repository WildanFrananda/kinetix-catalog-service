# 🛒 Kinetix Catalog Service (`kinetix-catalog-service`)

High-performance product catalog, search engine, inventory stock query, cart reservation, and checkout entrypoint microservice built with **Python 3.12+**, **Django 6.0+**, **gRPC Client Communication**, **PostgreSQL 16**, and **Strict Type Checking (mypy)** following **Hexagonal Architecture**.

---

## 🏛️ Domain Architecture & Resolved Audit Upgrades

1. **Idempotency Key & Duplicate Order Protection**:
   - `OrderService.checkout` locks and evaluates `idempotency_key` (extracted from `Idempotency-Key` or `X-Idempotency-Key` headers) in `OrderModel`. Retried requests return existing order details immediately without generating duplicate orders or gRPC calls.
2. **Atomic Stock Reservation Guard**:
   - Executes stock reservation checks (`bin_stock_port.reserve_stock()`) prior to saving orders in DB. Rejects checkout attempts with `ValueError` if available quantity is insufficient, eliminating overselling / negative inventory.
3. **Saga Failure Compensation**:
   - Implemented Saga compensation logic in `OrderService.checkout`. If gRPC `submit_fulfillment_order()` to `kinetix-warehouse-service` fails or returns active rejection, order status is automatically updated to `"failed"` in DB.
4. **Fail-Fast Production Secret Key Validation**:
   - `config/settings.py` enforces explicit `SECRET_KEY` presence in non-DEBUG environments, failing fast on missing environment variables.
5. **Parallel gRPC Performance & Channel Reuse**:
   - `ProductService.list_products` queries stock concurrently using `ThreadPoolExecutor`, while `BinStockGrpcClient` and `FulfillmentGrpcClient` reuse persistent gRPC channel connections across requests.

---

## 📂 Complete File Directory Structure (Hexagonal Architecture)

```
kinetix-catalog-service/
├── core/
│   ├── api/
│   │   ├── di.py                       # Dependency Injection Container
│   │   ├── serializers/                # REST API Serializers
│   │   └── views/                      # Clean REST Views
│   │       ├── product_list_view.py
│   │       ├── product_detail_view.py
│   │       ├── checkout_view.py
│   │       └── reserve_stock_view.py
│   ├── application/
│   │   ├── dto/                        # Data Transfer Objects
│   │   └── services/                   # Use Case Services (Product & Order)
│   ├── domain/
│   │   ├── entities/                   # Pure Domain Entities
│   │   └── repositories/               # Repository Port Interfaces
│   └── infrastructure/
│       ├── models/                     # Django ORM Models
│       ├── repositories/               # Django Repository Adapters
│       └── grpc/                       # gRPC Client Adapters (Channel Reuse)
│           ├── bin_stock_client.py
│           ├── fulfillment_client.py
│           └── generated/              # Protobuf Generated Modules
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
USE_POSTGRES=false venv/bin/pytest -v
```
