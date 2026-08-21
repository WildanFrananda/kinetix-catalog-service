# 🛒 Kinetix Catalog Service (`kinetix-catalog-service`)

High-performance product catalog, search engine, inventory stock query, cart reservation, and checkout entrypoint microservice built with **Python 3.12+**, **Django 6.0+**, **gRPC Client Communication**, **PostgreSQL 16**, and **Strict Type Checking (mypy)** following **Hexagonal Architecture**.

---

## 🏛️ Domain Architecture & Resolved Audit Upgrades

1. **gRPC Channel Reuse (Singleton Connection Pool)**:
   - `BinStockGrpcClient` & `FulfillmentGrpcClient` reuse persistent gRPC channel connections (`self._channel` & `self._stub`) across requests to eliminate socket/memory leaks.
2. **Parallel gRPC Query Execution (ThreadPoolExecutor)**:
   - `ProductService.list_products` queries stock for paginated items concurrently using `concurrent.futures.ThreadPoolExecutor` to eliminate N+1 gRPC query latency.
3. **Strict Stock Integrity (No Fake 25 Stock Fallbacks)**:
   - Completely eliminated silent fallback fake stock numbers ("Bin A-01 (Offline Fallback) 25 items"). When warehouse gRPC is unavailable, exact `available_quantity=0` is returned.
4. **Clean Codebase (Zero Dead Code Duplicates)**:
   - Removed dead code duplicate view files (`cart_views.py` & `order_views.py`), retaining clean active REST views (`ProductListView`, `ProductDetailView`, `CheckoutView`, `ReserveStockView`).

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
│       ├── django_models/              # Django ORM Models
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
# 1. Activate Python Virtual Environment
source venv/bin/activate

# 2. Run MyPy Strict Static Type Checking
mypy core

# 3. Run PyTest Test Suite
USE_POSTGRES=false python -m pytest -v
```
