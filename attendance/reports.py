"""Attendance reporting and monthly aggregation helpers."""
from __future__ import annotations

from typing import Any

from database.supabase_client import db


def monthly_summary(year: int, month: int) -> dict[str, Any]:
    """Aggregate present counts per day for a given year and month."""
    prefix = f"{year:04d}-{month:02d}"
    rows = db.table("attendance").select("date, student_id").execute().data

    per_day: dict[str, int] = {}
    for r in rows:
        d = str(r.get("date") or "")
        if d.startswith(prefix):
            per_day[d] = per_day.get(d, 0) + 1

    return {"per_day": dict(sorted(per_day.items()))}


class AttendanceReportService:
    def __init__(self) -> None:
        self.db = db

    def fetch_attendance_by_date_range(
        self, start_date: str, end_date: str, subject_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            self.db.table("attendance")
            .select("*, students(*), subjects(*)")
            .gte("date", start_date)
            .lte("date", end_date)
        )
        if subject_id:
            query = query.eq("subject_id", subject_id)
        return query.execute().data or []
