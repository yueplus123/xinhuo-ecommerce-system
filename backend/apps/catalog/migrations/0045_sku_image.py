from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0044_sku_price_structure"),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="sku_screenshots/",
                verbose_name="会员截图",
            ),
        ),
    ]
