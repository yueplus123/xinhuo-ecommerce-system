# Generated manually for 企业微信群 Webhook 推送去重

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0017_subscription_platform_option_and_reminder_datetime"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionReminderWecomNotify",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("next_reminder_at", models.DateTimeField(db_index=True, verbose_name="对应的下次提醒时间")),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="推送时间")),
                (
                    "reminder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wecom_notifies",
                        to="catalog.subscriptionreminder",
                        verbose_name="订阅提醒",
                    ),
                ),
            ],
            options={
                "verbose_name": "订阅提醒企微群推送记录",
                "verbose_name_plural": "订阅提醒企微群推送记录",
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionreminderwecomnotify",
            constraint=models.UniqueConstraint(
                fields=("reminder", "next_reminder_at"),
                name="catalog_subrem_wecom_once_per_next_at",
            ),
        ),
    ]
