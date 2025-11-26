from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main_app", "0011_staff_semesters_and_seed_data"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="feepayment",
            name="uniq_fee_by_student_session",
        ),
    ]