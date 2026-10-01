from django.db import migrations, models


def seed_default_fanbox(apps, schema_editor):
    FanboxStatsPage = apps.get_model("catalog", "FanboxStatsPage")
    if FanboxStatsPage.objects.exists():
        return
    FanboxStatsPage.objects.create(
        name="fanbox投稿作品统计",
        share_url="https://fanbox.xinhuo.pro/",
        sort_order=1,
        is_active=True,
    )


def unseed_default_fanbox(apps, schema_editor):
    FanboxStatsPage = apps.get_model("catalog", "FanboxStatsPage")
    FanboxStatsPage.objects.filter(share_url="https://fanbox.xinhuo.pro/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0064_pictcartpage"),
    ]

    operations = [
        migrations.CreateModel(
            name="FanboxStatsPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="页面名称")),
                ("share_url", models.URLField(verbose_name="页面链接")),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="数字越小越靠前；职员端「fanbox投稿作品统计」按此顺序展示。",
                        verbose_name="排序",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
            ],
            options={
                "verbose_name": "fanbox投稿作品统计页面",
                "verbose_name_plural": "fanbox投稿作品统计页面",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_default_fanbox, unseed_default_fanbox),
    ]
