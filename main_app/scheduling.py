from typing import List, Optional
import random

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import (
    TimetableEntry,
    Session,
    Room,
    Subject,
    StaffUnavailability,
)


DAYS = [choice[0] for choice in TimetableEntry._meta.get_field("day").choices]


def _find_free_room(session: Session, day: str, period: int) -> Optional[Room]:
    # Iterate rooms in random order to avoid always picking the first room
    rooms = list(Room.objects.all())
    random.shuffle(rooms)
    for room in rooms:
        if not TimetableEntry.objects.filter(session=session, day=day, period_number=period, room=room).exists():
            return room
    return None


def _is_lab_subject(subject: Subject) -> bool:
    name = (subject.name or "").lower()
    return "lab" in name or "practical" in name


def generate_for_session(session: Session) -> dict:
    """
    Greedy heuristic generator that schedules subjects up to their weekly credits.
    Respects:
    - No consecutive classes for the same subject (enforced by TimetableEntry.clean)
    - Max one class per subject per day (enforced by TimetableEntry.clean)
    - Labs scheduled as 2-hour blocks when detected
    - Avoids staff/course/room conflicts
    Returns summary dict with counts.
    """
    # Randomize subject order to avoid linear filling across subjects
    subjects = list(
        Subject.objects.select_related("staff").prefetch_related("courses", "sections").all()
    )
    random.shuffle(subjects)
    total_created = 0
    total_skipped = 0
    errors: List[str] = []

    for subject in subjects:
        credits = int(getattr(subject, "credits", 0) or 0)
        if credits <= 0:
            continue

        # Schedule per course offering
        subject_courses = list(subject.courses.all())
        if not subject_courses:
            continue

        is_lab = _is_lab_subject(subject)
        duration = 2 if is_lab else 1

        # Randomize day order so classes distribute across the week non-linearly
        day_order = DAYS[:]
        random.shuffle(day_order)

        for course in subject_courses:
            # Determine sections of this course this subject is offered in
            sections_for_course = list(subject.sections.filter(course=course))
            if not sections_for_course:
                # If no section assignments, skip scheduling for this course to ensure section-based timetables
                continue

            for section in sections_for_course:
                existing = TimetableEntry.objects.filter(
                    session=session, subject=subject, course=course, section=section
                ).count()
                remaining = max(0, credits - existing)
                if remaining == 0:
                    continue

                created_for_subject_section = 0
                for day in day_order:
                    if created_for_subject_section >= remaining:
                        break

                    # Iterate possible periods; for lab need P1..P5 for 2-block
                    max_start = 5 if is_lab else 6
                    # Randomize period order so we don't always fill mornings first
                    period_order = list(range(1, max_start + 1))
                    random.shuffle(period_order)
                    for period in period_order:
                        if created_for_subject_section >= remaining:
                            break

                        # Skip if staff or section busy at starting slot; subsequent conflicts checked by clean
                        if TimetableEntry.objects.filter(
                            session=session, day=day, period_number=period, staff=subject.staff
                        ).exists():
                            total_skipped += 1
                            continue
                        if TimetableEntry.objects.filter(
                            session=session, day=day, period_number=period, section=section
                        ).exists():
                            total_skipped += 1
                            continue

                        # Skip if staff marked unavailable for this slot (respect duration)
                        duration_span = 2 if is_lab else 1
                        unavail = StaffUnavailability.objects.filter(
                            staff=subject.staff,
                            session=session,
                            day=day,
                        )
                        unavailable_here = False
                        for ua in unavail:
                            covered = set(range(ua.period_number, ua.period_number + int(ua.duration_periods)))
                            if set(range(period, period + duration_span)) & covered:
                                unavailable_here = True
                                break
                        if unavailable_here:
                            total_skipped += 1
                            continue

                        room = _find_free_room(session, day, period)
                        if room is None:
                            total_skipped += 1
                            continue

                        entry = TimetableEntry(
                            session=session,
                            course=course,
                            section=section,
                            subject=subject,
                            staff=subject.staff,
                            room=room,
                            day=day,
                            period_number=period,
                            is_lab=is_lab,
                            duration_periods=duration,
                        )

                        try:
                            with transaction.atomic():
                                entry.full_clean()
                                entry.save()
                                created_for_subject_section += 1
                                total_created += 1
                        except ValidationError as e:
                            total_skipped += 1
                            errors.append(
                                f"{subject.name} ({course.name} / {section.name}) on {day} P{period}: {e}"
                            )
                        except Exception as e:
                            total_skipped += 1
                            errors.append(
                                f"{subject.name} ({course.name} / {section.name}) on {day} P{period}: {e}"
                            )

    return {
        "created": total_created,
        "skipped": total_skipped,
        "errors": errors,
    }