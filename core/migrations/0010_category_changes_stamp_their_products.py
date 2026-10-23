from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_products_record_their_change_transaction"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                CREATE FUNCTION categories_stamp_their_products() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    UPDATE products
                    SET change_transaction_id = pg_current_xact_id()
                    WHERE category_id = NEW.id;
                    RETURN NULL;
                END
                $$
                """,
                """
                CREATE TRIGGER categories_stamp_their_products
                AFTER UPDATE OF name, slug ON categories
                FOR EACH ROW
                WHEN (OLD.name IS DISTINCT FROM NEW.name OR OLD.slug IS DISTINCT FROM NEW.slug)
                EXECUTE FUNCTION categories_stamp_their_products()
                """,
            ],
            reverse_sql=[
                "DROP TRIGGER categories_stamp_their_products ON categories",
                "DROP FUNCTION categories_stamp_their_products()",
            ],
        ),
    ]
