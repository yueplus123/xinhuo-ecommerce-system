# Generated manually for subscription platform FK + reminder datetime

import django.db.models.deletion
from datetime import datetime, time
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone as dj_tz


def forwards_migrate_reminders(apps, schema_editor):
    Opt = apps.get_model("catalog", "SubscriptionPlatformOption")
    Rem = apps.get_model("catalog", "SubscriptionReminder")
    tz = dj_tz.get_current_timezone()
    names = set(
        (n or "").strip()
        for n in Rem.objects.values_list("subscription_platform", flat=True).distinct()
        if (n or "").strip()
    )
    for name in names:
        Opt.objects.get_or_create(name=name, defaults={"sort_order": 0})
    if not names:
        Opt.objects.get_or_create(name="未分类", defaults={"sort_order": 999})
    for r in Rem.objects.all():
        pname = (getattr(r, "subscription_platform", None) or "").strip() or "未分类"
        opt = Opt.objects.filter(name=pname).first()
        if opt is None:
            opt = Opt.objects.create(name=pname, sort_order=0)
        d = r.next_reminder_date
        naive = datetime.combine(d, time(9, 0))
        aware = dj_tz.make_aware(naive, tz)
        r.platform_option_id = opt.pk
        r.next_reminder_at = aware
        r.save(update_fields=["platform_option", "next_reminder_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0016_subscription_reminder"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlatformOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="平台名称")),
                ("sort_order", models.PositiveIntegerField(default=0, help_text="数字越小越靠前。", verbose_name="排序")),
            ],
            options={
                "verbose_name": "订阅平台选项",
                "verbose_name_plural": "订阅平台选项",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddField(
            model_name="subscriptionreminder",
            name="platform_option",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subscription_reminders",
                to="catalog.subscriptionplatformoption",
                verbose_name="订阅平台",
            ),
        ),
        migrations.AddField(
            model_name="subscriptionreminder",
            name="next_reminder_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="下次提醒时间"),
        ),
        migrations.RunPython(forwards_migrate_reminders, noop_reverse),
        migrations.RemoveField(
            model_name="subscriptionreminder",
            name="next_reminder_date",
        ),
        migrations.RemoveField(
            model_name="subscriptionreminder",
            name="subscription_platform",
        ),
        migrations.AlterField(
            model_name="subscriptionreminder",
            name="next_reminder_at",
            field=models.DateTimeField(
                help_text="年月日时分，24 小时制。",
                verbose_name="下次提醒时间",
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionreminder",
            name="platform_option",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subscription_reminders",
                to="catalog.subscriptionplatformoption",
                verbose_name="订阅平台",
            ),
        ),
        migrations.AlterModelOptions(
            name="subscriptionreminder",
            options={
                "ordering": ["next_reminder_at", "id"],
                "verbose_name": "订阅到期提醒",
                "verbose_name_plural": "订阅到期提醒",
            },
        ),
    ]
