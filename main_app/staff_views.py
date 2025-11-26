import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from . import forms, models
from datetime import date
from django.contrib import messages
from django.urls import reverse


def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    now = timezone.now()
    days = [now - timedelta(days=i) for i in range(6, -1, -1)]
    notif_labels = [d.strftime("%b %d") for d in days]
    staff_notif_counts = [NotificationStaff.objects.filter(staff=staff, created_at__date=d.date()).count() for d in days]
    recent_notifications = NotificationStaff.objects.filter(staff=staff).order_by('-created_at')[:10]

    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.first_name) + ' ' + str(staff.admin.last_name[0]) + '' + ' (' + str(staff.course) + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'notif_labels': notif_labels,
        'notif_counts': staff_notif_counts,
        'recent_notifications': recent_notifications,
    }
    return render(request, 'staff_template/home_content.html', context)


def staff_timetable(request):
    staff = get_object_or_404(Staff, admin=request.user)
    # Fetch all entries for this staff across sessions
    entries = (
        TimetableEntry.objects.filter(staff=staff)
        .select_related("session", "course", "section", "subject", "room", "subject__semester")
    )
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    grid = {d: [None] * 6 for d in days}
    for e in entries:
        if 1 <= e.period_number <= 6:
            end_p = min(e.period_number + max(1, int(getattr(e, "duration_periods", 1))) - 1, 6)
            for p in range(e.period_number, end_p + 1):
                grid[e.day][p - 1] = e
    # Build template-friendly rows as list of (day, row_entries)
    day_rows = [(d, grid[d]) for d in days]
    context = {
        "page_title": "My Timetable",
        "days": days,
        "day_rows": day_rows,
        "slot_labels": ["9-10", "10-11", "11-12", "12-1", "1-2", "2-3"],
    }
    return render(request, "staff_template/timetable.html", context)


logger = logging.getLogger(__name__)

def staff_mark_unavailability(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffUnavailabilityForm(request.POST or None)
    context = {
        "page_title": "Mark Unavailability",
        "form": form,
        "history": StaffUnavailability.objects.filter(staff=staff).order_by("-created_at"),
    }
    if request.method == "POST" and form.is_valid():
        logger.debug("Processing unavailability submission for staff_id=%s", staff.id)
        unavail = form.save(commit=False)
        unavail.staff = staff
        unavail.save()
        logger.info("Saved unavailability id=%s for staff_id=%s", unavail.id, staff.id)
        # Create extra availability slots for any scheduled entries affected
        try:
            affected = TimetableEntry.objects.filter(
                staff=staff,
                session=unavail.session,
                day=unavail.day,
                period_number__gte=unavail.period_number,
                period_number__lt=unavail.period_number + unavail.duration_periods,
            )
            for entry in affected:
                # Avoid duplicate create if already exists
                ExtraClassAvailability.objects.get_or_create(
                    session=entry.session,
                    course=entry.course,
                    day=entry.day,
                    period_number=entry.period_number,
                    duration_periods=entry.duration_periods,
                    room=entry.room,
                    defaults={"created_from": entry},
                )
            logger.info("Published %s extra slot(s) due to unavailability id=%s", affected.count(), unavail.id)
            # Notify other staff in the course
            others = Staff.objects.filter(course=staff.course).exclude(id=staff.id)
            msg = f"Extra slot available: {unavail.day} P{unavail.period_number} for {staff.course}"
            for s in others:
                NotificationStaff.objects.create(staff=s, message=msg)
            logger.debug("Notified %s staff about extra slots", others.count())
            TimetableAuditLog.objects.create(
                actor=request.user,
                action="unavailable",
                entry=None,
                details=f"{staff} unavailable {unavail.day} P{unavail.period_number} ({unavail.duration_periods}p)"
            )
            messages.success(request, "Unavailability recorded and extra slots published where applicable.")
        except Exception as e:
            logger.exception("Error while publishing extra slots for unavailability id=%s", unavail.id)
            messages.error(request, "Saved unavailability but could not publish slots. The issue has been logged.")
        return redirect(reverse("staff_mark_unavailability"))
    return render(request, "staff_template/unavailability.html", context)


def staff_schedule_extra_class(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = ExtraClassScheduleForm(request.POST or None)
    # Ensure model-level validation sees the correct staff during form.is_valid()
    form.instance.staff = staff
    # Limit selectable subjects to those taught by this staff
    form.fields["subject"].queryset = Subject.objects.filter(staff=staff)
    # Limit course to staff's course
    form.fields["course"].queryset = Course.objects.filter(id=staff.course_id)

    existing = ExtraClassSchedule.objects.filter(staff=staff).order_by("-start_datetime")
    context = {
        "page_title": "Schedule Extra Class",
        "form": form,
        "existing": existing,
    }
    if request.method == "POST" and form.is_valid():
        logger.debug("Processing extra class schedule request for staff_id=%s", staff.id)
        sched = form.save(commit=False)
        sched.staff = staff
        # Default: require HOD approval
        sched.requires_hod_approval = True
        try:
            with transaction.atomic():
                sched.full_clean()
                sched.save()
                logger.info("Saved extra class schedule id=%s for staff_id=%s", sched.id, staff.id)
                NotificationStaff.objects.create(
                    staff=staff,
                    message=f"Extra class request submitted: {sched.subject} on {sched.start_datetime}"
                )
                TimetableAuditLog.objects.create(
                    actor=request.user,
                    action="schedule_extra",
                    details=f"{staff} requested extra class {sched.subject} on {sched.start_datetime}"
                )
                messages.success(request, "Extra class request submitted for approval.")
                return redirect(reverse("staff_schedule_extra_class"))
        except Exception:
            logger.exception("Error while scheduling extra class for staff_id=%s", staff.id)
            messages.error(request, "Could not schedule extra class. Please check your inputs." )
            # Fall through to re-render the page with form errors and context
            
    # If form is invalid or exception occurred, render page with context
    return render(request, "staff_template/extra_class_schedule.html", context)


def staff_extra_class_request(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = ExtraClassRequestForm(request.POST or None, staff=staff)
    context = {
        "page_title": "Request Extra Class",
        "form": form,
        "requests": ExtraClassRequest.objects.filter(staff=staff).order_by("-created_at"),
    }
    if request.method == "POST" and form.is_valid():
        req = form.save(commit=False)
        req.staff = staff
        req.status = "requested"
        req.save()
        # Notify other teachers in the same course about this extra class request
        try:
            others = Staff.objects.filter(course=staff.course).exclude(id=staff.id)
            msg = (
                f"Extra class requested: {req.subject.name} ({req.session}) in {req.course.name}. "
                f"Preferred: {req.preferred_day or '-'} P{req.preferred_period or '-'}"
            )
            for s in others:
                NotificationStaff.objects.create(staff=s, message=msg)
        except Exception:
            # Non-fatal: continue even if notifications fail
            pass
        TimetableAuditLog.objects.create(
            actor=request.user,
            action="extra_request",
            details=f"Extra request for {req.subject} {req.session} {req.course}"
        )
        messages.success(request, "Extra class request submitted.")
        return redirect(reverse("staff_extra_class_request"))
    return render(request, "staff_template/extra_class_request.html", context)


def staff_available_extra_slots(request):
    staff = get_object_or_404(Staff, admin=request.user)
    # Filter slots for the staff course and unclaimed
    slots = ExtraClassAvailability.objects.filter(course=staff.course, claimed_by__isnull=True).select_related("room", "course", "session")
    context = {
        "page_title": "Available Extra Slots",
        "slots": slots.order_by("day", "period_number"),
        "subjects": Subject.objects.filter(staff=staff),
        "rooms": Room.objects.all().order_by("name"),
    }
    return render(request, "staff_template/extra_slots.html", context)


@transaction.atomic
def staff_claim_extra_slot(request, slot_id: int):
    staff = get_object_or_404(Staff, admin=request.user)
    slot = get_object_or_404(ExtraClassAvailability, id=slot_id, claimed_by__isnull=True)
    subject_id = request.POST.get("subject_id")
    subject = get_object_or_404(Subject, id=subject_id)
    room_id = request.POST.get("room_id")
    chosen_room = None
    if room_id:
        try:
            chosen_room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            chosen_room = None
    # Basic validations
    if subject.staff_id != staff.id:
        messages.error(request, "You can only claim slots for your own subject.")
        return redirect(reverse("staff_available_extra_slots"))
    if not subject.courses.filter(id=slot.course_id).exists():
        messages.error(request, "Subject is not offered for the selected course.")
        return redirect(reverse("staff_available_extra_slots"))
    # Prevent conflicts: staff, room, course slots already ensured unique via TimetableEntry constraints
    entry = TimetableEntry(
        session=slot.session,
        course=slot.course,
        subject=subject,
        staff=staff,
        room=chosen_room or slot.room,
        day=slot.day,
        period_number=slot.period_number,
        is_lab=False,
        duration_periods=slot.duration_periods,
    )
    try:
        entry.clean()
        entry.save()
        slot.claimed_by = staff
        slot.subject = subject
        slot.save()
        TimetableAuditLog.objects.create(
            actor=request.user,
            action="schedule_extra",
            entry=entry,
            details=f"Scheduled extra {subject} on {slot.day} P{slot.period_number}"
        )
        # Notify about claim due to teacher unavailability
        try:
            orig_staff = None
            if slot.created_from_id:
                try:
                    orig_staff = slot.created_from.staff
                except Exception:
                    orig_staff = None

            # Notify students in the course
            students = Student.objects.filter(course=slot.course)
            base_msg = (
                f"Extra class claimed: {subject.name} by {staff.admin.get_full_name()} "
                f"on {slot.day} P{slot.period_number} ({TimetableEntry.SLOT_LABELS.get(slot.period_number, '')})"
            )
            if orig_staff:
                student_msg = base_msg + f" due to unavailability of {orig_staff.admin.get_full_name()}"
            else:
                student_msg = base_msg + " due to teacher unavailability"
            for stu in students:
                NotificationStudent.objects.create(student=stu, message=student_msg)

            # Notify the originally unavailable teacher (if known)
            if orig_staff:
                NotificationStaff.objects.create(
                    staff=orig_staff,
                    message=(
                        f"Your unavailable slot {slot.day} P{slot.period_number} "
                        f"has been claimed by {staff.admin.get_full_name()} for {subject.name}."
                    ),
                )

            # Notify other staff in the course
            try:
                others = Staff.objects.filter(course=slot.course).exclude(id__in=[staff.id, getattr(orig_staff, 'id', None)])
                staff_msg = (
                    f"Extra slot claimed for {slot.course.name}: {subject.name} by {staff.admin.get_full_name()} "
                    f"on {slot.day} P{slot.period_number}"
                )
                if orig_staff:
                    staff_msg += f" (covering {orig_staff.admin.get_full_name()})"
                for s in others:
                    NotificationStaff.objects.create(staff=s, message=staff_msg)
            except Exception:
                pass
        except Exception:
            # Non-fatal: continue even if notifications fail
            pass
        messages.success(request, "Extra slot claimed and scheduled.")
    except Exception as e:
        messages.error(request, f"Could not schedule extra class: {e}")
    return redirect(reverse("staff_available_extra_slots"))


def staff_course_extra_classes(request):
    staff = get_object_or_404(Staff, admin=request.user)
    schedules = (
        ExtraClassSchedule.objects
        .filter(course=staff.course, status__in=["approved", "scheduled"])
        .select_related("staff", "subject", "course", "room")
        .order_by("-start_datetime")
    )
    context = {
        "page_title": "Course Extra Classes",
        "schedules": schedules,
    }
    return render(request, "staff_template/extra_classes_course.html", context)


def proctor_dashboard(request):
    staff = get_object_or_404(Staff, admin=request.user)
    assignments = ProctorAssignment.objects.filter(proctor=staff, active=True).select_related("student")
    students = [a.student for a in assignments]
    fees = FeePayment.objects.filter(student__in=students).select_related("student", "session")
    leaves = LeaveReportStudent.objects.filter(student__in=students).select_related("student").order_by("-created_at")
    context = {
        "page_title": "Proctor Dashboard",
        "assignments": assignments,
        "fees": fees,
        "leaves": leaves,
    }
    return render(request, "staff_template/proctor_dashboard.html", context)


def staff_review_fee(request, fee_id: int):
    staff = get_object_or_404(Staff, admin=request.user)
    fee = get_object_or_404(FeePayment, id=fee_id)
    # Ensure this staff is proctor of the student
    if not ProctorAssignment.objects.filter(proctor=staff, student=fee.student, active=True).exists():
        messages.error(request, "You are not the proctor for this student")
        return redirect(reverse("proctor_dashboard"))
    action = request.POST.get("action")
    notes = request.POST.get("notes", "")
    if not notes or not notes.strip():
        messages.error(request, "Message is required")
        return redirect(reverse("proctor_dashboard"))
    if action not in ("approve", "reject"):
        messages.error(request, "Invalid action")
        return redirect(reverse("proctor_dashboard"))
    fee.status = "approved" if action == "approve" else "rejected"
    fee.notes = notes
    fee.reviewed_by = staff
    from django.utils import timezone
    fee.reviewed_at = timezone.now()
    fee.save()
    messages.success(request, f"Fee {fee.status} for {fee.student}")
    return redirect(reverse("proctor_dashboard"))




def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_sections(request):
    """Return sections assigned to the given subject."""
    subject_id = request.POST.get('subject')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        sections = subject.sections.all().order_by('name')
        section_data = []
        for section in sections:
            section_data.append({
                "id": section.id,
                "name": f"{section.course.name} - {section.name}"
            })
        return JsonResponse(json.dumps(section_data), content_type='application/json', safe=False)
    except Exception as e:
        return e

@csrf_exempt
def get_students(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    section_id = request.POST.get('section')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        # If a specific section is chosen, filter by it directly
        if section_id:
            students = Student.objects.filter(section_id=section_id, session=session)
        else:
            # Otherwise, restrict to the subject's assigned sections (if any)
            sections_qs = subject.sections.all()
            if sections_qs.exists():
                students = Student.objects.filter(section__in=sections_qs, session=session)
            else:
                # Fallback to course-level filter if sections are not configured
                students = Student.objects.filter(
                    course_id__in=subject.courses.values_list('id', flat=True), session=session)
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.last_name + " " + student.admin.first_name
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    students = json.loads(student_data)
    try:
        session = get_object_or_404(Session, id=session_id)
        subject = get_object_or_404(Subject, id=subject_id)
        attendance = Attendance(session=session, subject=subject, date=date)
        attendance.save()

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))
            attendance_report = AttendanceReport(student=student, attendance=attendance, status=student_dict.get('status'))
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
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
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff=staff)
    sessions = Session.objects.all()
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects,
        'sessions': sessions
    }
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_list')
            subject_id = request.POST.get('subject')
            test1 = request.POST.get('test1')
            test2 = request.POST.get('test2')
            quiz = request.POST.get('quiz')
            experiential = request.POST.get('experiential')
            see = request.POST.get('see')
            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)
            try:
                data = StudentResult.objects.get(
                    student=student, subject=subject)
                data.test1 = float(test1 or 0)
                data.test2 = float(test2 or 0)
                data.quiz = float(quiz or 0)
                data.experiential = float(experiential or 0)
                data.see = float(see or 0)
                data.save()
                messages.success(request, "Scores Updated")
            except:
                result = StudentResult(
                    student=student,
                    subject=subject,
                    test1=float(test1 or 0),
                    test2=float(test2 or 0),
                    quiz=float(quiz or 0),
                    experiential=float(experiential or 0),
                    see=float(see or 0)
                )
                result.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "staff_template/staff_add_result.html", context)


@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id)
        result = StudentResult.objects.get(student=student, subject=subject)
        result_data = {
            'test1': result.test1,
            'test2': result.test2,
            'quiz': result.quiz,
            'experiential': result.experiential,
            'see': result.see
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')

#library
def add_book(request):
    if request.method == "POST":
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']


        books = Book.objects.create(name=name, author=author, isbn=isbn, category=category )
        books.save()
        alert = True
        return render(request, "staff_template/add_book.html", {'alert':alert})
    context = {
        'page_title': "Add Book"
    }
    return render(request, "staff_template/add_book.html",context)

#issue book


def issue_book(request):
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            obj = models.IssuedBook()
            obj.student_id = request.POST['name2']
            obj.isbn = request.POST['isbn2']
            obj.save()
            alert = True
            return render(request, "staff_template/issue_book.html", {'obj':obj, 'alert':alert})
    return render(request, "staff_template/issue_book.html", {'form':form})

def view_issued_book(request):
    issuedBooks = IssuedBook.objects.all()
    details = []
    for i in issuedBooks:
        days = (date.today()-i.issued_date)
        d=days.days
        fine=0
        if d>14:
            day=d-14
            fine=day*5
        books = list(models.Book.objects.filter(isbn=i.isbn))
        # students = list(models.Student.objects.filter(admin=i.admin))
        i=0
        for l in books:
            t=(books[i].name,books[i].isbn,issuedBooks[0].issued_date,issuedBooks[0].expiry_date,fine)
            i=i+1
            details.append(t)
    return render(request, "staff_template/view_issued_book.html", {'issuedBooks':issuedBooks, 'details':details})


# Notes upload and MCQ test management
def staff_manage_notes(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notes = Note.objects.filter(staff=staff).select_related("subject").order_by("-created_at")
    form = NoteUploadForm(request.POST or None, request.FILES or None, staff=staff)
    context = {
        "page_title": "Upload Notes",
        "form": form,
        "notes": notes,
    }
    if request.method == "POST":
        if form.is_valid():
            obj = form.save(commit=False)
            obj.staff = staff
            obj.save()
            messages.success(request, "Note uploaded successfully")
            return redirect(reverse("staff_manage_notes"))
        else:
            messages.error(request, "Please correct the errors in the form")
    return render(request, "staff_template/staff_manage_notes.html", context)


def staff_manage_tests(request):
    staff = get_object_or_404(Staff, admin=request.user)
    tests = MCQTest.objects.filter(staff=staff).select_related("subject").order_by("-created_at")
    form = MCQTestForm(request.POST or None, staff=staff)
    context = {
        "page_title": "Manage MCQ Tests",
        "form": form,
        "tests": tests,
    }
    if request.method == "POST":
        if form.is_valid():
            test = form.save(commit=False)
            test.staff = staff
            test.save()
            messages.success(request, "Test created. Add questions next.")
            return redirect(reverse("staff_add_question", kwargs={"test_id": test.id}))
        else:
            messages.error(request, "Please correct the errors in the form")
    return render(request, "staff_template/staff_manage_tests.html", context)


def staff_toggle_test_active(request, test_id: int):
    staff = get_object_or_404(Staff, admin=request.user)
    test = get_object_or_404(MCQTest, id=test_id, staff=staff)
    if request.method == "POST":
        test.is_active = not test.is_active
        test.save(update_fields=["is_active"])
        messages.success(request, f"Test '{test.title}' is now {'Active' if test.is_active else 'Inactive'}.")
    return redirect(reverse("staff_manage_tests"))


def staff_add_question(request, test_id: int):
    staff = get_object_or_404(Staff, admin=request.user)
    test = get_object_or_404(MCQTest, id=test_id, staff=staff)
    form = MCQQuestionCreateForm(request.POST or None)
    existing_questions = MCQQuestion.objects.filter(test=test).prefetch_related("options")
    context = {
        "page_title": f"Add Questions - {test.title}",
        "form": form,
        "test": test,
        "questions": existing_questions,
    }
    if request.method == "POST":
        if form.is_valid():
            q = MCQQuestion.objects.create(test=test, text=form.cleaned_data["question_text"]) 
            opts = [
                form.cleaned_data["option1"],
                form.cleaned_data["option2"],
                form.cleaned_data["option3"],
                form.cleaned_data["option4"],
            ]
            correct_index = int(form.cleaned_data["correct_option"]) - 1
            for idx, text in enumerate(opts):
                MCQOption.objects.create(question=q, text=text, is_correct=(idx == correct_index))
            messages.success(request, "Question added")
            return redirect(reverse("staff_add_question", kwargs={"test_id": test.id}))
        else:
            messages.error(request, "Please fix the errors and try again")
    return render(request, "staff_template/staff_add_question.html", context)