from django.db import migrations, models


def seed_default_page(apps, schema_editor):
    ServiceMonitorPage = apps.get_model("catalog", "ServiceMonitorPage")
    if ServiceMonitorPage.objects.exists():
        return
    ServiceMonitorPage.objects.create(
        name="Uptime Kuma",
        share_url="http://127.0.0.1:3001/",
        sort_order=1,
        is_active=True,
    )


def unseed_default_page(apps, schema_editor):
    ServiceMonitorPage = apps.get_model("catalog", "ServiceMonitorPage")
    ServiceMonitorPage.objects.filter(share_url="http://127.0.0.1:3001/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0068_delete_wallospage"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceMonitorPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="页面名称")),
                ("share_url", models.URLField(verbose_name="页面链接")),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="数字越小越靠前；职员端「服务监控」按此顺序展示。",
                        verbose_name="排序",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
            ],
            options={
                "verbose_name": "服务监控页面",
                "verbose_name_plural": "服务监控页面",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_default_page, unseed_default_page),
    ]
