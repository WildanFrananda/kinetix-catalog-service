# 📄 Product Requirements Document (PRD)
## Storefront Catalog, Real-Time Stock Check & Stock Reservation API

> **Project:** `storefront` (Python 6.1 / Django REST Framework)  
> **Architecture:** Hexagonal Architecture (Ports & Adapters)  
> **Quality Standards:** 100% Strict Typing (`mypy`), Test Pyramid (`pytest`), Zero Hardcoded Secrets (`.env`)  
> **gRPC Integration:** `fashion_fulfillment_oms` (`proto/fulfillment/v1/bin_stock_service.proto`)

---

## 🎯 1. Objective & Scope

This service owns **products, categories and search**. Nothing else.

It is **not** the public API gateway — that is `kinetix-api-gateway`, which every client talks to and
which routes `/api/v1/products` and `/api/v1/categories` here. It does **not** own checkout, orders,
buyers or addresses: the order aggregate belongs to `kinetix-order-service` and the person behind it
to `kinetix-identity-service`. An earlier version of this document said otherwise, and the code
followed it — catalog carried an `orders` table with `buyer_name`, `buyer_phone`, `street_address`,
`city` and `postal_code` until 2026-09-20. It is gone. (docs/BOUNDARY-DEBT.md C1, C5, C10)

### Key Objectives:
1. **Product catalog API**: let clients query products and categories.
2. **Real-time warehouse stock query via gRPC**: read stock counts from warehouse's `BinStockService`
   so a listing does not advertise what is not on a shelf. Warehouse owns the stock; catalog reads it.

---

## 🏛️ 2. Hexagonal Architecture Layout (`storefront/products/` & `storefront/cart/`)

Following `AGENTS.md` guidelines, all modules strictly follow layer separation:

```
storefront/
└── core/
    ├── domain/
    │   ├── entities/             # One dataclass per file: Product, Category, Money, StockInfo, StockStatus
    │   └── repositories/         # ProductRepository, CategoryRepository (ABCs)
    ├── application/
    │   ├── dto/                  # One DTO per file
    │   └── services/             # ProductService, CategoryService
    ├── infrastructure/
    │   ├── models/               # CategoryModel, ProductModel (Django ORM) — and nothing else
    │   ├── repositories/         # DjangoProductRepository, DjangoCategoryRepository
    │   ├── security/             # IdentityTokenAuthentication, TokenVerifier, Principal, mTLS
    │   └── grpc/
    │       └── bin_stock_client.py  # BinStockGrpcClient — reads warehouse stock
    ├── api/
    │   ├── serializers/
    │   ├── views/                # ProductView, CategoryView, HealthView, ReadinessView, MetricsView
    │   └── di.py
    ├── tests/
    │   ├── unit/                 # Domain service unit tests
    │   ├── integration/          # Django ORM repository tests
    │   └── api/                  # End-to-End APIView tests
    └── urls.py                   # /api/products/, /api/categories/ — no checkout, no orders
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
      "is_in_stock": true,
      "stock_status": "in_stock"
    }
  ]
}
```

`stock_status` is one of `in_stock`, `out_of_stock` or `unknown`. `unknown` means warehouse could
not be reached for that SKU, and `available_stock` and `is_in_stock` are then `null` — the
response never states a stock number this service did not obtain. A genuine sell-out is
`"available_stock": 0, "is_in_stock": false, "stock_status": "out_of_stock"`.

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
    "reserved_quantity": 0,
    "stock_status": "in_stock"
  }
}
```

When warehouse cannot be reached, `stock_status` is `unknown` and `bin_location`,
`available_quantity` and `reserved_quantity` are all `null`.

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
2. **Integration Tests**: Test `DjangoProductRepository` against real PostgreSQL.
3. **API Tests**: Test `ProductListView`, `ProductDetailView`, `ReserveStockView` HTTP endpoints.
4. **Strict Typing**: Run `mypy orders products cart` to ensure `Success: no issues found`.
