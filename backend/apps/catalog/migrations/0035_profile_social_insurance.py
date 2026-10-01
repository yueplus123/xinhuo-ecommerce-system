from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0034_staffsalarymonthentry_refund_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffsalaryprofile",
            name="has_social_insurance",
            field=models.BooleanField(default=False, verbose_name="是否有社保"),
        ),
        migrations.AddField(
            model_name="staffsalaryprofile",
            name="social_insurance_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="社保金额"),
        ),
        migrations.AddField(
            model_name="staffbasesalarylog",
            name="has_social_insurance",
            field=models.BooleanField(default=False, verbose_name="是否有社保"),
        ),
        migrations.AddField(
            model_name="staffbasesalarylog",
            name="social_insurance_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="社保金额"),
        ),
    ]
