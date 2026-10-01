from django.db import migrations, models


def copy_payment_tutorials_to_deploy_pool(apps, schema_editor):
    PaymentTutorial = apps.get_model("catalog", "PaymentTutorial")
    TutorialDeployTemplate = apps.get_model("catalog", "TutorialDeployTemplate")
    existing_names = set(TutorialDeployTemplate.objects.values_list("name", flat=True))
    for row in PaymentTutorial.objects.all().order_by("sort_order", "id"):
        if row.name in existing_names:
            continue
        TutorialDeployTemplate.objects.create(
            name=row.name,
            detail_url=row.detail_url,
            sort_order=row.sort_order,
        )
        existing_names.add(row.name)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_sharedappleidpage"),
    ]

    operations = [
        migrations.CreateModel(
            name="TutorialDeployTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="名称")),
                ("detail_url", models.URLField(verbose_name="详情链接")),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="数字越小越靠前；教程/步骤部署管理内按此顺序展示。",
                        verbose_name="排序",
                    ),
                ),
            ],
            options={
                "verbose_name": "教程步骤模板",
                "verbose_name_plural": "教程步骤模板",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(copy_payment_tutorials_to_deploy_pool, noop_reverse),
    ]
