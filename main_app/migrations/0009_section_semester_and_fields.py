from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main_app", "0008_subject_courses_m2m"),
    ]

    operations = [
        migrations.CreateModel(
            name="Semester",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveSmallIntegerField()),
                ("label", models.CharField(blank=True, max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="Section",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sections", to="main_app.course")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=["course", "name"], name="uniq_course_section_name"),
                ],
            },
        ),
        migrations.AddField(
            model_name="student",
            name="section",
            field=models.ForeignKey(null=True, blank=True, on_delete=models.deletion.DO_NOTHING, to="main_app.section"),
        ),
        migrations.AddField(
            model_name="student",
            name="semester",
            field=models.ForeignKey(null=True, blank=True, on_delete=models.deletion.DO_NOTHING, to="main_app.semester"),
        ),
        migrations.AddField(
            model_name="staff",
            name="sections",
            field=models.ManyToManyField(blank=True, related_name="staff", to="main_app.section"),
        ),
        migrations.AddField(
            model_name="subject",
            name="sections",
            field=models.ManyToManyField(blank=True, related_name="subjects", to="main_app.section"),
        ),
        migrations.AddField(
            model_name="subject",
            name="semester",
            field=models.ForeignKey(null=True, blank=True, on_delete=models.deletion.DO_NOTHING, to="main_app.semester"),
        ),
        migrations.AddField(
            model_name="timetableentry",
            name="section",
            field=models.ForeignKey(null=True, blank=True, on_delete=models.deletion.CASCADE, to="main_app.section"),
        ),
        migrations.AddConstraint(
            model_name="timetableentry",
            constraint=models.UniqueConstraint(fields=("session", "day", "period_number", "section"), name="uniq_section_slot"),
        ),
    ]