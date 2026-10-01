from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0069_servicemonitorpage"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommonCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=100, verbose_name="平台")),
                ("card_number", models.CharField(max_length=64, verbose_name="卡号")),
                ("expiry", models.CharField(max_length=16, verbose_name="有效期")),
                ("cvv", models.CharField(max_length=8, verbose_name="安全码")),
                ("remark", models.CharField(blank=True, default="", max_length=500, verbose_name="备注")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="最近更改日期")),
            ],
            options={
                "verbose_name": "常用卡",
                "verbose_name_plural": "常用卡",
                "ordering": ["-updated_at", "id"],
            },
        ),
    ]
