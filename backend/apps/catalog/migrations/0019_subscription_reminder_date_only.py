# 订阅提醒「下次提醒」改为仅日期（去掉时分）

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0018_subscription_reminder_wecom_notify"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriptionreminder",
            name="next_reminder_at",
            field=models.DateField(
                help_text="只需年月日；到该日当天起视为需要跟进。",
                verbose_name="下次提醒日期",
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionreminderwecomnotify",
            name="next_reminder_at",
            field=models.DateField(db_index=True, verbose_name="对应的下次提醒日期"),
        ),
    ]
