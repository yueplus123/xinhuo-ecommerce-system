from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0045_sku_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="SKUImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="sku_screenshots/", verbose_name="会员截图")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                (
                    "sku",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_images",
                        to="catalog.sku",
                        verbose_name="SKU",
                    ),
                ),
            ],
            options={
                "verbose_name": "SKU会员截图",
                "verbose_name_plural": "SKU会员截图",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
