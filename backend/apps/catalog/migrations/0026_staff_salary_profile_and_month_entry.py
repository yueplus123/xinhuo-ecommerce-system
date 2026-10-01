import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0025_ensure_ceo_group"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffSalaryProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "base_salary",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="底薪"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salary_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "职员工资档案",
                "verbose_name_plural": "职员工资档案",
            },
        ),
        migrations.CreateModel(
            name="StaffSalaryMonthEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(verbose_name="年")),
                ("month", models.PositiveSmallIntegerField(verbose_name="月")),
                (
                    "yinli_sales_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="用于按 0.1% 计算引力币提成。",
                        max_digits=14,
                        verbose_name="引力币销售额（手动）",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salary_month_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "月工资核算录入",
                "verbose_name_plural": "月工资核算录入",
            },
        ),
        migrations.AddConstraint(
            model_name="staffsalarymonthentry",
            constraint=models.UniqueConstraint(fields=("user", "year", "month"), name="uniq_staff_salary_month"),
        ),
    ]
