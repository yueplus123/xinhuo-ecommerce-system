import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0083_card_risk_handled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CardOtpLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.CharField(db_index=True, max_length=64, verbose_name="汇通卡ID")),
                ("token", models.CharField(max_length=48, unique=True, verbose_name="链接密钥")),
                ("card_bin", models.CharField(blank=True, default="", max_length=8, verbose_name="卡号前6位")),
                ("card_suffix", models.CharField(blank=True, default="", max_length=8, verbose_name="卡号后4位")),
                ("card_remark", models.CharField(blank=True, default="", max_length=255, verbose_name="卡片备注")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="生成时间")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="作废时间")),
                ("view_count", models.PositiveIntegerField(default=0, verbose_name="打开次数")),
                ("last_view_at", models.DateTimeField(blank=True, null=True, verbose_name="最后打开时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="生成人",
                    ),
                ),
            ],
            options={"verbose_name": "卡管家接码链接", "verbose_name_plural": "卡管家接码链接"},
        ),
        migrations.CreateModel(
            name="CardOtpCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.CharField(db_index=True, max_length=64, verbose_name="汇通卡ID")),
                ("payment_no", models.CharField(max_length=64, unique=True, verbose_name="汇通交易号")),
                ("code", models.CharField(max_length=12, verbose_name="验证码")),
                ("trans_at", models.DateTimeField(db_index=True, verbose_name="交易时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="上传时间")),
            ],
            options={"verbose_name": "卡管家验证码", "verbose_name_plural": "卡管家验证码"},
        ),
    ]
