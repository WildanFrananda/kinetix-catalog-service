# 🛒 Storefront Microservice API (Django 6 REST & gRPC Client)

The **Storefront microservice** serves as the customer-facing gateway for fashion catalog search, real-time warehouse bin stock lookup, cart item reservation, and checkout dispatch to the Warehouse OMS.

---

## 🏛️ Architecture & Clean Code Rules

Built with **Django 6.0+**, **Django REST Framework**, and **gRPC Client Adapters** following **Hexagonal Architecture (Ports and Adapters)**:

1. **100% Static Type Annotations (`mypy --strict`)**: `Success: no issues found in 96 source files`.
2. **Strict Single-Class-Per-File**: Every entity, DTO, serializer, view, repository, and fake test double lives in its own dedicated Python file.
3. **Pure Domain Core**: Zero framework imports in `core/domain/`.
4. **Thin Controllers/Views**: APIViews only delegate to `ProductService` or `OrderService` and format DRF responses.
5. **No Double Blank Lines**: Maximum 1 empty line between code blocks.

---

## 📂 Complete File Directory Structure

```
storefront/core/
├── domain/
│   ├── entities/               # Pure Dataclasses (1 class per file)
│   │   ├── product.py          # Product entity
│   │   ├── category.py         # Category entity
│   │   ├── stock_info.py       # StockInfo entity
│   │   ├── order.py            # Order entity
│   │   ├── order_item.py       # OrderItem entity
│   │   ├── money.py            # Money Value Object
│   │   ├── address.py          # Address Value Object
│   │   └── reservation_result.py # ReservationResult entity
│   └── repositories/           # Abstract Port Interfaces (1 class per file)
│       ├── product_repository.py     # ProductRepository ABC
│       ├── order_repository.py       # OrderRepository ABC
│       ├── bin_stock_service_port.py # BinStockServicePort ABC
│       └── fulfillment_service_port.py # FulfillmentServicePort ABC
├── application/
│   ├── dto/                    # Input/Output DTOs (1 class per file)
│   │   ├── product_filter_dto.py
│   │   ├── product_summary_dto.py
│   │   ├── product_list_result_dto.py
│   │   ├── warehouse_stock_dto.py
│   │   ├── product_detail_dto.py
│   │   ├── order_item_dto.py
│   │   ├── create_order_input_dto.py
│   │   ├── checkout_result_dto.py
│   │   └── reserve_cart_stock_input_dto.py
│   └── services/               # Unified Domain Services (1 class per file)
│       ├── product_service.py  # Catalog search & warehouse stock retrieval
│       └── order_service.py    # Checkout orchestration & cart stock reservation
├── infrastructure/
│   ├── models/                 # Django ORM Adapters (1 model per file)
│   │   ├── product_model.py
│   │   ├── category_model.py
│   │   ├── order_model.py
│   │   └── order_item_model.py
│   ├── repositories/           # Database Adapters (1 class per file)
│   │   ├── django_product_repository.py
│   │   └── django_order_repository.py
│   └── grpc/                   # Outbound gRPC Adapters (1 class per file)
│       ├── fulfillment_client.py   # Adapter for OMS port 50051
│       └── bin_stock_client.py      # Adapter for OMS port 50051
└── api/
    ├── serializers/            # DRF Serializers (1 class per file)
    │   ├── product_summary_serializer.py
    │   ├── product_list_response_serializer.py
    │   ├── warehouse_stock_serializer.py
    │   ├── product_detail_serializer.py
    │   ├── order_item_serializer.py
    │   ├── checkout_request_serializer.py
    │   ├── reserve_stock_request_serializer.py
    │   └── reservation_result_serializer.py
    ├── views/                  # Thin API Views (1 class per file)
    │   ├── product_list_view.py
    │   ├── product_detail_view.py
    │   ├── checkout_view.py
    │   └── reserve_stock_view.py
    └── di.py                   # Dependency Injection Wiring
```

---

## 📡 REST API Specifications

### 1. Catalog Search & Filter
- **Endpoint**: `GET /api/products/`
- **Params**: `category` (slug), `search` (query string), `page` (int), `page_size` (int).
- **Example Response (`200 OK`)**:
  ```json
  {
    "count": 5,
    "page": 1,
    "page_size": 10,
    "results": [
      {
        "id": 1,
        "sku": "TSHIRT-BLK-M",
        "title": "Oversized Heavyweight Black Tee - M",
        "category": "Apparel",
        "price": "189000.00",
        "currency": "IDR",
        "image_url": "https://images.unsplash.com/...",
        "available_stock": 25,
        "is_in_stock": true
      }
    ]
  }
  ```

### 2. Product Detail & Bin Location Query
- **Endpoint**: `GET /api/products/{sku}/`
- **Example Response (`200 OK`)**:
  ```json
  {
    "id": 1,
    "sku": "TSHIRT-BLK-M",
    "title": "Oversized Heavyweight Black Tee - M",
    "description": "240 GSM Premium Cotton Oversized T-Shirt",
    "category": "Apparel",
    "price": "189000.00",
    "currency": "IDR",
    "image_url": "https://images.unsplash.com/...",
    "warehouse_stock": {
      "sku": "TSHIRT-BLK-M",
      "bin_location": "Bin A-04",
      "available_quantity": 25,
      "reserved_quantity": 2
    }
  }
  ```

### 3. Cart Stock Reservation
- **Endpoint**: `POST /api/cart/reserve/`
- **Request**: `{"sku": "TSHIRT-BLK-M", "quantity": 2}`
- **Response (`200 OK`)**:
  ```json
  {
    "sku": "TSHIRT-BLK-M",
    "quantity": 2,
    "success": true,
    "bin_location": "Bin A-04",
    "message": "Stock successfully reserved for 15 minutes",
    "expires_in_seconds": 900
  }
  ```

### 4. Order Checkout
- **Endpoint**: `POST /api/orders/checkout/`
- **Request Body**:
  ```json
  {
    "merchant_api_key": "GRPC_TEST_KEY_123",
    "buyer_name": "Charlie Brown",
    "buyer_phone": "0899887766",
    "street_address": "Jl. MH Thamrin 9",
    "city": "Jakarta",
    "postal_code": "10350",
    "items": [
      {
        "sku": "HOODIE-GRY-L",
        "product_name": "Grey Hoodie L",
        "quantity": 1,
        "price": "450000.00"
      }
    ]
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "success": true,
    "order_id": 1,
    "order_number": "ORD-STF-A1B2C3D4",
    "status": "received",
    "total_amount": "450000.00",
    "fulfillment_ref": "101",
    "message": "Checkout completed and dispatched to Warehouse OMS"
  }
  ```

---

## 🛠️ Environment Variables Configuration (`.env`)

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `django-insecure-key-xyz` | Django framework secret key |
| `DEBUG` | `True` | Django debug flag |
| `ALLOWED_HOSTS` | `*` | Allowed host names |
| `USE_POSTGRES` | `False` | Toggle PostgreSQL (`True`) vs SQLite (`False`) |
| `POSTGRES_DB` | `storefront_db` | PostgreSQL database name |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host address |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `OMS_GRPC_HOST` | `localhost:50051` | Target address of Warehouse OMS gRPC Server |
| `MERCHANT_API_KEY` | `INTERNAL_OMS_KEY` | Merchant API authentication key |

---

## 🧪 Local Execution & Verification

```bash
# 1. Virtual Environment & Dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Static Type Check
mypy core

# 3. Test Pyramid Suite Execution
python -m pytest -v

# 4. Migrate Database & Seed Sample Data
python manage.py migrate
python manage.py seed_catalog

# 5. Run Server
python manage.py runserver 0.0.0.0:8000
```
