from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0029_staffbasesalarylog"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffsalaryprofile",
            name="yinli_separate",
            field=models.BooleanField(
                default=False,
                help_text="勾选后工资条可填引力币销售额，并按下方比例提成。",
                verbose_name="引力币单独核算",
            ),
        ),
        migrations.AddField(
            model_name="staffsalaryprofile",
            name="yinli_commission_rate_percent",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="如 10 表示按引力币销售额的 10% 提成；不单独核算时可留空。",
                max_digits=5,
                null=True,
                verbose_name="引力币提成比例（%）",
            ),
        ),
        migrations.AddField(
            model_name="staffbasesalarylog",
            name="yinli_separate",
            field=models.BooleanField(default=False, verbose_name="引力币单独核算"),
        ),
        migrations.AddField(
            model_name="staffbasesalarylog",
            name="yinli_commission_rate_percent",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="引力币提成比例（%）",
            ),
        ),
    ]
