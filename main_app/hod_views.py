import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from .forms import *
from .models import *


def admin_home(request):
    total_staff = Staff.objects.all().count()
    total_students = Student.objects.all().count()
    subjects = Subject.objects.all()
    total_subject = subjects.count()
    total_course = Course.objects.all().count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name[:7])
        attendance_list.append(attendance_count)

    # Total Subjects and students in Each Course
    course_all = Course.objects.all()
    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []

    for course in course_all:
        subjects = Subject.objects.filter(courses=course).count()
        students = Student.objects.filter(course_id=course.id).count()
        course_name_list.append(course.name)
        subject_count_list.append(subjects)
        student_count_list_in_course.append(students)
    
    subject_all = Subject.objects.all()
    subject_list = []
    student_count_list_in_subject = []
    for subject in subject_all:
        # Count students across all courses where this subject is offered
        student_count = Student.objects.filter(course__in=subject.courses.all()).count()
        subject_list.append(subject.name)
        student_count_list_in_subject.append(student_count)


    # For Students
    student_attendance_present_list=[]
    student_attendance_leave_list=[]
    student_name_list=[]

    students = Student.objects.all()
    for student in students:
        
        attendance = AttendanceReport.objects.filter(student_id=student.id, status=True).count()
        absent = AttendanceReport.objects.filter(student_id=student.id, status=False).count()
        leave = LeaveReportStudent.objects.filter(student_id=student.id, status=1).count()
        student_attendance_present_list.append(attendance)
        student_attendance_leave_list.append(leave+absent)
        student_name_list.append(student.admin.first_name)

    context = {
        'page_title': "Administrative Dashboard",
        'total_students': total_students,
        'total_staff': total_staff,
        'total_course': total_course,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'student_attendance_present_list': student_attendance_present_list,
        'student_attendance_leave_list': student_attendance_leave_list,
        "student_name_list": student_name_list,
        "student_count_list_in_subject": student_count_list_in_subject,
        "student_count_list_in_course": student_count_list_in_course,
        "course_name_list": course_name_list,

    }
    return render(request, 'hod_template/home_content.html', context)


def manage_proctors(request):
    form = ProctorAssignmentForm(request.POST or None)
    assignments = ProctorAssignment.objects.select_related("proctor", "student").all()
    context = {
        "page_title": "Manage Proctors",
        "form": form,
        "assignments": assignments,
    }
    if request.method == "POST":
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.clean()
                obj.save()
                messages.success(request, "Proctor assigned successfully")
                return redirect(reverse("manage_proctors"))
            except Exception as e:
                messages.error(request, f"Could not assign proctor: {e}")
        else:
            messages.error(request, "Please correct the errors below")
    return render(request, "hod_template/manage_proctors.html", context)


def add_staff(request):
    form = StaffForm(request.POST or None, request.FILES or None)
    # On initial GET, if a course is provided, filter sections to that course
    if request.method == 'GET':
        course_id = request.GET.get('course_id')
        if course_id:
            try:
                course = Course.objects.get(id=int(course_id))
                form.fields['sections'].queryset = Section.objects.filter(course=course)
                # Reflect selected course in the form
                form.fields['course'].initial = course.id
            except (ValueError, TypeError, Course.DoesNotExist):
                pass
    context = {'form': form, 'page_title': 'Add Staff'}
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password')
            course = form.cleaned_data.get('course')
            sections = form.cleaned_data.get('sections')
            semesters = form.cleaned_data.get('semesters')
            passport = request.FILES.get('profile_pic')
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=2, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.staff.course = course
                # Assign sections the staff can teach
                if sections is not None:
                    user.staff.save()
                    user.staff.sections.set(sections)
                # Assign semesters the staff can teach
                if semesters is not None:
                    user.staff.save()
                    user.staff.semesters.set(semesters)
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_staff'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Please fulfil all requirements")

    return render(request, 'hod_template/add_staff_template.html', context)


def add_student(request):
    student_form = StudentForm(request.POST or None, request.FILES or None)
    context = {'form': student_form, 'page_title': 'Add Student'}
    if request.method == 'POST':
        if student_form.is_valid():
            first_name = student_form.cleaned_data.get('first_name')
            last_name = student_form.cleaned_data.get('last_name')
            address = student_form.cleaned_data.get('address')
            email = student_form.cleaned_data.get('email')
            gender = student_form.cleaned_data.get('gender')
            password = student_form.cleaned_data.get('password')
            course = student_form.cleaned_data.get('course')
            session = student_form.cleaned_data.get('session')
            section = student_form.cleaned_data.get('section')
            semester = student_form.cleaned_data.get('semester')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=3, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.student.session = session
                user.student.course = course
                user.student.section = section
                user.student.semester = semester
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_student'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'hod_template/add_student_template.html', context)


def add_course(request):
    form = CourseForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course()
                course.name = name
                course.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_course'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'hod_template/add_course_template.html', context)


def add_subject(request):
    form = SubjectForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Subject'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                # Persist all fields (including credits) using the model form
                form.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_subject'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")

    return render(request, 'hod_template/add_subject_template.html', context)


def manage_staff(request):
    allStaff = CustomUser.objects.filter(user_type=2)
    context = {
        'allStaff': allStaff,
        'page_title': 'Manage Staff'
    }
    return render(request, "hod_template/manage_staff.html", context)


def manage_student(request):
    students = CustomUser.objects.filter(user_type=3)
    context = {
        'students': students,
        'page_title': 'Manage Students'
    }
    return render(request, "hod_template/manage_student.html", context)


def manage_course(request):
    courses = Course.objects.all()
    context = {
        'courses': courses,
        'page_title': 'Manage Courses'
    }
    return render(request, "hod_template/manage_course.html", context)


def manage_subject(request):
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
        'page_title': 'Manage Subjects'
    }
    return render(request, "hod_template/manage_subject.html", context)


def edit_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    form = StaffForm(request.POST or None, instance=staff)
    context = {
        'form': form,
        'staff_id': staff_id,
        'page_title': 'Edit Staff'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            course = form.cleaned_data.get('course')
            sections = form.cleaned_data.get('sections')
            semesters = form.cleaned_data.get('semesters')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=staff.admin.id)
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                staff.course = course
                # Update teachable sections
                if sections is not None:
                    staff.save()
                    staff.sections.set(sections)
                # Update teachable semesters
                if semesters is not None:
                    staff.save()
                    staff.semesters.set(semesters)
                user.save()
                staff.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_staff', args=[staff_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
                messages.error(request, "Please fil form properly")
    else:
        # Staff instance already loaded via get_object_or_404; simply render the form
        return render(request, "hod_template/edit_staff_template.html", context)


def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    form = StudentForm(request.POST or None, instance=student)
    context = {
        'form': form,
        'student_id': student_id,
        'page_title': 'Edit Student'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            course = form.cleaned_data.get('course')
            session = form.cleaned_data.get('session')
            section = form.cleaned_data.get('section')
            semester = form.cleaned_data.get('semester')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=student.admin.id)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                student.session = session
                user.gender = gender
                user.address = address
                student.course = course
                student.section = section
                student.semester = semester
                user.save()
                student.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_student', args=[student_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please Fill Form Properly!")
    else:
        return render(request, "hod_template/edit_student_template.html", context)


def edit_course(request, course_id):
    instance = get_object_or_404(Course, id=course_id)
    form = CourseForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'course_id': course_id,
        'page_title': 'Edit Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course.objects.get(id=course_id)
                course.name = name
                course.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'hod_template/edit_course_template.html', context)


def edit_subject(request, subject_id):
    instance = get_object_or_404(Subject, id=subject_id)
    form = SubjectForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'subject_id': subject_id,
        'page_title': 'Edit Subject'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                # Persist all fields (including credits) using the model form
                form.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_subject', args=[subject_id]))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")
    return render(request, 'hod_template/edit_subject_template.html', context)


def add_session(request):
    form = SessionForm(request.POST or None)
    context = {'form': form, 'page_title': 'Add Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Created")
                return redirect(reverse('add_session'))
            except Exception as e:
                messages.error(request, 'Could Not Add ' + str(e))
        else:
            messages.error(request, 'Fill Form Properly ')
    return render(request, "hod_template/add_session_template.html", context)


def manage_session(request):
    sessions = Session.objects.all()
    context = {'sessions': sessions, 'page_title': 'Manage Sessions'}
    return render(request, "hod_template/manage_session.html", context)


def edit_session(request, session_id):
    instance = get_object_or_404(Session, id=session_id)
    form = SessionForm(request.POST or None, instance=instance)
    context = {'form': form, 'session_id': session_id,
               'page_title': 'Edit Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Updated")
                return redirect(reverse('edit_session', args=[session_id]))
            except Exception as e:
                messages.error(
                    request, "Session Could Not Be Updated " + str(e))
                return render(request, "hod_template/edit_session_template.html", context)
        else:
            messages.error(request, "Invalid Form Submitted ")
            return render(request, "hod_template/edit_session_template.html", context)

    else:
        return render(request, "hod_template/edit_session_template.html", context)


@csrf_exempt
def check_email_availability(request):
    email = request.POST.get("email")
    try:
        user = CustomUser.objects.filter(email=email).exists()
        if user:
            return HttpResponse(True)
        return HttpResponse(False)
    except Exception as e:
        return HttpResponse(False)


@csrf_exempt
def student_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStudent.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Student Feedback Messages'
        }
        return render(request, 'hod_template/student_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStudent, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def staff_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStaff.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Staff Feedback Messages'
        }
        return render(request, 'hod_template/staff_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStaff, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def view_staff_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStaff.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Staff'
        }
        return render(request, "hod_template/staff_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStaff, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


@csrf_exempt
def view_student_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStudent.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Students'
        }
        return render(request, "hod_template/student_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStudent, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


def admin_view_attendance(request):
    subjects = Subject.objects.all()
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'View Attendance'
    }

    return render(request, "hod_template/admin_view_attendance.html", context)


def manage_timetable(request):
    page_title = "Manage Timetable"
    room_form = RoomForm(prefix="room")
    entry_form = TimetableEntryForm(prefix="entry")

    if request.method == "POST":
        # Decide which action was submitted
        post_keys = list(request.POST.keys())
        if any(k.startswith("room-") for k in post_keys):
            room_form = RoomForm(request.POST, prefix="room")
            if room_form.is_valid():
                room_form.save()
                messages.success(request, "Room added")
                return redirect("manage_timetable")
            else:
                messages.error(request, "Please fix room form errors")
        elif any(k.startswith("entry-") for k in post_keys):
            entry_form = TimetableEntryForm(request.POST, prefix="entry")
            if entry_form.is_valid():
                try:
                    entry_form.save()
                    messages.success(request, "Timetable entry created")
                    return redirect("manage_timetable")
                except Exception as e:
                    messages.error(request, f"Error creating entry: {e}")
            else:
                messages.error(request, "Please fix timetable form errors")
        elif request.POST.get("erase_entries"):
            # Erase timetable entries for the selected session (or latest if not provided)
            session_id = request.POST.get("erase_session_id")
            session = None
            if session_id:
                try:
                    session = Session.objects.get(id=int(session_id))
                except (Session.DoesNotExist, ValueError):
                    session = None
            if session is None:
                session = Session.objects.order_by('-end_year').first()
            if session is None:
                messages.error(request, "No session found. Please create a session first.")
                return redirect("manage_timetable")

            deleted_count, _ = TimetableEntry.objects.filter(session=session).delete()
            messages.warning(request, f"Erased {deleted_count} timetable entr{'y' if deleted_count == 1 else 'ies'} for session {session}.")
            return redirect("manage_timetable")
        elif request.POST.get("auto_generate"):
            # One-click auto-generate using scheduling heuristic
            session = Session.objects.order_by('-end_year').first()
            if session is None:
                messages.error(request, "No session found. Please create a session first.")
                return redirect("manage_timetable")

            from .scheduling import generate_for_session

            summary = generate_for_session(session)
            created = summary.get("created", 0)
            skipped = summary.get("skipped", 0)
            errors = summary.get("errors", [])
            if created > 0:
                messages.success(request, f"Auto-generated {created} timetable entr{'y' if created == 1 else 'ies'} across all subjects.")
            else:
                messages.warning(request, "No entries generated. Ensure subjects have credits and free slots exist.")
            if skipped > 0:
                messages.info(request, f"Skipped {skipped} slot{'s' if skipped != 1 else ''} due to conflicts or validation.")
            if errors:
                messages.warning(request, f"{len(errors)} validation issues encountered during generation.")
            return redirect("manage_timetable")

    entries = TimetableEntry.objects.select_related("session", "course", "section", "subject", "staff", "room").order_by(
        "session__start_year", "day", "period_number"
    )

    sessions = Session.objects.order_by('-end_year')

    # Build audit summary for latest session
    latest_session = sessions.first()
    audit = None
    if latest_session:
        # Credits coverage per subject/section
        coverage = []
        for subj in Subject.objects.all():
            credits = int(getattr(subj, "credits", 0) or 0)
            for section in subj.sections.all():
                cnt = TimetableEntry.objects.filter(
                    session=latest_session,
                    subject=subj,
                    course=section.course,
                    section=section,
                ).count()
                status = "ok" if cnt == credits else ("under" if cnt < credits else "over")
                coverage.append({
                    "subject": subj.name,
                    "course": section.course.name,
                    "section": section.name,
                    "count": cnt,
                    "credits": credits,
                    "status": status,
                })

        # Conflicts (should be zero thanks to constraints; still compute for visibility)
        staff_conflicts = list(
            TimetableEntry.objects.filter(session=latest_session)
            .values("day", "period_number", "staff_id")
            .annotate(c=models.Count("id"))
            .filter(c__gt=1)
        )
        room_conflicts = list(
            TimetableEntry.objects.filter(session=latest_session)
            .values("day", "period_number", "room_id")
            .annotate(c=models.Count("id"))
            .filter(c__gt=1)
        )
        section_conflicts = list(
            TimetableEntry.objects.filter(session=latest_session)
            .values("day", "period_number", "section_id")
            .annotate(c=models.Count("id"))
            .filter(c__gt=1)
        )
        per_day_dupes = list(
            TimetableEntry.objects.filter(session=latest_session)
            .values("day", "section_id", "subject_id")
            .annotate(c=models.Count("id"))
            .filter(c__gt=1)
        )

        concurrency_slots = list(
            TimetableEntry.objects.filter(session=latest_session)
            .values("day", "period_number", "course_id")
            .annotate(sec_count=models.Count("section_id"))
            .filter(sec_count__gt=1)
        )

        audit = {
            "session": latest_session,
            "coverage": coverage,
            "conflicts": {
                "staff": staff_conflicts,
                "room": room_conflicts,
                "section": section_conflicts,
                "per_day_dupes": per_day_dupes,
            },
            "concurrency": concurrency_slots,
        }
    context = {
        "page_title": page_title,
        "room_form": room_form,
        "entry_form": entry_form,
        "entries": entries,
        "sessions": sessions,
        "audit": audit,
    }
    return render(request, "hod_template/manage_timetable.html", context)


def manage_extra_requests(request):
    page_title = "Manage Extra Class Requests"
    # Filter and sort
    status = request.GET.get("status")
    qs = ExtraClassRequest.objects.select_related("staff", "subject", "course", "session").order_by("-created_at")
    if status in {"requested", "approved", "scheduled", "rejected", "cancelled"}:
        qs = qs.filter(status=status)
    context = {
        "page_title": page_title,
        "requests": qs,
        "status": status or "all",
    }
    return render(request, "hod_template/manage_extra_requests.html", context)


@csrf_exempt
def update_extra_request_status(request, request_id: int):
    if request.method != "POST":
        return HttpResponse(status=405)
    action = request.POST.get("action")
    req = get_object_or_404(ExtraClassRequest, id=request_id)
    valid = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}
    if action not in valid:
        messages.error(request, "Invalid action")
        return redirect(reverse("manage_extra_requests"))
    new_status = valid[action]
    req.status = new_status
    req.save()
    # Notify staff
    note = f"Your extra class request for {req.subject} ({req.session}) is {new_status}."
    NotificationStaff.objects.create(staff=req.staff, message=note)
    TimetableAuditLog.objects.create(
        actor=request.user,
        action="extra_request",
        details=f"{new_status} {req.subject} by {req.staff}"
    )
    messages.success(request, f"Request {new_status}.")
    return redirect(reverse("manage_extra_requests"))


def extra_classes_dashboard(request):
    page_title = "Extra Classes Dashboard"
    status = request.GET.get("status")
    schedules = ExtraClassSchedule.objects.select_related("staff", "subject", "course").order_by("-start_datetime")
    if status in {"requested", "approved", "rejected", "scheduled", "cancelled"}:
        schedules = schedules.filter(status=status)

    # Aggregate unavailability counts per staff for display/color coding
    unavailability = StaffUnavailability.objects.values("staff_id").annotate(count=models.Count("id"))
    unavail_map = {u["staff_id"]: u["count"] for u in unavailability}
    # Attach count to each schedule for template access
    for s in schedules:
        s.unavail_count = unavail_map.get(s.staff_id, 0)

    context = {
        "page_title": page_title,
        "schedules": schedules,
        "status": status or "all",
        "unavail_map": unavail_map,
    }
    return render(request, "hod_template/extra_classes_dashboard.html", context)


def view_staff_unavailability(request):
    """List all staff unavailability entries for admins/HOD with basic filtering."""
    page_title = "Staff Unavailability"
    # Optional filters
    course_id = request.GET.get("course_id")
    staff_id = request.GET.get("staff_id")
    session_id = request.GET.get("session_id")
    day = request.GET.get("day")

    qs = StaffUnavailability.objects.select_related("staff", "session").order_by("-created_at")
    if course_id:
        qs = qs.filter(staff__course_id=course_id)
    if staff_id:
        qs = qs.filter(staff_id=staff_id)
    if session_id:
        qs = qs.filter(session_id=session_id)
    if day:
        qs = qs.filter(day=day)

    context = {
        "page_title": page_title,
        "entries": qs,
        "courses": Course.objects.all(),
        "staffs": Staff.objects.all(),
        "sessions": Session.objects.all(),
        "selected": {
            "course_id": course_id or "",
            "staff_id": staff_id or "",
            "session_id": session_id or "",
            "day": day or "",
        },
    }
    return render(request, "hod_template/staff_unavailability.html", context)


def admin_schedule_extra_class(request):
    page_title = "Schedule Extra Class (Admin)"
    form = AdminExtraClassScheduleForm(request.POST or None)
    recent = ExtraClassSchedule.objects.select_related("staff", "subject", "course").order_by("-start_datetime")[:25]
    context = {
        "page_title": page_title,
        "form": form,
        "recent": recent,
    }

    if request.method == "POST" and form.is_valid():
        sched = form.save(commit=False)
        sched.requires_hod_approval = False
        sched.status = "scheduled"
        try:
            with transaction.atomic():
                sched.full_clean()
                sched.save()
                # Notify the assigned staff
                NotificationStaff.objects.create(
                    staff=sched.staff,
                    message=f"Extra class scheduled: {sched.subject} on {sched.start_datetime}"
                )
                # Broadcast to all staff in the course
                try:
                    course_staff = Staff.objects.filter(course=sched.course).exclude(id=sched.staff_id)
                    msg_staff = f"Extra class scheduled for {sched.course.name}: {sched.subject.name} on {sched.start_datetime}"
                    for s in course_staff:
                        NotificationStaff.objects.create(staff=s, message=msg_staff)
                except Exception:
                    pass
                # Notify students in the course
                try:
                    students = Student.objects.filter(course=sched.course)
                    msg_student = f"Extra class scheduled: {sched.subject.name} on {sched.start_datetime}"
                    for stu in students:
                        NotificationStudent.objects.create(student=stu, message=msg_student)
                except Exception:
                    pass
                TimetableAuditLog.objects.create(
                    actor=request.user,
                    action="schedule_extra",
                    details=f"Admin scheduled {sched.subject} for {sched.staff} on {sched.start_datetime}"
                )
                # Create a TimetableEntry so it appears in staff/student timetables
                try:
                    # Map datetime to weekday and period
                    from datetime import time, timedelta
                    dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
                    weekday = dow_map.get(sched.start_datetime.weekday())
                    period_ranges = [
                        (time(9, 0), time(10, 0)),
                        (time(10, 0), time(11, 0)),
                        (time(11, 0), time(12, 0)),
                        (time(12, 0), time(13, 0)),
                        (time(13, 0), time(14, 0)),
                        (time(14, 0), time(15, 0)),
                    ]
                    st = sched.start_datetime.time()
                    period_number = None
                    for idx, (ps, pe) in enumerate(period_ranges, start=1):
                        if ps <= st < pe:
                            period_number = idx
                            break
                    duration_periods = max(1, int(round(sched.duration_minutes / 60)))
                    if sched.room and weekday in [c[0] for c in TimetableEntry.DAY_CHOICES] and period_number:
                        entry = TimetableEntry(
                            session=sched.session,
                            course=sched.course,
                            subject=sched.subject,
                            staff=sched.staff,
                            room=sched.room,
                            day=weekday,
                            period_number=period_number,
                            is_lab=False,
                            duration_periods=duration_periods,
                        )
                        entry.clean()
                        entry.save()
                    else:
                        messages.info(request, "Timetable not updated: ensure room is set and time falls within 9-15.")
                except Exception:
                    # Non-fatal; schedule remains recorded and visible on extra classes pages
                    pass
                messages.success(request, "Extra class scheduled successfully.")
                return redirect(reverse("admin_schedule_extra_class"))
        except Exception:
            messages.error(request, "Failed to schedule extra class. Please review form errors.")

    return render(request, "hod_template/extra_class_schedule_admin.html", context)


@csrf_exempt
def update_extra_class_status(request, schedule_id: int):
    if request.method != "POST":
        return HttpResponse(status=405)
    action = request.POST.get("action")
    sched = get_object_or_404(ExtraClassSchedule, id=schedule_id)
    valid = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}
    if action not in valid:
        messages.error(request, "Invalid action")
        return redirect(reverse("extra_classes_dashboard"))
    new_status = valid[action]
    sched.status = new_status
    sched.save()
    # Notify requesting staff
    note = f"Your extra class for {sched.subject} on {sched.start_datetime} is {new_status}."
    NotificationStaff.objects.create(staff=sched.staff, message=note)
    # If scheduled or cancelled, notify course teachers and students
    try:
        if new_status in ["scheduled", "approved"]:
            # Teachers in course
            others = Staff.objects.filter(course=sched.course).exclude(id=sched.staff_id)
            msg_staff = f"Extra class {new_status}: {sched.subject.name} on {sched.start_datetime}"
            for s in others:
                NotificationStaff.objects.create(staff=s, message=msg_staff)
        if new_status == "scheduled":
            students = Student.objects.filter(course=sched.course)
            msg_student = f"Extra class scheduled: {sched.subject.name} on {sched.start_datetime}"
            for stu in students:
                NotificationStudent.objects.create(student=stu, message=msg_student)
        if new_status == "cancelled":
            students = Student.objects.filter(course=sched.course)
            msg_student = f"Extra class cancelled: {sched.subject.name} on {sched.start_datetime}"
            for stu in students:
                NotificationStudent.objects.create(student=stu, message=msg_student)
    except Exception:
        pass
    TimetableAuditLog.objects.create(
        actor=request.user,
        action="extra_schedule_status",
        details=f"{new_status} {sched.subject} by {sched.staff}"
    )
    messages.success(request, f"Extra class {new_status}.")
    # If scheduled, add to weekly timetable
    try:
        if new_status == "scheduled":
            from datetime import time, timedelta
            dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
            weekday = dow_map.get(sched.start_datetime.weekday())
            period_ranges = [
                (time(9, 0), time(10, 0)),
                (time(10, 0), time(11, 0)),
                (time(11, 0), time(12, 0)),
                (time(12, 0), time(13, 0)),
                (time(13, 0), time(14, 0)),
                (time(14, 0), time(15, 0)),
            ]
            st = sched.start_datetime.time()
            period_number = None
            for idx, (ps, pe) in enumerate(period_ranges, start=1):
                if ps <= st < pe:
                    period_number = idx
                    break
            duration_periods = max(1, int(round(sched.duration_minutes / 60)))
            if sched.room and weekday in [c[0] for c in TimetableEntry.DAY_CHOICES] and period_number:
                entry = TimetableEntry(
                    session=sched.session,
                    course=sched.course,
                    subject=sched.subject,
                    staff=sched.staff,
                    room=sched.room,
                    day=weekday,
                    period_number=period_number,
                    is_lab=False,
                    duration_periods=duration_periods,
                )
                entry.clean()
                entry.save()
            else:
                messages.info(request, "Timetable not updated: set a room and a start time within 9-15.")
    except Exception:
        pass
    return redirect(reverse("extra_classes_dashboard"))


@csrf_exempt
def get_admin_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = get_object_or_404(
            Attendance, id=attendance_date_id, session=session)
        attendance_reports = AttendanceReport.objects.filter(
            attendance=attendance)
        json_data = []
        for report in attendance_reports:
            data = {
                "status":  str(report.status),
                "name": str(report.student)
            }
            json_data.append(data)
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        return None


def admin_view_profile(request):
    admin = get_object_or_404(Admin, admin=request.user)
    form = AdminForm(request.POST or None, request.FILES or None,
                     instance=admin)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                passport = request.FILES.get('profile_pic') or None
                custom_user = admin.admin
                if password != None:
                    custom_user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    custom_user.profile_pic = passport_url
                custom_user.first_name = first_name
                custom_user.last_name = last_name
                custom_user.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('admin_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
    return render(request, "hod_template/admin_view_profile.html", context)


def admin_notify_staff(request):
    staff = CustomUser.objects.filter(user_type=2)
    context = {
        'page_title': "Send Notifications To Staff",
        'allStaff': staff
    }
    return render(request, "hod_template/staff_notification.html", context)


def admin_notify_student(request):
    student = CustomUser.objects.filter(user_type=3)
    context = {
        'page_title': "Send Notifications To Students",
        'students': student
    }
    return render(request, "hod_template/student_notification.html", context)


@csrf_exempt
def send_student_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    student = get_object_or_404(Student, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('student_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': student.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStudent(student=student, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


@csrf_exempt
def send_staff_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    staff = get_object_or_404(Staff, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('staff_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': staff.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStaff(staff=staff, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def delete_staff(request, staff_id):
    staff = get_object_or_404(CustomUser, staff__id=staff_id)
    staff.delete()
    messages.success(request, "Staff deleted successfully!")
    return redirect(reverse('manage_staff'))


def delete_student(request, student_id):
    student = get_object_or_404(CustomUser, student__id=student_id)
    student.delete()
    messages.success(request, "Student deleted successfully!")
    return redirect(reverse('manage_student'))


def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        course.delete()
        messages.success(request, "Course deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some students are assigned to this course already. Kindly change the affected student course and try again")
    return redirect(reverse('manage_course'))


def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.delete()
    messages.success(request, "Subject deleted successfully!")
    return redirect(reverse('manage_subject'))


def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    try:
        session.delete()
        messages.success(request, "Session deleted successfully!")
    except Exception:
        messages.error(
            request, "There are students assigned to this session. Please move them to another session.")
    return redirect(reverse('manage_session'))
