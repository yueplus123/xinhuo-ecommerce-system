from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0047_tutorial_phrase_pools"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformTagPool",
            fields=[],
            options={
                "verbose_name": "平台标签",
                "verbose_name_plural": "标签池",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("catalog.tag",),
        ),
        migrations.CreateModel(
            name="ChannelTagPool",
            fields=[],
            options={
                "verbose_name": "渠道标签",
                "verbose_name_plural": "渠道池",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("catalog.tag",),
        ),
        migrations.AlterField(
            model_name="tag",
            name="order",
            field=models.PositiveIntegerField(default=0, verbose_name="排序"),
        ),
    ]
