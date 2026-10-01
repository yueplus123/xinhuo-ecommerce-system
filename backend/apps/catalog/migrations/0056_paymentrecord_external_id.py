from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0055_staffloginmeta_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentrecord",
            name="external_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=128,
                null=True,
                unique=True,
                verbose_name="外部事件ID",
            ),
        ),
    ]
