from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0059_remove_ledger_usdt_and_settlement_time"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CeoInspectionMaintenanceLog",
        ),
        migrations.DeleteModel(
            name="CeoWebsiteMaintenanceLog",
        ),
    ]
