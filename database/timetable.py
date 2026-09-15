"""Timetable CRUD service for managing weekly schedules."""
from __future__ import annotations

from typing import Any, Optional

from database.supabase_client import db


class TimetableError(Exception):
    pass


DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def list_timetable(class_name: str | None = None, day_of_week: str | None = None) -> list[dict[str, Any]]:
    """Return timetable entries, optionally filtered by class and/or day_of_week."""
    q = db.table("timetable").select("*")
    if class_name:
        q = q.eq("class", class_name)
    if day_of_week:
        q = q.eq("day_of_week", day_of_week)
    rows = q.order("period_no").execute().data
    return rows


def get_timetable_entry(entry_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single timetable record by its primary key ID."""
    rows = db.table("timetable").select("*").eq("id", entry_id).execute().data
    return rows[0] if rows else None


def get_slot(class_name: str, day_of_week: str, period_no: int) -> Optional[dict[str, Any]]:
    """Retrieve slot by unique constraint (class, day_of_week, period_no)."""
    rows = (
        db.table("timetable")
        .select("*")
        .eq("class", class_name)
        .eq("day_of_week", day_of_week)
        .eq("period_no", period_no)
        .execute()
        .data
    )
    return rows[0] if rows else None


def save_slot(
    class_name: str,
    day_of_week: str,
    period_no: int,
    start_time: str,
    end_time: str,
    subject_id: str | None = None,
    staff_id: str | None = None,
    room: str = "",
) -> dict[str, Any]:
    """Insert or update a timetable slot enforcing the unique constraint."""
    if not class_name or not day_of_week or not period_no:
        raise TimetableError("Class, day of week, and period number are required")
    if not start_time or not end_time:
        raise TimetableError("Start time and end time are required")

    existing = get_slot(class_name, day_of_week, period_no)
    payload = {
        "class": class_name,
        "day_of_week": day_of_week,
        "period_no": int(period_no),
        "start_time": start_time,
        "end_time": end_time,
        "subject_id": subject_id or None,
        "staff_id": staff_id or None,
        "room": room.strip() or None,
    }

    if existing:
        resp = db.table("timetable").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    else:
        resp = db.table("timetable").insert(payload).execute()
        return resp.data[0]


def delete_slot(class_name: str, day_of_week: str, period_no: int) -> None:
    """Delete the timetable record matching (class, day_of_week, period_no)."""
    existing = get_slot(class_name, day_of_week, period_no)
    if existing:
        delete_entry(existing["id"])


def delete_entry(entry_id: str) -> None:
    """Delete a timetable record by its primary key ID."""
    db.table("timetable").delete().eq("id", entry_id).execute()


def get_weekly_grid(class_name: str) -> dict[str, dict[int, dict[str, Any]]]:
    """Return a nested dict: {day_of_week: {period_no: enriched_slot_data}}."""
    entries = list_timetable(class_name=class_name)
    enriched = [enrich_slot(e) for e in entries]

    grid: dict[str, dict[int, dict[str, Any]]] = {day: {} for day in DAYS_OF_WEEK}
    for item in enriched:
        day = item.get("day_of_week")
        p_no = item.get("period_no")
        if day in grid and p_no is not None:
            grid[day][int(p_no)] = item
    return grid


def enrich_slot(slot: dict[str, Any]) -> dict[str, Any]:
    """Attach subject and staff details to the slot dictionary."""
    enriched = dict(slot)
    subject_id = slot.get("subject_id")
    staff_id = slot.get("staff_id")

    enriched["subject_name"] = ""
    enriched["subject_code"] = ""
    if subject_id:
        sub_rows = db.table("subjects").select("*").eq("id", subject_id).execute().data
        if sub_rows:
            enriched["subject_name"] = sub_rows[0].get("name", "")
            enriched["subject_code"] = sub_rows[0].get("code", "")

    enriched["staff_name"] = ""
    enriched["staff_email"] = ""
    enriched["staff_phone"] = ""
    if staff_id:
        staff_rows = db.table("staff").select("*").eq("id", staff_id).execute().data
        if staff_rows:
            enriched["staff_name"] = staff_rows[0].get("name", "")
            enriched["staff_email"] = staff_rows[0].get("email", "")
            enriched["staff_phone"] = staff_rows[0].get("phone", "")

    return enriched


def list_distinct_classes() -> list[str]:
    """Return a sorted list of all classes found across students and timetable."""
    classes = set()
    try:
        stu_rows = db.table("students").select("class").execute().data
        for r in stu_rows:
            c = r.get("class")
            if c:
                classes.add(c.strip())
    except Exception:
        pass

    try:
        tt_rows = db.table("timetable").select("class").execute().data
        for r in tt_rows:
            c = r.get("class")
            if c:
                classes.add(c.strip())
    except Exception:
        pass

    default_classes = ["CSE-A", "CSE-B", "ECE-A", "ECE-B", "IT-A", "MECH-A"]
    for dc in default_classes:
        classes.add(dc)

    return sorted(classes)
