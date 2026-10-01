from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_quickphrasetemplate"),
    ]

    operations = [
        migrations.CreateModel(
            name="RenewalReminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=200, verbose_name="客户名称")),
                ("contact", models.CharField(blank=True, max_length=200, verbose_name="联系方式")),
                ("product_name", models.CharField(default="ChatGPT", max_length=200, verbose_name="产品")),
                ("start_date", models.DateField(verbose_name="开通日期")),
                ("note", models.CharField(blank=True, max_length=500, verbose_name="备注")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用提醒")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "ordering": ["-start_date", "-id"],
            },
        ),
    ]
