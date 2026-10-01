# 收款记录：填写日期/提交时间使用可调用默认值（避免迁移时固化成某一天）

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0021_subscription_reminder_remark"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentrecord",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name="提交时间"),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="record_date",
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name="填写日期"),
        ),
    ]
