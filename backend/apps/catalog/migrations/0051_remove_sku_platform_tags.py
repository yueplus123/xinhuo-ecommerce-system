from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0050_sku_platform_tags"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sku",
            name="platform_tags",
        ),
    ]
