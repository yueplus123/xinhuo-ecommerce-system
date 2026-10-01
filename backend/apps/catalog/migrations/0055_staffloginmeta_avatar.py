from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0054_payment_channel_bilibili"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffloginmeta",
            name="avatar",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="avatars/%Y/%m/",
                verbose_name="头像",
            ),
        ),
    ]
