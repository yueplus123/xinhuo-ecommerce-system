from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0039_paymentrecord_time_labels"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentBatchSubmitKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_id", models.CharField(max_length=64, verbose_name="提交批次 ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_batch_submit_keys",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="职员",
                    ),
                ),
            ],
            options={
                "verbose_name": "收款批量提交幂等键",
                "verbose_name_plural": "收款批量提交幂等键",
            },
        ),
        migrations.AddConstraint(
            model_name="paymentbatchsubmitkey",
            constraint=models.UniqueConstraint(fields=("user", "batch_id"), name="uniq_payment_batch_submit_key"),
        ),
    ]
