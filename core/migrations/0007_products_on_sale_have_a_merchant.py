from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.utils import timezone


def withdraw_products_without_a_merchant(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    product = apps.get_model("core", "ProductModel")
    product.objects.filter(is_active=True).filter(
        models.Q(merchant_principal_id__isnull=True) | models.Q(merchant_principal_id="")
    ).update(is_active=False, updated_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_products_know_when_they_changed"),
    ]

    operations = [
        migrations.RunPython(withdraw_products_without_a_merchant, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="productmodel",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(is_active=False)
                    | (models.Q(merchant_principal_id__isnull=False) & ~models.Q(merchant_principal_id=""))
                ),
                name="products_on_sale_have_a_merchant",
            ),
        ),
        migrations.AlterField(
            model_name="productmodel",
            name="category",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="products",
                to="core.categorymodel",
            ),
        ),
    ]
