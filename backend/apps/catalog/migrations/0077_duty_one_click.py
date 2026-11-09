"""值班打卡改为一键打卡：所有事务不再要求填数量、勾清单、传截图。"""

from django.db import migrations, models


def to_one_click(apps, schema_editor):
    DutyTask = apps.get_model("catalog", "DutyTask")
    DutyTask.objects.update(qty_enabled=False, qty_required=False, target_mode="none", checklist=[], image_mode="none")


class Migration(migrations.Migration):
    dependencies = [("catalog", "0076_duty_tasks")]

    operations = [
        migrations.AlterField(
            model_name="dutytask",
            name="image_mode",
            field=models.CharField(
                choices=[("none", "不需要"), ("optional", "可选"), ("required", "必须")],
                default="none", max_length=10, verbose_name="截图",
            ),
        ),
        migrations.RunPython(to_one_click, migrations.RunPython.noop),
    ]
