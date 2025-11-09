from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from datetime import datetime,timedelta




class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()

    def __str__(self):
        return "From " + str(self.start_year) + " to " + str(self.end_year)


class CustomUser(AbstractUser):
    USER_TYPE = ((1, "HOD"), (2, "Staff"), (3, "Student"))
    GENDER = [("M", "Male"), ("F", "Female")]
    
    
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField()
    fcm_token = models.TextField(default="")  # For firebase notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return  self.first_name + " " + self.last_name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



class Course(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.PositiveIntegerField()
    category = models.CharField(max_length=50)

    def __str__(self):
        return str(self.name) + " ["+str(self.isbn)+']'


class Student(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name

class Library(models.Model):
    student = models.ForeignKey(Student,  on_delete=models.CASCADE, null=True, blank=False)
    book = models.ForeignKey(Book,  on_delete=models.CASCADE, null=True, blank=False)
    def __str__(self):
        return str(self.student)

def expiry():
    return datetime.today() + timedelta(days=14)
class IssuedBook(models.Model):
    student_id = models.CharField(max_length=100, blank=True) 
    isbn = models.CharField(max_length=13)
    issued_date = models.DateField(auto_now=True)
    expiry_date = models.DateField(default=expiry)



class Staff(models.Model):
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.first_name + " " +  self.admin.last_name


class Subject(models.Model):
    name = models.CharField(max_length=120)
    staff = models.ForeignKey(Staff,on_delete=models.CASCADE,)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    credits = models.PositiveSmallIntegerField(default=0, help_text="Classes per week limit")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AttendanceReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StudentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    test = models.FloatField(default=0)
    exam = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        if instance.user_type == 2:
            Staff.objects.create(admin=instance)
        if instance.user_type == 3:
            Student.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    if instance.user_type == 2:
        instance.staff.save()
    if instance.user_type == 3:
        instance.student.save()

# Timetable proxies removed along with tablelogic integration

# Timetable models

class Room(models.Model):
    name = models.CharField(max_length=64, unique=True)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} (cap {self.capacity})"


class TimetableEntry(models.Model):
    DAY_CHOICES = [
        ("Mon", "Monday"),
        ("Tue", "Tuesday"),
        ("Wed", "Wednesday"),
        ("Thu", "Thursday"),
        ("Fri", "Friday"),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    period_number = models.PositiveSmallIntegerField()  # 1..6
    is_lab = models.BooleanField(default=False)
    duration_periods = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Prevent staff clashes in same session/day/period
            models.UniqueConstraint(
                fields=["session", "day", "period_number", "staff"],
                name="uniq_staff_slot",
            ),
            # Prevent room clashes
            models.UniqueConstraint(
                fields=["session", "day", "period_number", "room"],
                name="uniq_room_slot",
            ),
            # Prevent a course group being scheduled for multiple classes at same time
            models.UniqueConstraint(
                fields=["session", "day", "period_number", "course"],
                name="uniq_course_slot",
            ),
        ]

    SLOT_LABELS = {
        1: "9-10",
        2: "10-11",
        3: "11-12",
        4: "12-1",
        5: "1-2",
        6: "2-3",
    }

    @property
    def slot_label(self):
        return self.SLOT_LABELS.get(int(self.period_number), f"P{self.period_number}")

    def __str__(self):
        label = self.slot_label
        span = f" ({self.duration_periods}p)" if int(self.duration_periods) > 1 else ""
        kind = " [Lab]" if self.is_lab else ""
        return f"{self.get_day_display()} {label}{span}: {self.course} - {self.subject} ({self.room}){kind}"

    def clean(self):
        # Ensure subject belongs to course and staff teaches subject
        if self.subject.course_id != self.course_id:
            raise ValidationError("Subject course mismatch with entry course")
        if self.subject.staff_id != self.staff_id:
            raise ValidationError("Selected staff is not assigned to the subject")

        # Period range and duration validations
        if not (1 <= int(self.period_number) <= 6):
            raise ValidationError("period_number must be between 1 and 6")

        if int(self.duration_periods) < 1:
            raise ValidationError("duration_periods must be at least 1")

        if self.is_lab and int(self.duration_periods) != 2:
            raise ValidationError("Lab sessions must span exactly 2 consecutive periods")

        end_period = int(self.period_number) + int(self.duration_periods) - 1
        if end_period > 6:
            raise ValidationError("Session extends beyond the last available period")

        # If this slot originates from a published extra slot due to unavailability,
        # relax certain per-day subject restrictions to allow make-up/extra classes.
        try:
            extra_slot_exists = ExtraClassAvailability.objects.filter(
                session_id=self.session_id,
                day=self.day,
                period_number=self.period_number,
                course_id=self.course_id,
            ).exists()
        except Exception:
            extra_slot_exists = False

        # Prevent scheduling same subject more than once per course/day,
        # except when filling an ExtraClassAvailability slot (make-up/extra class).
        if not extra_slot_exists:
            if TimetableEntry.objects.filter(
                session_id=self.session_id,
                day=self.day,
                course_id=self.course_id,
                subject_id=self.subject_id,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("Subject already scheduled for this course on the selected day")

        # Prevent conflicts across spanned periods for staff, room, and course
        for p in range(int(self.period_number), end_period + 1):
            if TimetableEntry.objects.filter(
                session_id=self.session_id,
                day=self.day,
                period_number=p,
                staff_id=self.staff_id,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("Teacher has another class in the selected time range")

            if TimetableEntry.objects.filter(
                session_id=self.session_id,
                day=self.day,
                period_number=p,
                room_id=self.room_id,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("Room is occupied in the selected time range")

            if TimetableEntry.objects.filter(
                session_id=self.session_id,
                day=self.day,
                period_number=p,
                course_id=self.course_id,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("Course already has another class in the selected time range")

        # No consecutive classes for the same subject (ensure a gap)
        # Disallow immediately adjacent periods before or after this entry's spanned range
        adjacent_periods = []
        start_p = int(self.period_number)
        end_p = int(end_period)
        if start_p - 1 >= 1:
            adjacent_periods.append(start_p - 1)
        if end_p + 1 <= 6:
            adjacent_periods.append(end_p + 1)
        if adjacent_periods:
            # Skip adjacency restriction when filling an ExtraClassAvailability slot
            if not extra_slot_exists:
                if TimetableEntry.objects.filter(
                    session_id=self.session_id,
                    day=self.day,
                    course_id=self.course_id,
                    subject_id=self.subject_id,
                    period_number__in=adjacent_periods,
                ).exclude(pk=self.pk).exists():
                    raise ValidationError("No consecutive periods allowed for the same subject")

        # Weekly credit limit: sum of durations for this subject in the session
        # Weekly credit limit: keep for regular scheduling, but allow overage when
        # filling ExtraClassAvailability (admin/HOD may later review totals).
        credits = getattr(self.subject, "credits", 0) or 0
        if credits > 0 and not extra_slot_exists:
            existing_entries = TimetableEntry.objects.filter(
                session_id=self.session_id,
                subject_id=self.subject_id,
            ).exclude(pk=self.pk)
            existing_total = sum(int(e.duration_periods) for e in existing_entries)
            if existing_total + int(self.duration_periods) > credits:
                raise ValidationError(
                    f"Weekly limit exceeded: {existing_total + int(self.duration_periods)} > allowed {credits} for {self.subject.name}"
                )

class ExtraClassSchedule(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("scheduled", "Scheduled"),
        ("cancelled", "Cancelled"),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True)
    start_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="requested")
    requires_hod_approval = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} extra class by {self.staff} on {self.start_datetime} ({self.duration_minutes}m)"

    def clean(self):
        # Basic validation and conflict detection
        if not self.start_datetime:
            raise ValidationError("Start date/time is required")
        if self.duration_minutes <= 0:
            raise ValidationError("Duration must be positive")

        # Ensure subject belongs to staff/course
        if self.subject.staff_id != self.staff_id:
            raise ValidationError("Subject is not taught by the selected staff")
        if self.subject.course_id != self.course_id:
            raise ValidationError("Subject does not belong to the selected course")

        # Disallow scheduling during staff unavailability (weekly pattern check)
        # Map datetime to weekday code used by TimetableEntry.DAY_CHOICES
        dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        weekday = dow_map.get(self.start_datetime.weekday())
        # For clashes with weekly timetable periods (approximate by hour blocks 9-15)
        try:
            from datetime import time, timedelta
            start_time = self.start_datetime.time()
            end_dt = self.start_datetime + timedelta(minutes=int(self.duration_minutes))
            end_time = end_dt.time()

            # Map to period numbers 1..6 based on hour ranges
            period_ranges = [
                (time(9, 0), time(10, 0)),
                (time(10, 0), time(11, 0)),
                (time(11, 0), time(12, 0)),
                (time(12, 0), time(13, 0)),
                (time(13, 0), time(14, 0)),
                (time(14, 0), time(15, 0)),
            ]
            occupied_periods = []
            for idx, (ps, pe) in enumerate(period_ranges, start=1):
                # Overlap if extra class touches any part of the period window
                if not (end_time <= ps or start_time >= pe):
                    occupied_periods.append(idx)

            if weekday in [c[0] for c in TimetableEntry.DAY_CHOICES] and occupied_periods:
                # Check clashes with teacher/course/room timetable entries
                for p in occupied_periods:
                    if TimetableEntry.objects.filter(
                        session_id=self.session_id,
                        day=weekday,
                        period_number=p,
                        staff_id=self.staff_id,
                    ).exists():
                        raise ValidationError("Teacher has another class during the selected time")
                    if TimetableEntry.objects.filter(
                        session_id=self.session_id,
                        day=weekday,
                        period_number=p,
                        course_id=self.course_id,
                    ).exists():
                        raise ValidationError("Course has another class during the selected time")
                    if self.room_id and TimetableEntry.objects.filter(
                        session_id=self.session_id,
                        day=weekday,
                        period_number=p,
                        room_id=self.room_id,
                    ).exists():
                        raise ValidationError("Room is occupied during the selected time")

            # Block if unavailability overlaps by weekly pattern
            # Note: StaffUnavailability stores weekly day/period spans with duration
            extra_date = self.start_datetime.date()
            unav_qs = StaffUnavailability.objects.filter(
                staff_id=self.staff_id,
                session_id=self.session_id,
                day=weekday,
            )
            for ua in unav_qs:
                # Skip if a one-time exception applies on the extra class date
                if ua.exception_date and ua.exception_date == extra_date:
                    continue
                # Skip recurring entries past their repeat_until date
                if ua.recurring_weekly and ua.repeat_until and extra_date > ua.repeat_until:
                    continue
                covered = set(range(ua.period_number, ua.period_number + int(ua.duration_periods)))
                if covered & set(occupied_periods):
                    raise ValidationError("Selected time overlaps with marked unavailability")
        except Exception:
            # Best-effort conflict detection; do not fail clean due to mapping errors
            pass

class StaffUnavailability(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=TimetableEntry.DAY_CHOICES)
    period_number = models.PositiveSmallIntegerField()
    duration_periods = models.PositiveSmallIntegerField(default=1)
    reason = models.TextField(blank=True)
    # New fields for recurring and coded reasons
    REASON_CODE_CHOICES = [
        ("personal", "Personal"),
        ("medical", "Medical"),
        ("professional", "Professional Development"),
        ("other", "Other"),
    ]
    reason_code = models.CharField(max_length=32, choices=REASON_CODE_CHOICES, default="other")
    recurring_weekly = models.BooleanField(default=False)
    repeat_until = models.DateField(null=True, blank=True)
    # One-time exception support
    exception_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff} unavailable {self.day} P{self.period_number} ({self.duration_periods}p)"


class ExtraClassAvailability(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=TimetableEntry.DAY_CHOICES)
    period_number = models.PositiveSmallIntegerField()
    duration_periods = models.PositiveSmallIntegerField(default=1)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    created_from = models.ForeignKey('TimetableEntry', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_by = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "day", "period_number", "room"], name="uniq_extra_slot_room"),
            models.UniqueConstraint(fields=["session", "day", "period_number", "course"], name="uniq_extra_slot_course"),
        ]

    def __str__(self):
        claimed = f" claimed by {self.claimed_by}" if self.claimed_by_id else " available"
        return f"Extra slot {self.day} P{self.period_number} ({self.duration_periods}p) in {self.room} for {self.course}{claimed}"


class ExtraClassRequest(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("scheduled", "Scheduled"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    preferred_day = models.CharField(max_length=3, choices=TimetableEntry.DAY_CHOICES, blank=True)
    preferred_period = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_periods = models.PositiveSmallIntegerField(default=1)
    is_lab = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Extra request {self.subject} by {self.staff} ({self.status})"


class TimetableAuditLog(models.Model):
    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("unavailable", "Mark Unavailable"),
        ("extra_request", "Extra Request"),
        ("schedule_extra", "Schedule Extra"),
    ]

    actor = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    entry = models.ForeignKey(TimetableEntry, null=True, blank=True, on_delete=models.SET_NULL)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.actor.email if self.actor_id else "system"
        return f"[{self.action}] by {who} at {self.created_at}"

# Notes and MCQ Test models

class Note(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    file = models.FileField(upload_to="notes/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name}"


class MCQTest(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name}"


class MCQQuestion(models.Model):
    test = models.ForeignKey(MCQTest, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()

    def __str__(self):
        return self.text[:50]


class MCQOption(models.Model):
    question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:50]


class MCQSubmission(models.Model):
    test = models.ForeignKey(MCQTest, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["test", "student"], name="uniq_test_student_submission"),
        ]


class MCQAnswer(models.Model):
    submission = models.ForeignKey(MCQSubmission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(MCQOption, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["submission", "question"], name="uniq_submission_question"),
        ]


# Proctor and Fee Payment models

class ProctorAssignment(models.Model):
    proctor = models.ForeignKey(Staff, on_delete=models.CASCADE)
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student"], name="uniq_student_proctor"),
        ]

    def clean(self):
        # Ensure proctor and student belong to same course
        if self.proctor.course_id and self.student.course_id and self.proctor.course_id != self.student.course_id:
            raise ValidationError("Proctor must belong to the same course as the student")
        # Limit number of students per proctor (configurable cap)
        cap = 25
        current = ProctorAssignment.objects.filter(proctor_id=self.proctor_id, active=True).exclude(pk=self.pk).count()
        if current >= cap:
            raise ValidationError(f"Proctor load exceeded: {current} assigned, cap is {cap}")

    def __str__(self):
        return f"{self.student} → {self.proctor}"


class FeePayment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to="fees/")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "session"], name="uniq_fee_by_student_session"),
        ]

    def __str__(self):
        return f"{self.student} - {self.session} ({self.status})"
