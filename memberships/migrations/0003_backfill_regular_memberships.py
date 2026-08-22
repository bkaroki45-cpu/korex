from decimal import Decimal

from django.db import migrations


def normalize_memberships(apps, schema_editor):
    Membership = apps.get_model("memberships", "Membership")
    Membership.objects.filter(membership_type="BASIC").update(membership_type="REGULAR", daily_sessions=2, earning_rate=Decimal("0.0200"))
    Membership.objects.filter(membership_type="TEAM").update(membership_type="TEAM_LEADER", daily_sessions=3, earning_rate=Decimal("0.0300"))


class Migration(migrations.Migration):
    dependencies = [("memberships", "0002_membership_earning_rate_and_more")]
    operations = [migrations.RunPython(normalize_memberships, migrations.RunPython.noop)]
