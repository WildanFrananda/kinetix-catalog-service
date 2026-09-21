"""Give products an updated_at, so a read model can page forward through changes.

Three steps rather than one, because `auto_now=True` is NOT NULL and the table already has rows.
Adding it in a single operation makes Django demand a one-off default and stamps every existing
product with the moment of the deploy — which would tell a consumer that the entire catalogue
changed at once, and send it through a full resync on a migration that changed no product at all.

Backfilling from created_at instead keeps the answer true: a row that has never been edited last
changed when it was written.
"""

import django.utils.timezone
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def backfill_from_created_at(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    ProductModel = apps.get_model("core", "ProductModel")
    ProductModel.objects.update(updated_at=models.F("created_at"))


def noop(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Reversing needs no data change — the column goes away in the operation above this one."""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_drop_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="productmodel",
            name="updated_at",
            field=models.DateTimeField(
                null=True, default=django.utils.timezone.now
            ),
        ),
        migrations.RunPython(backfill_from_created_at, noop),
        migrations.AlterField(
            model_name="productmodel",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="productmodel",
            index=models.Index(
                fields=["updated_at", "sku"], name="products_changed_since_idx"
            ),
        ),
    ]
