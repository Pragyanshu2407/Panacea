from django.db import migrations, models


def seed_semesters_and_sections(apps, schema_editor):
    Semester = apps.get_model('main_app', 'Semester')
    Course = apps.get_model('main_app', 'Course')
    Section = apps.get_model('main_app', 'Section')

    # Seed semesters 1..8
    for num in range(1, 9):
        Semester.objects.get_or_create(number=num, defaults={"label": f"Semester {num}"})

    # Seed sections A..D for every course
    for course in Course.objects.all():
        for name in ["A", "B", "C", "D"]:
            Section.objects.get_or_create(course=course, name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0010_remove_course_unique_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='semesters',
            field=models.ManyToManyField(blank=True, related_name='staff', to='main_app.Semester'),
        ),
        migrations.RunPython(seed_semesters_and_sections, migrations.RunPython.noop),
    ]