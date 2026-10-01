from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0071_alter_commoncard_remark"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommonAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=100, verbose_name="平台")),
                ("account", models.CharField(max_length=200, verbose_name="账号")),
                ("password", models.CharField(max_length=500, verbose_name="密码")),
                ("remark", models.CharField(blank=True, default="", max_length=500, verbose_name="备注")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "常用账号",
                "verbose_name_plural": "常用账号",
                "ordering": ["-updated_at", "id"],
            },
        ),
    ]
