from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0027_ledger_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="LedgerSettlementTimeLog",
            fields=[
                ("id", models.CharField(max_length=36, primary_key=True, serialize=False)),
                ("settled_at", models.CharField(db_index=True, max_length=64)),
            ],
            options={
                "verbose_name": "清账时间记录",
                "verbose_name_plural": "清账时间记录",
                "ordering": ["-settled_at", "-id"],
            },
        ),
    ]
