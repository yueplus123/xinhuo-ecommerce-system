from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0040_paymentbatchsubmitkey"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffLoginLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip", models.CharField(blank=True, default="", max_length=64, verbose_name="登录 IP")),
                ("logged_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="登录时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="login_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "职员登录日志",
                "verbose_name_plural": "职员登录日志",
                "ordering": ["-logged_at", "-id"],
            },
        ),
    ]
