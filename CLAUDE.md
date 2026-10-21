# CLAUDE.md — kinetix-catalog-service

The workspace `AGENTS.md` holds the stack and the verification commands, and this repository's `AGENTS.md`
its conventions. This file holds decisions that the code states but cannot explain.

## Every product has a weight

`weight_grams` is required when a product is created: a positive whole number of grams, at most 1,000,000
(`ProductFieldParser`). The column stays nullable, with a check that a weight present is positive
(`products_weigh_something`), because products created before 2026-10-18 have none, and catalog does not
invent one for them. An update may leave it out. `GetProduct` sets the field only when there is a weight, so
order can tell "no weight" from zero; order refuses a checkout holding a product without one, and the
merchant sets it to sell the product again.

Shipping is priced from the route and the parcel's weight, and until 2026-10-18 neither was known: every
buyer paid a tier's minimum fee.

## An unknown signing key is looked for at most every ten seconds

`SigningKeySet` answers a token's `kid` from the keys it holds. A `kid` it does not hold makes it fetch
identity's JWKS again only if the last fetch was at least `UNKNOWN_KEY_REFRESH_SECONDS` (ten) ago, one fetch
at a time. PyJWT's `PyJWKClient` fetches on every unknown `kid`, so until 2026-10-19 a stream of forged
tokens with made-up key ids made identity answer once per request. A fetch that failed is remembered: a
token whose key is unknown then gets `IdentityKeysUnavailable` (503), never "invalid token", until a later
fetch succeeds. A key set with no usable key (`PyJWKSetError`, e.g. `{"keys": []}`) counts as a failed fetch.

## The change feed reads in commit-safe order

`ChangedSince` used to page by `(updated_at, sku)`. `updated_at` is written before the transaction commits, so a
product saved in a transaction that committed after a later one's could be behind the cursor by the time it
became visible, and search never indexed that change. Since 2026-10-19 every product carries
`change_transaction_id xid8`, stamped by the `products_stamp_change_transaction` trigger on every insert and
update, and a cursor that carries `transaction_id` is served by `find_changed_after`: rows ordered by
`(change_transaction_id, sku)`, only below `pg_snapshot_xmin(pg_current_snapshot())`. A product whose
transaction is still open holds the feed back; it is never skipped. Any transaction left open in the cluster
holds it back too, which is the price.

A cursor without `transaction_id` is still served the old way, for search's release before contracts 1.5.0.
Once search speaks the new cursor in production, `find_changed_since` and the `(updated_at, sku)` index have
no reader and go. The migration stamped every existing product with its own transaction, so a reader starting
from zero sees the whole catalogue once.

The tests that prove the order run with `django_db(transaction=True)`: rows written inside a test transaction
that never commits are never below the horizon.

## Every route answers with and without its trailing slash

Kong's catalog routes strip `/api/v1` and send `/api/products…` and `/api/categories…` as the client wrote them, so
`GET /api/v1/products` arrives as `/api/products`. Django's `APPEND_SLASH` used to answer that with a 301 to
`/api/products/`, a path Kong does not route, and a redirected POST became a GET. `core/urls.py` now lists every
route twice, with and without the slash, and `APPEND_SLASH` is off, so catalog never redirects to an upstream path.
Only the slashed form is named, so `reverse()` keeps answering it. The metrics label tells the two forms apart.

## One error shape

Every refusal is `{"error": CODE, "message": text, "traceId": X-Request-Id or "-"}`, plus `field` for
`INVALID_INPUT` and `product_count` for `CATEGORY_IN_USE`. Views raise; `core/api/exception_handler.py` maps domain
errors and DRF's own exceptions (its code upper-cased) to that shape, and anything else to a JSON 500. Django's
own 400, 404 and 500 (`core/api/error_handlers.py`) use it too, so no answer is HTML.

## Public reads never read the token

`PublicReadApiView` skips authentication on GET, HEAD and OPTIONS. A catalog read answers the same to everyone,
so a stale token, a forged one, or identity's keys being unreachable cannot turn a product page into a 401 or a
503. Pricing reads its token, because its answer depends on the caller (an owner sees quota); there an invalid
token is anonymous and unreachable keys are 503. A write verifies the token as before.

`JWT_ISSUER`, `JWT_AUDIENCE` and `IDENTITY_JWKS_URL` are read when `config/wsgi.py` is imported, so gunicorn's
worker fails to boot without them. They used to be read on the first authenticated request, and a missing one was
answered "Invalid token". `manage.py` commands (migrate, grpcserver) do not import `wsgi.py` and do not need them.

## A SKU is permanent, and every SKU can be fetched

An update may restate a product's SKU but not change it (`INVALID_INPUT`, field `sku`). Search indexes and
pricing promotions are keyed by SKU, and the change feed reports removals only for withdrawn rows, so a renamed
SKU left the old one behind in both. A new SKU is a new product.

A SKU is refused at create when its product page could not be reached: `create` (the create route), `.` and `..`
(dot segments, removed by path normalisation), and anything starting with `search` or `suggest`, because Kong's
search routes are plain string prefixes under `/api/v1/products/`. SKUs created before 2026-10-21 are not checked.

## Text Postgres cannot hold is refused

A NUL character cannot be stored in a Postgres text column, and a query carrying one raised `DataError` (500).
Every text field, filter and category name refuses it as `INVALID_INPUT`; a SKU path carrying one is not found.
Whole numbers are ASCII digits only: `str.isdigit()` accepted `²`, which `int()` then refused.
