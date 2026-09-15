from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def refuse_if_populated(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    product = apps.get_model("core", "ProductModel")
    rows = product.objects.exclude(merchant_id=None).count()
    if rows:
        raise RuntimeError(
            f"{rows} product(s) name a merchant by account id and this migration has no way to "
            "convert them. Resolve each merchant_id through identity before dropping the column."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_add_product_merchant_and_is_active"),
    ]

    operations = [
        migrations.RunPython(refuse_if_populated, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="productmodel",
            name="merchant_id",
        ),
        migrations.AddField(
            model_name="productmodel",
            name="merchant_principal_id",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
    ]
