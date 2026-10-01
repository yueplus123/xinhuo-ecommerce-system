from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0049_sku_precaution"),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="platform_tags",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"type": "platform"},
                related_name="skus_platform",
                to="catalog.tag",
                verbose_name="平台标签",
            ),
        ),
    ]
