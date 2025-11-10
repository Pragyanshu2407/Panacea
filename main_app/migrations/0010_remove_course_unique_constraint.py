from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main_app", "0009_section_semester_and_fields"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="timetableentry",
            name="uniq_course_slot",
        ),
    ]