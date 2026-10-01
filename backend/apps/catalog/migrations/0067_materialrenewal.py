from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0066_wallospage"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialRenewal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="物料名称")),
                ("category", models.CharField(blank=True, default="", max_length=100, verbose_name="分类")),
                (
                    "amount",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="费用"),
                ),
                ("currency", models.CharField(blank=True, default="CNY", max_length=8, verbose_name="币种")),
                (
                    "cycle_type",
                    models.CharField(
                        choices=[("monthly", "每月"), ("yearly", "每年"), ("days", "自定义天数")],
                        default="yearly",
                        max_length=16,
                        verbose_name="续费周期",
                    ),
                ),
                (
                    "cycle_days",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="仅「自定义天数」时填写。",
                        null=True,
                        verbose_name="周期天数",
                    ),
                ),
                ("next_due_at", models.DateField(verbose_name="下次到期日")),
                ("last_renewed_at", models.DateTimeField(blank=True, null=True, verbose_name="上次续费登记时间")),
                ("remark", models.CharField(blank=True, default="", max_length=500, verbose_name="备注")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "物料续费",
                "verbose_name_plural": "物料续费",
                "ordering": ["next_due_at", "id"],
            },
        ),
    ]
