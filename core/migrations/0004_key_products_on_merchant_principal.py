from django.db import migrations, models


def refuse_if_populated(apps, schema_editor):
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
