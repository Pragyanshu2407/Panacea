from django import forms
from django.forms.widgets import DateInput, TextInput

from .models import *
from . import models


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'


class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'gender',  'password','profile_pic', 'address' ]


class StudentForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields + [
            'course', 'session', 'section', 'semester'
        ]


class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields


class StaffForm(CustomUserForm):
    class SectionMultipleChoiceField(forms.ModelMultipleChoiceField):
        def label_from_instance(self, obj):
            return obj.name  # show only 'A', 'B', 'C', 'D'

    def __init__(self, *args, **kwargs):
        super(StaffForm, self).__init__(*args, **kwargs)
        # Order semesters and filter sections by selected course
        self.fields['semesters'].queryset = Semester.objects.order_by('number')
        # Improve checkbox rendering with a CSS class
        self.fields['sections'].widget.attrs['class'] = 'checkbox-list'
        self.fields['semesters'].widget.attrs['class'] = 'checkbox-list'

        # Default: no sections until a course is chosen
        course_obj = None
        try:
            if self.data and self.data.get('course'):
                course_obj = Course.objects.filter(id=int(self.data.get('course'))).first()
        except (ValueError, TypeError):
            course_obj = None

        if not course_obj and getattr(self.instance, 'course_id', None):
            course_obj = self.instance.course

        self.fields['sections'].queryset = (
            Section.objects.filter(course=course_obj) if course_obj else Section.objects.none()
        )

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields + ['course', 'sections', 'semesters']
        widgets = {
            'sections': forms.CheckboxSelectMultiple(),
            'semesters': forms.CheckboxSelectMultiple(),
        }

    # Override sections field to control labels
    sections = SectionMultipleChoiceField(queryset=Section.objects.none(), required=False, widget=forms.CheckboxSelectMultiple())


class CourseForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name']
        model = Course


class SubjectForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Subject
        fields = ['name', 'staff', 'courses', 'sections', 'semester', 'credits']
        widgets = {
            'courses': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'sections': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


class SessionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Session
        fields = '__all__'
        widgets = {
            'start_year': DateInput(attrs={'type': 'date'}),
            'end_year': DateInput(attrs={'type': 'date'}),
        }


class LeaveReportStaffForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStaff
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStaffForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStaff
        fields = ['feedback']


class LeaveReportStudentForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStudent
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStudentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStudent
        fields = ['feedback']


class StudentEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields 


class StaffEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields


class EditResultForm(FormSettings):
    session_list = Session.objects.all()
    session_year = forms.ModelChoiceField(
        label="Session Year", queryset=session_list, required=True)

    def __init__(self, *args, **kwargs):
        super(EditResultForm, self).__init__(*args, **kwargs)

    class Meta:
        model = StudentResult
        fields = ['session_year', 'subject', 'student', 'test', 'exam']

#todos
# class TodoForm(forms.ModelForm):
#     class Meta:
#         model=Todo
#         fields=["title","is_finished"]

#issue book

class IssueBookForm(forms.Form):
    isbn2 = forms.ModelChoiceField(queryset=models.Book.objects.all(), empty_label="Book Name [ISBN]", to_field_name="isbn", label="Book (Name and ISBN)")
    name2 = forms.ModelChoiceField(queryset=models.Student.objects.all(), empty_label="Name ", to_field_name="", label="Student Details")
    
    isbn2.widget.attrs.update({'class': 'form-control'})
    name2.widget.attrs.update({'class':'form-control'})


# Timetable forms
class RoomForm(forms.ModelForm):
    class Meta:
        model = models.Room
        fields = ["name", "capacity"]


class TimetableEntryForm(forms.ModelForm):
    class Meta:
        model = models.TimetableEntry
        fields = [
            "session",
            "course",
            "section",
            "subject",
            "staff",
            "room",
            "day",
            "period_number",
            "is_lab",
            "duration_periods",
        ]
        widgets = {
            "period_number": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
            "is_lab": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "duration_periods": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
        }

class ExtraClassRequestForm(forms.ModelForm):
    class Meta:
        model = models.ExtraClassRequest
        fields = [
            "subject",
            "course",
            "session",
            "preferred_day",
            "preferred_period",
            "duration_periods",
            "is_lab",
            "reason",
        ]
        widgets = {
            "preferred_period": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
            "duration_periods": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
            "is_lab": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "reason": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit subjects to those taught by requesting staff (if provided)
        if staff is not None:
            self.fields["subject"].queryset = models.Subject.objects.filter(staff=staff)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()

class StaffUnavailabilityForm(forms.ModelForm):
    class Meta:
        model = models.StaffUnavailability
        fields = [
            "session",
            "day",
            "period_number",
            "duration_periods",
            "reason_code",
            "reason",
            "recurring_weekly",
            "repeat_until",
            "exception_date",
        ]
        widgets = {
            "period_number": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
            "duration_periods": forms.NumberInput(attrs={"min": 1, "max": 6, "class": "form-control"}),
            "reason": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "repeat_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "exception_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class ExtraClassScheduleForm(forms.ModelForm):
    # Ensure browser "datetime-local" input parses correctly
    start_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control datetimepicker-input",
                "data-target": "#datetimepicker1",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        required=True,
    )
    class Meta:
        model = models.ExtraClassSchedule
        fields = [
            "session",
            "course",
            "subject",
            "room",
            "start_datetime",
            "duration_minutes",
            "notes",
        ]
        widgets = {
            "duration_minutes": forms.NumberInput(attrs={"min": 15, "step": 15, "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class AdminExtraClassScheduleForm(forms.ModelForm):
    staff = forms.ModelChoiceField(queryset=models.Staff.objects.all(), required=True, label="Teacher")
    # Match the parsing behavior for admin as well
    start_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control datetimepicker-input",
                "data-target": "#datetimepicker1",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        required=True,
    )

    class Meta:
        model = models.ExtraClassSchedule
        fields = [
            "staff",
            "session",
            "course",
            "subject",
            "room",
            "start_datetime",
            "duration_minutes",
            "notes",
        ]
        widgets = {
            "duration_minutes": forms.NumberInput(attrs={"min": 15, "step": 15, "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure consistent styling
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()

        # Dynamically restrict course/subject based on chosen staff
        staff_obj = None
        # Prefer bound data, fall back to initial
        staff_id = None
        if self.data.get("staff"):
            try:
                staff_id = int(self.data.get("staff"))
            except (TypeError, ValueError):
                staff_id = None
        if staff_id is None and self.initial.get("staff"):
            try:
                staff_id = int(self.initial.get("staff"))
            except (TypeError, ValueError):
                staff_id = None

        if staff_id:
            try:
                staff_obj = models.Staff.objects.get(id=staff_id)
            except models.Staff.DoesNotExist:
                staff_obj = None

        if staff_obj is not None:
            self.fields["subject"].queryset = models.Subject.objects.filter(staff=staff_obj)
            if staff_obj.course_id:
                self.fields["course"].queryset = models.Course.objects.filter(id=staff_obj.course_id)


# Proctor and Fee Payment forms
class ProctorAssignmentForm(forms.ModelForm):
    class Meta:
        model = models.ProctorAssignment
        fields = ["proctor", "student", "active"]


class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = models.FeePayment
        fields = ["session", "amount", "receipt"]


# Auto-generate timetable form
class AutoGenerateTimetableForm(forms.Form):
    session = forms.ModelChoiceField(queryset=models.Session.objects.all(), required=True, label="Session")
    course = forms.ModelChoiceField(queryset=models.Course.objects.all(), required=True, label="Course")
    subject = forms.ModelChoiceField(queryset=models.Subject.objects.all(), required=True, label="Subject")
    staff = forms.ModelChoiceField(queryset=models.Staff.objects.all(), required=True, label="Staff")
    room = forms.ModelChoiceField(queryset=models.Room.objects.all(), required=True, label="Room")
    classes_per_week = forms.IntegerField(required=False, min_value=1, max_value=30, label="Classes per week")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()

# Notes upload form for staff
class NoteUploadForm(forms.ModelForm):
    class Meta:
        model = models.Note
        fields = ["title", "subject", "file"]

    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit subjects to ones taught by this staff
        if staff is not None:
            self.fields["subject"].queryset = models.Subject.objects.filter(staff=staff)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()


# MCQ Test creation form
class MCQTestForm(forms.ModelForm):
    class Meta:
        model = models.MCQTest
        fields = ["title", "subject", "is_active"]

    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        if staff is not None:
            self.fields["subject"].queryset = models.Subject.objects.filter(staff=staff)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()


# MCQ Question + options form (single question at a time)
class MCQQuestionCreateForm(forms.Form):
    question_text = forms.CharField(widget=forms.Textarea, label="Question")
    option1 = forms.CharField(label="Option 1")
    option2 = forms.CharField(label="Option 2")
    option3 = forms.CharField(label="Option 3")
    option4 = forms.CharField(label="Option 4")
    correct_option = forms.ChoiceField(
        choices=[("1", "Option 1"), ("2", "Option 2"), ("3", "Option 3"), ("4", "Option 4")],
        label="Correct Option",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
