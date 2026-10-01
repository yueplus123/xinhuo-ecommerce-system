from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0038_salaryslipsharetoken_multi_link"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentrecord",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name="填写时间"),
        ),
        migrations.AlterField(
            model_name="paymentrecord",
            name="record_date",
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name="订单时间"),
        ),
    ]
