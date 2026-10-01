from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0033_staffsalarymonthentry_social_insurance"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffsalarymonthentry",
            name="refund_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="退款项金额（手动）",
            ),
        ),
    ]
