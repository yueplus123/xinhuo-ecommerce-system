from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0041_staffloginlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="CeoWebsiteMaintenanceLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="维护项")),
                ("note", models.TextField(blank=True, default="", verbose_name="说明")),
                ("record_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="维护日期")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ceo_website_maintenance_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="记录人",
                    ),
                ),
            ],
            options={
                "verbose_name": "CEO网站维护记录",
                "verbose_name_plural": "CEO网站维护记录",
                "ordering": ["-record_date", "-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="CeoInspectionMaintenanceLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="检查项")),
                ("note", models.TextField(blank=True, default="", verbose_name="说明/结果")),
                ("record_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="检查日期")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ceo_inspection_maintenance_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="记录人",
                    ),
                ),
            ],
            options={
                "verbose_name": "CEO检查维护记录",
                "verbose_name_plural": "CEO检查维护记录",
                "ordering": ["-record_date", "-created_at", "-id"],
            },
        ),
    ]
