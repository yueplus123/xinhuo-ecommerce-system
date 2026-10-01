# 订阅到期提醒增加选填「备注」

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0020_subscription_reminder_wecom_daily_digest"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionreminder",
            name="remark",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="备注"),
        ),
    ]
