from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0032_staffsalarymonthentry_manual_sales"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffsalarymonthentry",
            name="social_insurance_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=14,
                verbose_name="社保金额（手动）",
            ),
        ),
    ]
