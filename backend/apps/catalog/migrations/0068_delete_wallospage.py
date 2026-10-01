from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0067_materialrenewal"),
    ]

    operations = [
        migrations.DeleteModel(name="WallosPage"),
    ]
