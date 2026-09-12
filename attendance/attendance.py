"""Classroom attendance service: recording scans, duplicate prevention, and dashboard stats."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from database.supabase_client import db


@dataclass
class MarkResult:
    ok: bool
    duplicate: bool = False
    message: str = ""


class AttendanceService:
    def __init__(self) -> None:
        self.db = db

    def mark_present(self, student: dict[str, Any], subject_id: str) -> MarkResult:
        """Mark a student present for a subject today with duplicate check."""
        today_s = date.today().isoformat()
        student_id = student["id"]

        # Duplicate check: student already marked for this subject today
        existing = (
            self.db.table("attendance")
            .select("*")
            .eq("student_id", student_id)
            .eq("subject_id", subject_id)
            .eq("date", today_s)
            .execute()
            .data
        )
        if existing:
            t = str(existing[0].get("entry_time") or "")[:5]
            return MarkResult(
                ok=False,
                duplicate=True,
                message=f"already marked present today at {t}",
            )

        now_time = datetime.now().strftime("%H:%M:%S")
        record = {
            "student_id": student_id,
            "subject_id": subject_id,
            "date": today_s,
            "entry_time": now_time,
            "status": "PRESENT",
        }
        self.db.table("attendance").insert(record).execute()
        return MarkResult(
            ok=True,
            duplicate=False,
            message=f"marked present at {now_time[:5]}",
        )

    def today_rows(self, subject_id: str | None = None) -> list[dict[str, Any]]:
        """Return attendance rows for today, optionally filtered by subject."""
        today_s = date.today().isoformat()
        query = self.db.table("attendance").select("*").eq("date", today_s)
        if subject_id:
            query = query.eq("subject_id", subject_id)
        return query.order("entry_time", desc=True).execute().data

    def dashboard_stats(self) -> dict[str, Any]:
        """Compute today's total students, present, absent, and attendance percentage."""
        today_s = date.today().isoformat()
        total_students = len(self.db.table("students").select("id").execute().data)

        today_records = (
            self.db.table("attendance")
            .select("student_id")
            .eq("date", today_s)
            .execute()
            .data
        )
        present_count = len({r["student_id"] for r in today_records})
        absent_count = max(0, total_students - present_count)
        percent = (present_count / total_students * 100.0) if total_students > 0 else 0.0

        return {
            "total": total_students,
            "present": present_count,
            "absent": absent_count,
            "percent": percent,
            "date": today_s,
        }

    # Backward-compatible helpers
    def mark_classroom_attendance(self, fingerprint_id: str, subject_id: str) -> tuple[bool, dict | None, str]:
        student_res = self.db.table("students").select("*").eq("fingerprint_id", fingerprint_id).execute()
        if not student_res.data:
            return False, None, "Fingerprint not recognized or student not registered."
        student = student_res.data[0]
        res = self.mark_present(student, subject_id)
        return res.ok, student, res.message

    def get_todays_attendance(self, subject_id: str | None = None) -> list[dict[str, Any]]:
        return self.today_rows(subject_id)
