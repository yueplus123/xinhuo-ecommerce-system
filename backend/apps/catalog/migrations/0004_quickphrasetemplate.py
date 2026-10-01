from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_remove_linkcategory_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuickPhraseTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="名称")),
                ("content", models.TextField(verbose_name="内容")),
            ],
            options={
                "ordering": ["id"],
                "unique_together": {("name", "content")},
            },
        ),
    ]

