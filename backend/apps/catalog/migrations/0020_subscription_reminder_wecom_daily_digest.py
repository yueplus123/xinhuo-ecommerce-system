# Generated manually: 订阅提醒企微「按职员每日汇总」去重

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0019_subscription_reminder_date_only"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionReminderWecomDailyDigest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("digest_date", models.DateField(db_index=True, verbose_name="汇总日期")),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="推送时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription_wecom_daily_digests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "订阅提醒企微每日汇总",
                "verbose_name_plural": "订阅提醒企微每日汇总",
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionreminderwecomdailydigest",
            constraint=models.UniqueConstraint(
                fields=("user", "digest_date"),
                name="catalog_subrem_wecom_daily_once_per_user_date",
            ),
        ),
    ]
