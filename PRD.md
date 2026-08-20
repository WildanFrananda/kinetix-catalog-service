# 📄 Product Requirements Document (PRD)
## Storefront Catalog, Real-Time Stock Check & Stock Reservation API

> **Project:** `storefront` (Python 6.1 / Django REST Framework)  
> **Architecture:** Hexagonal Architecture (Ports & Adapters)  
> **Quality Standards:** 100% Strict Typing (`mypy`), Test Pyramid (`pytest`), Zero Hardcoded Secrets (`.env`)  
> **gRPC Integration:** `fashion_fulfillment_oms` (`proto/fulfillment/v1/bin_stock_service.proto`)

---

## 🎯 1. Objective & Scope

The `storefront` microservice serves as the **Primary Public API Gateway** for client applications (Mobile App, Web Frontend). This document defines the **Product Catalog, Real-Time Warehouse Stock Query, and Cart Stock Reservation API**.

### Key Objectives:
1. **Public Catalog API**: Allow mobile and web clients to query products, categories, pricing, and live availability.
2. **Real-Time Warehouse Stock Query via gRPC**: Check exact stock counts across warehouse bins (`fashion_fulfillment_oms` gRPC `BinStockService`) to prevent overselling.
3. **Cart Stock Reservation**: Temporarily reserve bin stock when a buyer initiates checkout, ensuring stock integrity before final payment.

---

## 🏛️ 2. Hexagonal Architecture Layout (`storefront/products/` & `storefront/cart/`)

Following `AGENTS.md` guidelines, all modules strictly follow layer separation:

```
storefront/
└── core/
    ├── domain/
    │   ├── entities.py           # Pure Python dataclasses: Product, Category, Order, StockInfo
    │   └── repositories.py       # ProductRepository (ABC), OrderRepository (ABC), Ports (ABC)
    ├── application/
    │   ├── dto.py                # All DTOs: ProductFilterDTO, CreateOrderInputDTO, ReserveCartStockInputDTO
    │   └── services.py           # Unified ProductService & OrderService
    ├── infrastructure/
    │   ├── models.py             # CategoryModel, ProductModel, OrderModel, OrderItemModel (Django ORM)
    │   ├── repositories.py       # DjangoProductRepository, DjangoOrderRepository
    │   └── grpc/
    │       ├── fulfillment_client.py # FulfillmentGrpcClient (Adapter to OMS port 50051)
    │       └── bin_stock_client.py    # BinStockGrpcClient (Adapter to OMS port 50051)
    ├── api/
    │   ├── serializers.py        # Serializers
    │   ├── views.py              # ProductListView, ProductDetailView, CheckoutView, ReserveStockView
    │   └── di.py                 # get_product_service(), get_order_service()
    ├── tests/
    │   ├── unit/                 # Domain service unit tests
    │   ├── integration/          # Django ORM repository tests
    │   └── api/                  # End-to-End APIView tests
    └── urls.py                   # Single consolidated routes: /api/products/, /api/orders/checkout/, /api/cart/reserve/
```


---

## 📡 3. API Endpoints Specification

### 3.1 List Products Catalog
- **Endpoint**: `GET /api/products/`
- **Query Parameters**:
  - `category` (optional, string): Filter by category slug (e.g. `apparel`, `footwear`)
  - `search` (optional, string): Search in title, description, or SKU
  - `page` (optional, integer, default: 1)
  - `page_size` (optional, integer, default: 10)
- **Response `200 OK`**:
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
      "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800",
      "available_stock": 25,
      "is_in_stock": true
    }
  ]
}
```

---

### 3.2 Product Detail & Live Bin Location Stock
- **Endpoint**: `GET /api/products/{sku}/`
- **Response `200 OK`**:
```json
{
  "id": 1,
  "sku": "TSHIRT-BLK-M",
  "title": "Oversized Heavyweight Black Tee - M",
  "description": "240 GSM Premium Cotton Oversized T-Shirt with relaxed silhouette.",
  "category": "Apparel",
  "price": "189000.00",
  "currency": "IDR",
  "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800",
  "warehouse_stock": {
    "sku": "TSHIRT-BLK-M",
    "bin_location": "Bin A-04",
    "available_quantity": 25,
    "reserved_quantity": 0
  }
}
```

---

### 3.3 Cart Bin Stock Reservation (gRPC Port)
- **Endpoint**: `POST /api/cart/reserve/`
- **Request Body**:
```json
{
  "sku": "TSHIRT-BLK-M",
  "quantity": 2
}
```
- **Response `200 OK`**:
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

---

## ⚙️ 4. Data Models & Database Schema

### `CategoryModel` (`categories` table)
| Field | Type | Attributes |
|---|---|---|
| `id` | BigAutoField | Primary Key |
| `name` | CharField(128) | Unique, Index |
| `slug` | SlugField(128) | Unique, Index |

### `ProductModel` (`products` table)
| Field | Type | Attributes |
|---|---|---|
| `id` | BigAutoField | Primary Key |
| `sku` | CharField(64) | Unique, Index |
| `title` | CharField(255) | Index |
| `description` | TextField | Blank=True |
| `price` | DecimalField(12, 2) | |
| `currency` | CharField(8) | Default: `IDR` |
| `image_url` | URLField | Blank=True |
| `category` | ForeignKey(CategoryModel) | On Delete Cascade |
| `created_at` | DateTimeField | Auto Add Now |

---

## 🔌 5. gRPC Integration Schema (`BinStockService`)

`BinStockGrpcClient` connects to `fashion_fulfillment_oms` gRPC port `50051` using the existing Protobuf schema:

1. **`GetBinStockInfo(GetBinStockInfoRequest)`**:
   - Request: `{ sku: "TSHIRT-BLK-M" }`
   - Response: `{ bin_location: "Bin A-04", available_quantity: 25, reserved_quantity: 0 }`
2. **`ReserveStock(ReserveStockRequest)`**:
   - Request: `{ sku: "TSHIRT-BLK-M", requested_quantity: 2 }`
   - Response: `{ success: true, bin_location: "Bin A-04", remaining_available: 23 }`

---

## 🔺 6. Test Pyramid & Quality Requirements

1. **Unit Tests**: Test `ListProductsService`, `GetProductDetailService`, `ReserveCartStockService` using fake in-memory repositories & fake gRPC ports.
2. **Integration Tests**: Test `DjangoProductRepository` against real PostgreSQL / SQLite.
3. **API Tests**: Test `ProductListView`, `ProductDetailView`, `ReserveStockView` HTTP endpoints.
4. **Strict Typing**: Run `mypy orders products cart` to ensure `Success: no issues found`.
