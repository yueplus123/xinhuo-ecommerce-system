from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0028_ledger_settlement_time_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffBaseSalaryLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_salary", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="基本工资")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="录入时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="base_salary_logs_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="录入人",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="base_salary_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "基本工资录入记录",
                "verbose_name_plural": "基本工资录入记录",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
