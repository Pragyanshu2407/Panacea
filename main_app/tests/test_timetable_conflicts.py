from django.test import TestCase
from django.core.exceptions import ValidationError

from django.core.files.uploadedfile import SimpleUploadedFile
from main_app.models import (
    Session,
    Course,
    Section,
    Semester,
    CustomUser,
    Staff,
    Subject,
    Room,
    TimetableEntry,
    StaffUnavailability,
)


class TimetableConflictTests(TestCase):
    def setUp(self):
        self.session = Session.objects.create(start_year="2024-01-01", end_year="2025-01-01")
        self.course = Course.objects.create(name="CSE")
        self.sem = Semester.objects.create(number=5, label="Semester 5")
        self.sec_b = Section.objects.create(course=self.course, name="B")
        self.sec_c = Section.objects.create(course=self.course, name="C")
        # Create a CustomUser for staff (signals will create Staff)
        pic = SimpleUploadedFile("pic.jpg", b"filecontent", content_type="image/jpeg")
        admin_user = CustomUser.objects.create_user(
            email="staff@example.com",
            password="pass",
            user_type=2,  # Staff
            gender="M",
            address="Test",
            profile_pic=pic,
        )
        self.staff = admin_user.staff
        # Assign course to staff for consistency
        self.staff.course = self.course
        self.staff.save()
        self.room1 = Room.objects.create(name="R1", capacity=30)
        self.room2 = Room.objects.create(name="R2", capacity=30)
        self.sub1 = Subject.objects.create(name="Algo", staff=self.staff, semester=self.sem, credits=3)
        self.sub2 = Subject.objects.create(name="DBMS", staff=self.staff, semester=self.sem, credits=3)
        self.sub1.courses.add(self.course)
        self.sub2.courses.add(self.course)
        self.sub1.sections.add(self.sec_b, self.sec_c)
        self.sub2.sections.add(self.sec_b, self.sec_c)

    def test_section_uniqueness_same_slot(self):
        e1 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub1,
            staff=self.staff,
            room=self.room1,
            day="Mon",
            period_number=2,
            is_lab=False,
            duration_periods=1,
        )
        e1.full_clean()
        e1.save()

        e2 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub2,
            staff=self.staff,
            room=self.room2,
            day="Mon",
            period_number=2,
            is_lab=False,
            duration_periods=1,
        )
        with self.assertRaises(ValidationError):
            e2.full_clean()

    def test_teacher_conflict_across_sections(self):
        e1 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub1,
            staff=self.staff,
            room=self.room1,
            day="Tue",
            period_number=3,
            is_lab=False,
            duration_periods=1,
        )
        e1.full_clean()
        e1.save()

        e2 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_c,
            subject=self.sub2,
            staff=self.staff,
            room=self.room2,
            day="Tue",
            period_number=3,
            is_lab=False,
            duration_periods=1,
        )
        with self.assertRaises(ValidationError):
            e2.full_clean()

    def test_teacher_unavailability_blocks_slot(self):
        StaffUnavailability.objects.create(
            staff=self.staff,
            session=self.session,
            day="Wed",
            period_number=1,
            duration_periods=1,
            reason="Busy",
        )
        e = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub1,
            staff=self.staff,
            room=self.room1,
            day="Wed",
            period_number=1,
            is_lab=False,
            duration_periods=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            e.full_clean()
        self.assertIn("unavailable", str(ctx.exception).lower())

    def test_suggestions_present_on_conflict(self):
        # Create a conflicting entry for staff
        e1 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub1,
            staff=self.staff,
            room=self.room1,
            day="Thu",
            period_number=2,
            is_lab=False,
            duration_periods=1,
        )
        e1.full_clean()
        e1.save()

        e2 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_c,
            subject=self.sub2,
            staff=self.staff,
            room=self.room2,
            day="Thu",
            period_number=2,
            is_lab=False,
            duration_periods=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            e2.full_clean()
        self.assertIn("Suggested alternatives", str(ctx.exception))

    def test_credits_cap_per_section(self):
        # Add 3 entries for 3-credit subject in one section
        for day, period in [("Mon", 1), ("Tue", 2), ("Wed", 3)]:
            e = TimetableEntry(
                session=self.session,
                course=self.course,
                section=self.sec_b,
                subject=self.sub1,
                staff=self.staff,
                room=self.room1,
                day=day,
                period_number=period,
                is_lab=False,
                duration_periods=1,
            )
            e.full_clean()
            e.save()

        # 4th should fail due to credits cap
        e4 = TimetableEntry(
            session=self.session,
            course=self.course,
            section=self.sec_b,
            subject=self.sub1,
            staff=self.staff,
            room=self.room2,
            day="Thu",
            period_number=2,
            is_lab=False,
            duration_periods=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            e4.full_clean()
        self.assertIn("Weekly credits limit", str(ctx.exception))