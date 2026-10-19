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
fetch succeeds.

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
