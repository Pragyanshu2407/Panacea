from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


class UserModel(UserAdmin):
    ordering = ('email',)


def erase_timetable_for_sessions(modeladmin, request, queryset):
    # Delete all TimetableEntry rows tied to the selected sessions
    deleted_count, _ = TimetableEntry.objects.filter(session__in=queryset).delete()
    messages.warning(request, f"Erased {deleted_count} timetable entries for selected sessions.")
erase_timetable_for_sessions.short_description = "Erase timetable entries for selected sessions"


class SessionAdmin(admin.ModelAdmin):
    list_display = ("start_year", "end_year")
    actions = [erase_timetable_for_sessions]


class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "day",
        "period_number",
        "course",
        "section",
        "subject",
        "staff",
        "room",
        "is_lab",
        "duration_periods",
    )
    list_filter = ("session", "day", "course", "section", "subject", "staff", "is_lab")


admin.site.register(CustomUser, UserModel)
admin.site.register(Staff)
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(Book)
admin.site.register(IssuedBook)
admin.site.register(Library)
admin.site.register(Subject)
admin.site.register(Session, SessionAdmin)
admin.site.register(TimetableEntry, TimetableEntryAdmin)
admin.site.register(ExtraClassSchedule)
