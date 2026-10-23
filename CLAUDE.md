# CLAUDE.md — kinetix-catalog-service

The workspace `AGENTS.md` holds the stack and the verification commands, and this repository's `AGENTS.md`
its conventions. This file holds decisions that the code states but cannot explain.

## Every setting comes from the environment

`config/settings.py` refuses to import, naming the variable, when any of `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_CONN_MAX_AGE` or `LOG_LEVEL` is missing or empty, and
`gunicorn.conf.py` refuses a missing `LOG_LEVEL` before it forks. Until 2026-10-23 all but `SECRET_KEY` and
`DB_PASSWORD` fell back to a lab value (`postgres`@`localhost:5432`, a sixty-second connection age, `INFO`, and
`localhost` as the only host whenever `DEBUG` was on). `DEBUG` is `true`/`1`/`yes` or `false`/`0`/`no` and nothing
else; `DB_CONN_MAX_AGE` is ASCII digits. `WAREHOUSE_GRPC_HOST` and `WAREHOUSE_GRPC_PORT` were settings nothing read
(the warehouse client reads `WAREHOUSE_GRPC_URL`) and are gone.

Every process imports the settings, `manage.py migrate` and mypy included, so every one needs every variable. Nothing
reads `USE_POSTGRES`: the engine is always Postgres, and the unit suite runs because no unit test opens a connection,
not because a variable switched it off. The tests set a variable to the empty string rather than unsetting it, because
`load_dotenv` fills only what is unset.

## A caller's request id is adopted on both surfaces

`RequestIdMiddleware` (HTTP `X-Request-Id`) and `RequestIdInterceptor` (gRPC `x-request-id`, first in
`catalog_grpc_server`'s chain, so a call the allow list refuses is logged under its id) adopt an id only when
`accepted_request_id` accepts it: 1 to 128 characters of letters, digits and `._:#/+=-`, which covers Kong's
`uuid` and `uuid#counter`, ASP.NET's trace identifier and base64. Anything else is ignored: logged as `-`, not echoed.
Until 2026-10-23 HTTP adopted and echoed any non-empty value, and the gRPC server never read one, so every gRPC log
line said `request_id: "-"` although order forwards the id.

A worker thread keeps a context variable between calls, so the id is reset when the call ends, raised or not. A
streaming call sets it around each step and never across a `yield`: a generator closed later, or on another
thread, would otherwise reset the variable under the next call.

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

A product's row in the feed carries its category's name and slug, and search files products by slug. Until
2026-10-23 renaming a category changed no product row, so search kept the old slug until each product was edited
or reindexed. The `categories_stamp_their_products` trigger (migration 0010) now restamps `change_transaction_id`
on every product filed under a category whose name or slug changes, in the renaming transaction, so the rename
reaches the feed (withdrawn products again as removals) once it commits, and not at all if it rolls back. A save
that changes neither field stamps nothing. A rename locks every product row of that category until it commits.

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
own 400, 404 and 500 (`core/api/error_handlers.py`) use it too, so no answer is HTML. No answer carries another
key: a DRF exception without a single coded detail (Django's `Http404`, a `ValidationError` holding a dict) is
answered with its status name and phrase, and its detail is dropped, not nested under `details`.

Django refuses to read a body over `DATA_UPLOAD_MAX_MEMORY_SIZE` (`RequestDataTooBig`) and a query string or form
over `DATA_UPLOAD_MAX_NUMBER_FIELDS` (`TooManyFieldsSent`); DRF 3.18 reads JSON through `request.body`, so the
limit holds for JSON too. Both reached the handler as unknown exceptions and answered 500 until 2026-10-23; they
are `413 BODY_TOO_LARGE` and `400 TOO_MANY_FIELDS` now. `URL_FORMAT_OVERRIDE` is off: `?format=xml` used to be a
renderer choice that answered 404 on every route, and is now an ignored query parameter.

## A database that cannot be reached is 503

The house failure mode: "the database did not answer" is not a server fault of the request. A Django
`OperationalError` whose psycopg cause has no SQLSTATE (the connection failed or broke), a class `08` state,
`57P01`-`57P03` (shutdown, crash, starting up) or `53300` (too many connections), and any `InterfaceError` (a
closed connection) answer `503 DATABASE_UNAVAILABLE` with `Retry-After`, public reads included; the cause is
logged, never sent (`is_database_unavailable`). An error the database answered with (a statement timeout, a
deadlock, a constraint) stays a 500. gRPC answers `UNAVAILABLE` for the same errors (next section).

## A failed RPC answers a fixed status

Until 2026-10-23 an exception raised by an RPC reached the caller as `UNKNOWN` with grpc's `Exception calling
application: …`, which carried the database's host and port during an outage. `ErrorStatusInterceptor`, wired by
`catalog_grpc_server` between the allow list and `DatabaseConnectionInterceptor`, now maps what an RPC raises:
`InvalidInputError` is `INVALID_ARGUMENT` with `<field> <reason>`, a database `is_database_unavailable` names is
`UNAVAILABLE`, and anything else is `INTERNAL`, both with a fixed details string and the cause in the log. Health and
reflection are left to grpc. `found: false` stays the only answer for "no such product", a NUL SKU included.

The servicer raises and never calls `context.abort`: grpc's abort raises a bare `Exception`, which the interceptor
would answer as `INTERNAL`. A cursor no catalog answer carries (a NUL in `last_sku`, an `updated_through` outside a
timestamp's range) is `INVALID_ARGUMENT`. Both callers read `UNAVAILABLE` and `INTERNAL` alike as "catalog could not
answer": order's `GetProduct` becomes `503 CATALOG_UNAVAILABLE`, and search's sync keeps its cursor and tries again
on its next tick.

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

A SKU is refused at create when its product page could not be reached: `create` (the create route), `mine` (the
seller's listing, since 2026-10-23), `.` and `..` (dot segments, removed by path normalisation), and anything
starting with `search` or `suggest`, because Kong's search routes are plain string prefixes under
`/api/v1/products/`. SKUs created before 2026-10-21 (before 2026-10-23 for `mine`) are not checked.

## A seller lists its own products

`GET /api/products/mine` answers the caller's products, withdrawn ones included with `is_active`, in the record
shape a create answers, paged and filtered like the public listing. It needs a seller's token (`SELLER_REQUIRED`
otherwise) and keys on the token's `sub`: identity's `GetMerchantInfo` answers the caller's own principal id as
`merchant_principal_id`, which is what `create_product` stores. If identity ever names another tenant, this
listing must ask it. It reads neither identity nor warehouse, so a seller that may no longer trade still sees its
records. Both listings order by `(-created_at, -id)`: `created_at` alone left rows written in the same instant in
no fixed order, so offset paging could show one twice and another never.

## Products of a merchant that may no longer trade stay listed

Ruled by the user on 2026-10-22: catalog reads never ask identity, so a suspended or closed merchant's products
stay listed, readable and searchable, and order's checkout refuses them. Hiding them waits for the suspension work;
it is not a catalog bug.

## Admin actions are audited

Category writes are the only admin-only requests here. Once `category_manager` has accepted the caller, the view
names the action (`core/api/admin_actions.py`), and `AdminAuditedApiView.finalize_response` writes one
`admin_action` line at INFO (`actor` the token's `sub`, `action`, `target` the id in the path or the id a create
answered, `outcome`, `request_id`) and counts `kinetix_admin_actions_total{action,outcome}`: below 400 is `done`,
4xx `refused`, 5xx `failed`. A caller refused at the role check is not an admin action and is not recorded.
`admin_actions.py` publishes every action and outcome at zero when it is imported, which is when a worker first
loads the URLconf (the first health probe), as the gRPC clients do; under gunicorn each worker writes its own
multiprocess file and `/metrics` merges them.

## Text Postgres cannot hold is refused

A NUL character cannot be stored in a Postgres text column, and a query carrying one raised `DataError` (500).
Every text field, filter and category name refuses it as `INVALID_INPUT`; a SKU path carrying one is not found.
Whole numbers are ASCII digits only: `str.isdigit()` accepted `²`, which `int()` then refused.

## The log formatter's imports create no metric

gunicorn applies `logconfig_dict` before its `on_starting` hook makes `PROMETHEUS_MULTIPROC_DIR`, and importing
`core.infrastructure.observability.json_log_formatter` runs the package's `__init__.py` first. catalog v1.2.0 exported the
admin audit helpers from that package; they import `core.infrastructure.metrics`, whose metrics open their files in the
multiprocess directory when they are created, so gunicorn died on its first line with "Unable to configure formatter
'json'" (2026-10-23, Deploy run 39921518410, rolled back to v1.1.0). The helpers are imported from
`core.infrastructure.observability.admin_action_audit` directly and the package exports nothing that touches
`prometheus_client`. `test_gunicorn_log_config_unit.py` applies the logging configuration in a fresh interpreter while the
directory does not exist yet, and checks that importing the formatter loads no metrics library.
