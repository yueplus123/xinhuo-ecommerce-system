"""记账记录：对齐微信机器人字段（提交人/群/状态/单号）。"""

from django.db import migrations, models


def backfill_ledger_status(apps, schema_editor):
    LedgerRecord = apps.get_model("catalog", "LedgerRecord")
    for row in LedgerRecord.objects.all().iterator():
        updates = []
        if not row.record_no and row.record_at:
            row.record_no = str(row.record_at)[:64]
            updates.append("record_no")
        if row.settled_at:
            if row.status != "PROCESSED":
                row.status = "PROCESSED"
                updates.append("status")
        elif not row.status:
            row.status = "ACTIVE"
            updates.append("status")
        if updates:
            row.save(update_fields=updates)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0057_wechatbotrecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="ledgerrecord",
            name="record_no",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="ledgerrecord",
            name="external_id",
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="ledgerrecord",
            name="employee_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="ledgerrecord",
            name="chat_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="ledgerrecord",
            name="status",
            field=models.CharField(
                choices=[("ACTIVE", "未清账"), ("PROCESSED", "已清账"), ("REVERSED", "已撤销")],
                db_index=True,
                default="ACTIVE",
                max_length=16,
            ),
        ),
        migrations.RunPython(backfill_ledger_status, migrations.RunPython.noop),
    ]
