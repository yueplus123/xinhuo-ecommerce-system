from django.db import migrations, models
import django.db.models.deletion


def migrate_hall_images(apps, schema_editor):
    HallBlock = apps.get_model("catalog", "HallBlock")
    HallBlockImage = apps.get_model("catalog", "HallBlockImage")
    for block in HallBlock.objects.exclude(image="").exclude(image__isnull=True):
        if not block.image:
            continue
        if HallBlockImage.objects.filter(block_id=block.pk).exists():
            continue
        HallBlockImage.objects.create(
            block_id=block.pk,
            image=block.image,
            sort_order=0,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0052_usd_proxy_price_pool"),
    ]

    operations = [
        migrations.CreateModel(
            name="HallBlockImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="hall/", verbose_name="配图")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                (
                    "block",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="catalog.hallblock",
                        verbose_name="大厅板块",
                    ),
                ),
            ],
            options={
                "verbose_name": "大厅配图",
                "verbose_name_plural": "大厅配图",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(migrate_hall_images, migrations.RunPython.noop),
    ]
