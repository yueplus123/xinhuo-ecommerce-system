from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0036_salaryslipsharetoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="salaryslipsharetoken",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="员工提交时间"),
        ),
    ]
