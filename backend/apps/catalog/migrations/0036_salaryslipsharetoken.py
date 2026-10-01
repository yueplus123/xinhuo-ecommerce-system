from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0035_profile_social_insurance"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalarySlipShareToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(verbose_name="年")),
                ("month", models.PositiveSmallIntegerField(verbose_name="月")),
                ("token", models.CharField(db_index=True, max_length=64, unique=True, verbose_name="分享令牌")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salary_slip_share_tokens",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "工资条分享链接",
                "verbose_name_plural": "工资条分享链接",
            },
        ),
        migrations.AddConstraint(
            model_name="salaryslipsharetoken",
            constraint=models.UniqueConstraint(fields=("user", "year", "month"), name="uniq_salary_slip_share_month"),
        ),
    ]
