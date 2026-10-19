from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_products_on_sale_have_a_merchant"),
    ]

    operations = [
        migrations.AddField(
            model_name="productmodel",
            name="weight_grams",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="productmodel",
            constraint=models.CheckConstraint(
                condition=models.Q(weight_grams__isnull=True) | models.Q(weight_grams__gt=0),
                name="products_weigh_something",
            ),
        ),
    ]
