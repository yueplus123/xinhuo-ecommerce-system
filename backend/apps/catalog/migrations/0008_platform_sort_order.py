from django.db import migrations, models


def forwards_fill_platform_sort_order(apps, schema_editor):
    Platform = apps.get_model("catalog", "Platform")
    for i, p in enumerate(Platform.objects.order_by("id")):
        p.sort_order = i
        p.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_hallblock_is_pinned"),
    ]

    operations = [
        migrations.AddField(
            model_name="platform",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="数字越小越靠前；职员端平台列表按此顺序展示。",
                verbose_name="排序",
            ),
        ),
        migrations.RunPython(forwards_fill_platform_sort_order, migrations.RunPython.noop),
    ]
