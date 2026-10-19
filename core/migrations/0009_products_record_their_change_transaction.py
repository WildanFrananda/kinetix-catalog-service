from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_products_have_a_weight"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE products ADD COLUMN change_transaction_id xid8",
                "UPDATE products SET change_transaction_id = pg_current_xact_id()",
                "ALTER TABLE products ALTER COLUMN change_transaction_id SET NOT NULL",
                """
                CREATE FUNCTION products_stamp_change_transaction() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    NEW.change_transaction_id := pg_current_xact_id();
                    RETURN NEW;
                END
                $$
                """,
                """
                CREATE TRIGGER products_stamp_change_transaction
                BEFORE INSERT OR UPDATE ON products
                FOR EACH ROW EXECUTE FUNCTION products_stamp_change_transaction()
                """,
                "CREATE INDEX products_change_feed_idx ON products (change_transaction_id, sku)",
            ],
            reverse_sql=[
                "DROP INDEX products_change_feed_idx",
                "DROP TRIGGER products_stamp_change_transaction ON products",
                "DROP FUNCTION products_stamp_change_transaction()",
                "ALTER TABLE products DROP COLUMN change_transaction_id",
            ],
        ),
    ]
