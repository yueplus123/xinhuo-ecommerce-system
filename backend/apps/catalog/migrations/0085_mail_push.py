import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0084_card_otp"),
    ]

    operations = [
        migrations.CreateModel(
            name="MailPushSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("webhook_url", models.CharField(blank=True, default="", max_length=300, verbose_name="企微群 Webhook")),
                ("dry_run", models.BooleanField(default=True, verbose_name="观察模式（只记录不推送）")),
                ("poll_interval", models.PositiveIntegerField(default=60, verbose_name="检查间隔（秒）")),
                ("summary_chars", models.PositiveIntegerField(default=400, verbose_name="摘要字数")),
                (
                    "exclude_senders",
                    models.TextField(blank=True, default="10000@qq.com", verbose_name="排除的发件人（一行一个）"),
                ),
                (
                    "exclude_keywords",
                    models.TextField(
                        blank=True,
                        default="退订\n促销\n广告\n优惠券\nunsubscribe\nnewsletter",
                        verbose_name="排除的标题关键词（一行一个）",
                    ),
                ),
                ("check_requested_at", models.DateTimeField(blank=True, null=True, verbose_name="请求立即检查")),
                ("worker_heartbeat_at", models.DateTimeField(blank=True, null=True, verbose_name="收信服务心跳")),
                ("last_round_at", models.DateTimeField(blank=True, null=True, verbose_name="上次检查完成")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "邮件推送设置",
                "verbose_name_plural": "邮件推送设置",
            },
        ),
        migrations.CreateModel(
            name="MailPushAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=30, unique=True, verbose_name="名称")),
                ("email", models.CharField(max_length=120, unique=True, verbose_name="邮箱地址")),
                ("auth_code", models.CharField(max_length=100, verbose_name="授权码")),
                ("enabled", models.BooleanField(default=True, verbose_name="启用")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("uidvalidity", models.BigIntegerField(blank=True, null=True, verbose_name="UIDVALIDITY")),
                ("last_uid", models.BigIntegerField(blank=True, null=True, verbose_name="已处理到的 UID")),
                ("last_check_at", models.DateTimeField(blank=True, null=True, verbose_name="上次检查")),
                ("last_ok", models.BooleanField(blank=True, null=True, verbose_name="上次检查是否成功")),
                ("last_error", models.CharField(blank=True, default="", max_length=300, verbose_name="上次错误")),
                ("fail_count", models.PositiveIntegerField(default=0, verbose_name="连续失败次数")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "邮件推送邮箱",
                "verbose_name_plural": "邮件推送邮箱",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="MailPushRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=30, verbose_name="规则名称")),
                (
                    "senders",
                    models.TextField(blank=True, default="", verbose_name="发件人（一行一个，@开头=整个域名）"),
                ),
                ("subject_keywords", models.TextField(blank=True, default="", verbose_name="标题关键词（一行一个）")),
                (
                    "style",
                    models.CharField(
                        choices=[("summary", "标题+摘要"), ("code", "只推验证码"), ("title_only", "只推标题")],
                        default="summary",
                        max_length=16,
                        verbose_name="推送样式",
                    ),
                ),
                ("enabled", models.BooleanField(default=True, verbose_name="启用")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "accounts",
                    models.ManyToManyField(
                        blank=True,
                        related_name="mail_push_rules",
                        to="catalog.mailpushaccount",
                        verbose_name="适用邮箱（不选=全部）",
                    ),
                ),
            ],
            options={
                "verbose_name": "邮件推送规则",
                "verbose_name_plural": "邮件推送规则",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="MailPushRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uidvalidity", models.BigIntegerField(verbose_name="UIDVALIDITY")),
                ("uid", models.BigIntegerField(verbose_name="UID")),
                ("sender", models.CharField(blank=True, default="", max_length=200, verbose_name="发件人")),
                ("subject", models.CharField(blank=True, default="", max_length=300, verbose_name="标题")),
                ("rule_name", models.CharField(blank=True, default="", max_length=60, verbose_name="命中规则")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pushed", "已推送"),
                            ("dry_run", "会推送"),
                            ("ignored", "未命中"),
                            ("excluded", "已排除"),
                            ("failed", "失败"),
                        ],
                        db_index=True,
                        max_length=16,
                        verbose_name="结果",
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=1, verbose_name="处理次数")),
                ("error", models.CharField(blank=True, default="", max_length=300, verbose_name="错误")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="records",
                        to="catalog.mailpushaccount",
                        verbose_name="邮箱",
                    ),
                ),
            ],
            options={
                "verbose_name": "邮件推送记录",
                "verbose_name_plural": "邮件推送记录",
                "ordering": ["-id"],
                "constraints": [
                    models.UniqueConstraint(fields=("account", "uidvalidity", "uid"), name="uniq_mail_push_record")
                ],
            },
        ),
    ]
