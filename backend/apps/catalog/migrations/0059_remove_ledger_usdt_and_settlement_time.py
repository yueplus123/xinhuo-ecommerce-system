from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0058_ledger_record_bot_fields"),
    ]

    operations = [
        migrations.DeleteModel(
            name="LedgerSettlementTimeLog",
        ),
        migrations.DeleteModel(
            name="LedgerUsdtRecord",
        ),
    ]
