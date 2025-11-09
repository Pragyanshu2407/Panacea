import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'college_management_system.settings')
import django
django.setup()

from django.db import transaction
from main_app.models import (
    CustomUser,
    Staff,
    Student,
    Attendance,
    AttendanceReport,
    LeaveReportStudent,
    LeaveReportStaff,
    FeedbackStudent,
    FeedbackStaff,
    NotificationStudent,
    NotificationStaff,
    StudentResult,
    Library,
    IssuedBook,
    TimetableEntry,
    ExtraClassSchedule,
    ExtraClassRequest,
    ExtraClassAvailability,
    Note,
    MCQTest,
    MCQQuestion,
    MCQOption,
    MCQAnswer,
    MCQSubmission,
    ProctorAssignment,
    FeePayment,
    Subject,
)


def reset_staff_and_students():
    """
    Deletes all Staff and Student accounts (and cascaded data) while keeping Admins.

    NOTE: Due to model constraints (on_delete=CASCADE), removing Staff will also
    remove dependent records such as Subjects assigned to those Staff, their
    TimetableEntries, attendance/feedback/notifications linked to them, etc.
    Removing Students will cascade their attendance reports, library records,
    fee payments, proctor assignments, and other related data.
    """
    # Show current counts for visibility
    print("Before reset:")
    print("  Staff profiles:", Staff.objects.count())
    print("  Student profiles:", Student.objects.count())
    print("  Staff users (user_type=2):", CustomUser.objects.filter(user_type='2').count())
    print("  Student users (user_type=3):", CustomUser.objects.filter(user_type='3').count())

    # Proactively remove dependent records that use PROTECT/DO_NOTHING to avoid FK errors
    with transaction.atomic():
        print("Deleting dependent records...")
        AttendanceReport.objects.all().delete()
        Attendance.objects.all().delete()
        MCQAnswer.objects.all().delete()
        MCQSubmission.objects.all().delete()
        StudentResult.objects.all().delete()
        NotificationStudent.objects.all().delete()
        NotificationStaff.objects.all().delete()
        FeedbackStudent.objects.all().delete()
        FeedbackStaff.objects.all().delete()
        LeaveReportStudent.objects.all().delete()
        LeaveReportStaff.objects.all().delete()
        ProctorAssignment.objects.all().delete()
        FeePayment.objects.all().delete()
        Library.objects.all().delete()
        IssuedBook.objects.all().delete()
        ExtraClassRequest.objects.all().delete()
        ExtraClassSchedule.objects.all().delete()
        ExtraClassAvailability.objects.all().delete()
        MCQOption.objects.all().delete()
        MCQQuestion.objects.all().delete()
        MCQTest.objects.all().delete()
        Note.objects.all().delete()
        TimetableEntry.objects.all().delete()

        # Delete students and staff profiles explicitly
        Student.objects.all().delete()
        Subject.objects.all().delete()
        Staff.objects.all().delete()

        # Finally delete all non-admin users
        non_admin_users = CustomUser.objects.exclude(user_type='1')
        print("Deleting non-admin users:", non_admin_users.count())
        deleted_summary = non_admin_users.delete()

    print("Delete summary:", deleted_summary)
    print("After reset:")
    print("  Staff profiles:", Staff.objects.count())
    print("  Student profiles:", Student.objects.count())
    print("  Remaining non-admin users:", CustomUser.objects.exclude(user_type='1').count())
    print("Completed reset of staff and student data. Admin users are preserved.")


if __name__ == '__main__':
    try:
        reset_staff_and_students()
    except Exception as e:
        import traceback
        print("ERROR during reset:", e)
        print(traceback.format_exc())