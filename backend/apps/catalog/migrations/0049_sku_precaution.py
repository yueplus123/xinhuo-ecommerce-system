from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0048_tag_pools"),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="precaution",
            field=models.TextField(blank=True, verbose_name="注意事项"),
        ),
    ]
