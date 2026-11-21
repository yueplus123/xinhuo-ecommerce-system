import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0082_card_manager_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CardRiskHandled",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.CharField(max_length=64, verbose_name="汇通卡ID")),
                ("risk", models.CharField(max_length=20, verbose_name="风险类型")),
                ("mark", models.CharField(blank=True, default="", max_length=64, verbose_name="处理时的触发点")),
                (
                    "result",
                    models.CharField(
                        choices=[("ok", "没问题"), ("locked", "已锁卡"), ("cancelled", "已销卡"), ("other", "其他")],
                        default="ok",
                        max_length=20,
                        verbose_name="处理结果",
                    ),
                ),
                ("note", models.CharField(blank=True, default="", max_length=200, verbose_name="备注")),
                ("card_suffix", models.CharField(blank=True, default="", max_length=8, verbose_name="卡号后4位")),
                ("card_remark", models.CharField(blank=True, default="", max_length=255, verbose_name="卡片备注")),
                ("handled_at", models.DateTimeField(auto_now=True, verbose_name="处理时间")),
                (
                    "handled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="处理人",
                    ),
                ),
            ],
            options={
                "verbose_name": "卡管家风险处理记录",
                "verbose_name_plural": "卡管家风险处理记录",
                "indexes": [models.Index(fields=["handled_at"], name="card_risk_handled_at")],
                "constraints": [models.UniqueConstraint(fields=("card_id", "risk"), name="uniq_card_risk_handled")],
            },
        ),
    ]
