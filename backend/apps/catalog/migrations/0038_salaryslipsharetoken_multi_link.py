from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0037_salaryslipsharetoken_submitted_at"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="salaryslipsharetoken",
            name="uniq_salary_slip_share_month",
        ),
        migrations.AddIndex(
            model_name="salaryslipsharetoken",
            index=models.Index(fields=["user", "year", "month"], name="salary_slip_share_user_month"),
        ),
    ]
