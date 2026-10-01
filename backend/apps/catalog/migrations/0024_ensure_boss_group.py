from django.db import migrations

BOSS_GROUP_NAME = "老板"


def create_boss_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=BOSS_GROUP_NAME)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0022_alter_paymentrecord_timestamps"),
        ("catalog", "0023_paymentrecord_date_defaults"),
    ]

    operations = [
        migrations.RunPython(create_boss_group, noop_reverse),
    ]
