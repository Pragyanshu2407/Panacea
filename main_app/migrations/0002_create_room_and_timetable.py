from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main_app", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=
            """
            CREATE TABLE IF NOT EXISTS "main_app_room" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "name" varchar(64) NOT NULL UNIQUE,
                "capacity" integer NOT NULL DEFAULT 0
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS main_app_room;",
        ),
        migrations.RunSQL(
            sql=
            """
            CREATE TABLE IF NOT EXISTS "main_app_timetableentry" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "day" varchar(3) NOT NULL,
                "period_number" smallint NOT NULL,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL,
                "course_id" integer NOT NULL REFERENCES "main_app_course" ("id"),
                "room_id" integer NOT NULL REFERENCES "main_app_room" ("id"),
                "session_id" integer NOT NULL REFERENCES "main_app_session" ("id"),
                "staff_id" integer NOT NULL REFERENCES "main_app_staff" ("id"),
                "subject_id" integer NOT NULL REFERENCES "main_app_subject" ("id"),
                UNIQUE ("session_id", "day", "period_number", "staff_id"),
                UNIQUE ("session_id", "day", "period_number", "room_id"),
                UNIQUE ("session_id", "day", "period_number", "course_id")
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS main_app_timetableentry;",
        ),
    ]