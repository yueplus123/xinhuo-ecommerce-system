from django.db import migrations, models


def forwards_fill_sort_order(apps, schema_editor):
    PaymentTutorial = apps.get_model("catalog", "PaymentTutorial")
    for i, o in enumerate(PaymentTutorial.objects.order_by("id")):
        o.sort_order = i
        o.save(update_fields=["sort_order"])
    PlatformAccount = apps.get_model("catalog", "PlatformAccount")
    for i, o in enumerate(PlatformAccount.objects.order_by("id")):
        o.sort_order = i
        o.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_platform_sort_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttutorial",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="数字越小越靠前；职员端支付教程列表按此顺序展示。",
                verbose_name="排序",
            ),
        ),
        migrations.AddField(
            model_name="platformaccount",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="数字越小越靠前；职员端平台账号密码表按此顺序展示。",
                verbose_name="排序",
            ),
        ),
        migrations.RunPython(forwards_fill_sort_order, migrations.RunPython.noop),
    ]
