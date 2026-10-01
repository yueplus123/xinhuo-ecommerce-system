# Generated manually for WechatBotRecord

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0056_paymentrecord_external_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="WechatBotRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "table_type",
                    models.CharField(
                        choices=[
                            ("pixivcoban", "pixivcoban 充币表"),
                            ("usdt", "USDT 充值表"),
                            ("chatgpt", "ChatGPT 代充表"),
                        ],
                        db_index=True,
                        max_length=32,
                        verbose_name="所属表",
                    ),
                ),
                ("external_id", models.CharField(db_index=True, max_length=128, unique=True, verbose_name="外部事件ID")),
                ("record_no", models.CharField(blank=True, default="", max_length=64, verbose_name="机器人流水号")),
                ("book", models.CharField(blank=True, default="", max_length=32, verbose_name="机器人账本")),
                ("direction", models.CharField(blank=True, default="", max_length=16, verbose_name="收支")),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name="金额")),
                ("currency", models.CharField(blank=True, default="CNY", max_length=8, verbose_name="币种")),
                ("business_name", models.CharField(blank=True, default="", max_length=128, verbose_name="业务名")),
                ("amount_to_you", models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name="给你")),
                ("amount_to_me", models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name="给我")),
                ("profit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name="利润")),
                ("employee_name", models.CharField(blank=True, default="", max_length=128, verbose_name="员工")),
                ("chat_name", models.CharField(blank=True, default="", max_length=128, verbose_name="群名")),
                ("raw_text", models.CharField(blank=True, default="", max_length=500, verbose_name="原始消息")),
                ("remark", models.CharField(blank=True, default="", max_length=200, verbose_name="备注")),
                ("status", models.CharField(blank=True, default="ACTIVE", max_length=16, verbose_name="状态")),
                ("occurred_at", models.DateTimeField(blank=True, null=True, verbose_name="业务时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="入库时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "微信BOT记录",
                "verbose_name_plural": "微信BOT记录",
                "ordering": ["-occurred_at", "-id"],
                "indexes": [
                    models.Index(fields=["table_type", "-occurred_at"], name="catalog_wec_table_t_8c1a1a_idx"),
                    models.Index(fields=["table_type", "status"], name="catalog_wec_table_t_2b9f0c_idx"),
                ],
            },
        ),
    ]
