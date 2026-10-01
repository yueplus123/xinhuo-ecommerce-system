from django.db import migrations

CEO_GROUP_NAME = "CEO"


def create_ceo_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=CEO_GROUP_NAME)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0024_ensure_boss_group"),
    ]

    operations = [
        migrations.RunPython(create_ceo_group, noop_reverse),
    ]
