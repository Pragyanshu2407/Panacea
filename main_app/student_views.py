import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    # Subject now relates to Course via M2M 'courses'
    total_subject = Subject.objects.filter(courses=student.course).count()
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()
    if total_attendance == 0:  # Don't divide. DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    subjects = Subject.objects.filter(courses=student.course)
    for subject in subjects:
        attendance = Attendance.objects.filter(subject=subject)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count()
        subject_name.append(subject.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    now = timezone.now()
    days = [now - timedelta(days=i) for i in range(6, -1, -1)]
    notif_labels = [d.strftime("%b %d") for d in days]
    notif_counts = [NotificationStudent.objects.filter(student=student, created_at__date=d.date()).count() for d in days]
    recent_notifications = NotificationStudent.objects.filter(student=student).order_by('-created_at')[:10]

    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'subjects': subjects,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'page_title': 'Student Homepage',
        'notif_labels': notif_labels,
        'notif_counts': notif_counts,
        'recent_notifications': recent_notifications,

    }
    return render(request, 'student_template/home_content.html', context)


def student_timetable(request):
    student = get_object_or_404(Student, admin=request.user)
    # Filter strictly by the student's section and session so students
    # only see their own section's timetable, not the entire course.
    entries = (
        TimetableEntry.objects
        .filter(session=student.session, section=student.section)
        .select_related("subject", "staff", "room")
    )
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    grid = {d: [None] * 6 for d in days}
    for e in entries:
        if 1 <= e.period_number <= 6:
            end_p = min(e.period_number + max(1, int(getattr(e, "duration_periods", 1))) - 1, 6)
            for p in range(e.period_number, end_p + 1):
                grid[e.day][p - 1] = e
    day_rows = [(d, grid[d]) for d in days]
    context = {
        "page_title": "My Timetable",
        "days": days,
        "day_rows": day_rows,
        "slot_labels": ["9-10", "10-11", "11-12", "12-1", "1-2", "2-3"],
    }
    return render(request, "student_template/timetable.html", context)


def student_extra_classes(request):
    student = get_object_or_404(Student, admin=request.user)
    schedules = (
        ExtraClassSchedule.objects
        .filter(course=student.course, status__in=["approved", "scheduled"])
        .select_related("staff", "subject", "course", "room")
        .order_by("-start_datetime")
    )
    context = {
        "page_title": "Extra Classes",
        "schedules": schedules,
    }
    return render(request, "student_template/extra_classes.html", context)


def student_fees(request):
    student = get_object_or_404(Student, admin=request.user)
    # Limit sessions to student's session and set initial
    form = FeePaymentForm(request.POST or None, request.FILES or None)
    if request.method != "POST":
        if "session" in form.fields:
            form.fields["session"].queryset = Session.objects.filter(id=student.session_id)
            form.initial["session"] = student.session
    context = {
        "page_title": "Fee Payment",
        "form": form,
        "fees": FeePayment.objects.filter(student=student).select_related("session"),
    }
    if request.method == "POST":
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                # Force session to student's session
                obj.session = student.session
                obj.save()
                messages.success(request, "Fee submitted for review")
                return redirect(reverse("student_fees"))
            except Exception as e:
                messages.error(request, f"Could not submit: {e}")
        else:
            messages.error(request, "Please correct the errors below")
    return render(request, "student_template/fees.html", context)




@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            # Filter by M2M 'courses'
            'subjects': Subject.objects.filter(courses=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None, request.FILES or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student)
    context = {
        'results': results,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)


#library

def view_books(request):
    books = Book.objects.all()
    context = {
        'books': books,
        'page_title': "Library"
    }
    return render(request, "student_template/view_books.html", context)


# Notes view and MCQ tests for students
def student_view_notes(request):
    student = get_object_or_404(Student, admin=request.user)
    subjects = Subject.objects.filter(courses=student.course)
    subject_id = request.GET.get("subject")
    notes_qs = Note.objects.filter(subject__courses=student.course).select_related("subject", "staff")
    if subject_id:
        notes_qs = notes_qs.filter(subject_id=subject_id)
    context = {
        "page_title": "Subject Notes",
        "subjects": subjects,
        "notes": notes_qs.order_by("-created_at"),
        "selected_subject_id": int(subject_id) if subject_id else None,
    }
    return render(request, "student_template/student_view_notes.html", context)


def student_available_tests(request):
    student = get_object_or_404(Student, admin=request.user)
    now = timezone.now()
    tests = (
        MCQTest.objects
        .filter(subject__courses=student.course, is_active=True)
        .filter(Q(scheduled_at__isnull=True) | Q(scheduled_at__lte=now))
        .select_related("subject", "staff")
    )
    context = {
        "page_title": "Available MCQ Tests",
        "tests": tests.order_by("-created_at"),
    }
    return render(request, "student_template/student_available_tests.html", context)


def student_take_test(request, test_id: int):
    student = get_object_or_404(Student, admin=request.user)
    test = get_object_or_404(MCQTest, id=test_id, subject__courses=student.course, is_active=True)
    # Enforce schedule: block access before scheduled time
    now = timezone.now()
    if test.scheduled_at and test.scheduled_at > now and request.method != "POST":
        messages.info(request, "This test will be available at %s" % test.scheduled_at)
        return redirect(reverse("student_available_tests"))
    questions = MCQQuestion.objects.filter(test=test).prefetch_related("options")
    # Check if already submitted
    existing = MCQSubmission.objects.filter(test=test, student=student).first()
    if existing and request.method != "POST":
        messages.info(request, "You have already submitted this test. Score: %d" % existing.score)
    if request.method == "POST":
        if existing:
            messages.info(request, "You already submitted this test.")
            return redirect(reverse("student_available_tests"))
        # Evaluate answers
        score = 0
        submission = MCQSubmission.objects.create(test=test, student=student, score=0)
        for q in questions:
            key = f"q_{q.id}"
            selected_option_id = request.POST.get(key)
            if not selected_option_id:
                continue
            try:
                opt = MCQOption.objects.get(id=int(selected_option_id), question=q)
            except MCQOption.DoesNotExist:
                continue
            MCQAnswer.objects.create(submission=submission, question=q, selected_option=opt)
            if opt.is_correct:
                score += 1
        submission.score = score
        submission.save(update_fields=["score"])
        messages.success(request, f"Submitted! Your score: {score} / {questions.count()}")
        return redirect(reverse("student_available_tests"))
    context = {
        "page_title": f"Take Test - {test.title}",
        "test": test,
        "questions": questions,
    }
    return render(request, "student_template/student_take_test.html", context)

