from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_hallblock_linkcategory_paymenttutorial_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="Link"),
        migrations.DeleteModel(name="LinkCategory"),
    ]
