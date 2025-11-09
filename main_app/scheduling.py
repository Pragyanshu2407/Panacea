from typing import List, Optional

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import (
    TimetableEntry,
    Session,
    Room,
    Subject,
)


DAYS = [choice[0] for choice in TimetableEntry._meta.get_field("day").choices]


def _find_free_room(session: Session, day: str, period: int) -> Optional[Room]:
    for room in Room.objects.all():
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
    subjects = Subject.objects.select_related("course", "staff").all()
    total_created = 0
    total_skipped = 0
    errors: List[str] = []

    for subject in subjects:
        credits = int(getattr(subject, "credits", 0) or 0)
        if credits <= 0:
            continue

        existing = TimetableEntry.objects.filter(session=session, subject=subject).count()
        remaining = max(0, credits - existing)
        if remaining == 0:
            continue

        is_lab = _is_lab_subject(subject)
        duration = 2 if is_lab else 1

        created_for_subject = 0
        for day in DAYS:
            if created_for_subject >= remaining:
                break

            # Iterate possible periods; for lab need P1..P5 for 2-block
            max_start = 5 if is_lab else 6
            for period in range(1, max_start + 1):
                if created_for_subject >= remaining:
                    break

                # Skip if staff or course busy at starting slot; subsequent conflicts checked by clean
                if TimetableEntry.objects.filter(session=session, day=day, period_number=period, staff=subject.staff).exists():
                    total_skipped += 1
                    continue
                if TimetableEntry.objects.filter(session=session, day=day, period_number=period, course=subject.course).exists():
                    total_skipped += 1
                    continue

                room = _find_free_room(session, day, period)
                if room is None:
                    total_skipped += 1
                    continue

                entry = TimetableEntry(
                    session=session,
                    course=subject.course,
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
                        created_for_subject += 1
                        total_created += 1
                except ValidationError as e:
                    total_skipped += 1
                    errors.append(f"{subject.name} on {day} P{period}: {e}")
                except Exception as e:
                    total_skipped += 1
                    errors.append(f"{subject.name} on {day} P{period}: {e}")

    return {
        "created": total_created,
        "skipped": total_skipped,
        "errors": errors,
    }