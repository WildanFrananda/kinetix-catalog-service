from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_key_products_on_merchant_principal"),
    ]

    operations = [
        migrations.DeleteModel(name="OrderItemModel"),
        migrations.DeleteModel(name="OrderModel"),
    ]
