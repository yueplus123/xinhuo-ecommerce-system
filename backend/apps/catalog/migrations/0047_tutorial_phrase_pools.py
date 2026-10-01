from django.db import migrations, models


def backfill_phrase_pool_sort_order(apps, schema_editor):
    PhrasePool = apps.get_model("catalog", "PhrasePool")
    for idx, row in enumerate(PhrasePool.objects.all().order_by("id")):
        if row.sort_order == 0:
            PhrasePool.objects.filter(pk=row.pk).update(sort_order=(idx + 1) * 10)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0046_sku_member_images"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="TutorialDeployTemplate",
            new_name="TutorialPool",
        ),
        migrations.RenameModel(
            old_name="QuickPhraseTemplate",
            new_name="PhrasePool",
        ),
        migrations.AlterModelOptions(
            name="tutorialpool",
            options={
                "ordering": ["sort_order", "id"],
                "verbose_name": "教程池",
                "verbose_name_plural": "教程池",
            },
        ),
        migrations.AlterModelOptions(
            name="phrasepool",
            options={
                "ordering": ["sort_order", "id"],
                "verbose_name": "话术池",
                "verbose_name_plural": "话术池",
            },
        ),
        migrations.AlterField(
            model_name="tutorialpool",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="数字越小越靠前。",
                verbose_name="排序",
            ),
        ),
        migrations.AddField(
            model_name="phrasepool",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="数字越小越靠前。",
                verbose_name="排序",
            ),
        ),
        migrations.RunPython(backfill_phrase_pool_sort_order, migrations.RunPython.noop),
    ]
