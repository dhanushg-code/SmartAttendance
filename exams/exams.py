"""Exam management: exams, eligibility, halls, seats, allocation, attendance."""
from __future__ import annotations

from typing import Any, Optional

from database.supabase_client import db


class ExamError(Exception):
    pass


# --- 19. Exams -------------------------------------------------------------------
def create_exam(exam_name: str, subject: str, exam_date: str,
                start_time: str, end_time: str) -> dict[str, Any]:
    resp = db.table("exams").insert({
        "exam_name": exam_name,
        "subject": subject,
        "exam_date": exam_date,
        "start_time": start_time,
        "end_time": end_time,
    }).execute()
    return resp.data[0]


def list_exams() -> list[dict[str, Any]]:
    return db.table("exams").select("*").order("exam_date").execute().data


# --- 20. Exam students (eligibility) ------------------------------------------------
def set_eligible_students(exam_id: str, student_ids: list[str]) -> int:
    """Bulk-insert eligibility rows; ignores already-added students."""
    existing = {
        r["student_id"]
        for r in db.table("exam_students").select("student_id").eq("exam_id", exam_id).execute().data
    }
    new = [{"exam_id": exam_id, "student_id": sid, "eligible": True}
           for sid in student_ids if sid not in existing]
    if new:
        db.table("exam_students").insert(new).execute()
    return len(new)


def is_eligible(exam_id: str, student_id: str) -> bool:
    rows = (
        db.table("exam_students")
        .select("eligible")
        .eq("exam_id", exam_id)
        .eq("student_id", student_id)
        .execute()
        .data
    )
    return bool(rows and rows[0]["eligible"])


def eligible_students(exam_id: str) -> list[dict[str, Any]]:
    return db.table("exam_students").select("*").eq("exam_id", exam_id).execute().data


# --- 21. Halls ------------------------------------------------------------------------
def create_hall(hall_name: str, room_number: str, capacity: int) -> dict[str, Any]:
    resp = db.table("halls").insert({
        "hall_name": hall_name,
        "room_number": room_number,
        "capacity": capacity,
    }).execute()
    return resp.data[0]


def list_halls() -> list[dict[str, Any]]:
    return db.table("halls").select("*").order("hall_name").execute().data


# --- 22. Seats ---------------------------------------------------------------------------
def create_seats(hall_id: str, count: int, prefix: str = "") -> list[dict[str, Any]]:
    """Create seat_number rows A-01..A-count for one hall."""
    existing = {
        r["seat_number"]
        for r in db.table("seats").select("seat_number").eq("hall_id", hall_id).execute().data
    }
    payload = []
    for i in range(1, count + 1):
        seat_number = f"{prefix}{i:02d}"
        if seat_number in existing:
            continue
        payload.append({"hall_id": hall_id, "seat_number": seat_number, "status": "AVAILABLE"})
    if payload:
        db.table("seats").insert(payload).execute()
    return payload


def seats_for_hall(hall_id: str) -> list[dict[str, Any]]:
    return db.table("seats").select("*").eq("hall_id", hall_id).order("seat_number").execute().data


# --- 23. Automatic seat allocation ----------------------------------------------------------
def allocate_seats(exam_id: str, hall_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """Assign every eligible student to the next free seat (spec section 14).

    Guarantees no two students share a seat: allocations are checked against
    both existing seat_allocations rows and seats already claimed in this run.
    """
    students = eligible_students(exam_id)
    eligible_ids = [r["student_id"] for r in students if r["eligible"]]

    already = {
        r["student_id"]: r
        for r in db.table("seat_allocations").select("*").eq("exam_id", exam_id).execute().data
    }
    taken_seat_ids = {r["seat_id"] for r in already.values()}

    halls = [h for h in list_halls() if not hall_ids or h["id"] in hall_ids]
    free_seats: list[dict[str, Any]] = []
    for hall in halls:
        for seat in seats_for_hall(hall["id"]):
            if seat["id"] not in taken_seat_ids and seat["status"] in ("AVAILABLE", "ALLOCATED"):
                free_seats.append({"hall": hall, "seat": seat})

    assigned, skipped = [], []
    claimed: set[str] = set()
    for sid in eligible_ids:
        if sid in already:
            continue  # keep prior allocation
        chosen = next((f for f in free_seats if f["seat"]["id"] not in claimed), None)
        if chosen is None:
            skipped.append(sid)
            continue
        claimed.add(chosen["seat"]["id"])
        assigned.append({
            "exam_id": exam_id,
            "student_id": sid,
            "hall_id": chosen["hall"]["id"],
            "seat_id": chosen["seat"]["id"],
        })

    if assigned:
        db.table("seat_allocations").insert(assigned).execute()
        for a in assigned:
            db.table("seats").update({"status": "ALLOCATED"}).eq("id", a["seat_id"]).execute()

    return {"assigned": len(assigned), "skipped": skipped}


def allocations_for_exam(exam_id: str) -> list[dict[str, Any]]:
    return db.table("seat_allocations").select("*").eq("exam_id", exam_id).execute().data


def allocation_for_student(exam_id: str, student_id: str) -> Optional[dict[str, Any]]:
    rows = (
        db.table("seat_allocations")
        .select("*")
        .eq("exam_id", exam_id)
        .eq("student_id", student_id)
        .execute()
        .data
    )
    return rows[0] if rows else None


# --- 24. Exam attendance ------------------------------------------------------------------------
def mark_exam_present(exam_id: str, student: dict[str, Any]) -> dict[str, Any]:
    """Verify + mark exam attendance (spec sections 10-12).

    Returns a result dict with display fields for the exam-verified screen.
    """
    student_id = student["id"]

    if not is_eligible(exam_id, student_id):
        return {
            "ok": False,
            "reason": "NOT ELIGIBLE FOR THIS EXAM",
            "detail": "Please contact the examination office.",
            "student": student,
        }

    allocation = allocation_for_student(exam_id, student_id)
    if not allocation:
        return {
            "ok": False,
            "reason": "NO SEAT ALLOCATED",
            "detail": "Seat allocation has not been done for this exam.",
            "student": student,
        }

    existing = (
        db.table("exam_attendance")
        .select("*")
        .eq("exam_id", exam_id)
        .eq("student_id", student_id)
        .execute()
        .data
    )
    if existing:
        row = existing[0]
        return {
            "ok": True,
            "duplicate": True,
            "message": f"Already verified at {row.get('verification_time')}",
            "allocation": allocation,
            "student": student,
        }

    db.table("exam_attendance").insert({
        "exam_id": exam_id,
        "student_id": student_id,
        "hall_id": allocation["hall_id"],
        "seat_id": allocation["seat_id"],
        "status": "Present",
    }).execute()
    db.table("seats").update({"status": "PRESENT"}).eq("id", allocation["seat_id"]).execute()

    return {"ok": True, "duplicate": False, "allocation": allocation, "student": student}


def exam_attendance_rows(exam_id: str) -> list[dict[str, Any]]:
    return db.table("exam_attendance").select("*").eq("exam_id", exam_id).execute().data
