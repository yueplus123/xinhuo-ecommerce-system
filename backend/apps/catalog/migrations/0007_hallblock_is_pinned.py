from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_renewalreminder_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="hallblock",
            name="is_pinned",
            field=models.BooleanField(
                default=False,
                help_text="置顶的板块在职员端大厅最前展示，同置顶内仍按排序数字。",
                verbose_name="置顶",
            ),
        ),
    ]
