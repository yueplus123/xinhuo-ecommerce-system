from django.db import migrations

GUEST_GROUP_NAME = "游客"


def create_guest_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GUEST_GROUP_NAME)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0060_remove_ceo_maintenance_logs"),
    ]

    operations = [
        migrations.RunPython(create_guest_group, noop_reverse),
    ]
