from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0031_dongmei_yinli_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffsalarymonthentry",
            name="shilei_sales_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="十类销售额（手动）",
            ),
        ),
        migrations.AddField(
            model_name="staffsalarymonthentry",
            name="tier2_sales_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="二类销售额（手动）",
            ),
        ),
        migrations.AlterField(
            model_name="staffsalarymonthentry",
            name="yinli_sales_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="用于按配置比例计算引力币提成。",
                max_digits=14,
                verbose_name="引力币销售额（手动）",
            ),
        ),
    ]
