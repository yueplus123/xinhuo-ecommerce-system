from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0070_commoncard"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commoncard",
            name="remark",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="备注/平台"),
        ),
    ]
