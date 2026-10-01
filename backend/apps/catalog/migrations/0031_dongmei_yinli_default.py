from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import migrations


def enable_yinli_for_dongmei(apps, schema_editor):
    User = get_user_model()
    StaffSalaryProfile = apps.get_model("catalog", "StaffSalaryProfile")
    user = User.objects.filter(username="冬梅", is_staff=True).first()
    if not user:
        return
    profile, _ = StaffSalaryProfile.objects.get_or_create(user_id=user.pk, defaults={"base_salary": 0})
    if not profile.yinli_separate:
        profile.yinli_separate = True
        profile.yinli_commission_rate_percent = Decimal("0.10")
        profile.save(update_fields=["yinli_separate", "yinli_commission_rate_percent"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0030_yinli_separate_commission"),
    ]

    operations = [
        migrations.RunPython(enable_yinli_for_dongmei, migrations.RunPython.noop),
    ]
