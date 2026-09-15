"""End-to-end backend smoke test (demo mode, no Qt). Run: python tests/smoke_test.py"""
from __future__ import annotations

import builtins
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

assert settings.DEMO_MODE, "smoke test requires DEMO_MODE=true"

from database import auth, staff as staff_service, students as student_service, timetable as timetable_service  # noqa: E402
from database.supabase_client import db  # noqa: E402
from exams import exams as exam_service  # noqa: E402
from fingerprint.scanner import ScanEvent, SimulatedScanner  # noqa: E402
from fingerprint.verification import VerificationService  # noqa: E402
from attendance.attendance import AttendanceService  # noqa: E402
from excel.excel_export import export_daily, export_exam_attendance  # noqa: E402
from scripts.seed_demo import main as seed  # noqa: E402
from tests.test_alerts import run_tests as test_alerts_run  # noqa: E402


def fake_input(_prompt: str = "") -> str:
    return "101"


builtins.input = fake_input

# 1. seed -----------------------------------------------------------------------
seed()

students = student_service.list_students()
assert len(students) == 20, f"expected 20 students, got {len(students)}"
assert students[0]["fingerprint_id"] == "101"

# 2. login --------------------------------------------------------------------------
assert auth.login("admin", "admin123"), "admin login should succeed"
assert not auth.login("admin", "wrong"), "bad password must fail"

# 3. classroom attendance + duplicate prevention -------------------------------------
svc = AttendanceService()
subject_id = student_service.subjects()[0]["id"]
stu101 = student_service.get_student_by_register_no("101")
stu102 = student_service.get_student_by_register_no("102")

first = svc.mark_present(stu101, subject_id)
assert first.ok and not first.duplicate, "first scan should mark present"

dup = svc.mark_present(stu101, subject_id)
assert dup.duplicate and not dup.ok, "second scan same day must be duplicate"

second = svc.mark_present(stu102, subject_id)
assert second.ok, "different student should mark fine"

stats = svc.dashboard_stats()
assert stats["present"] >= 2, "dashboard present count should include new marks"

# 4. verification flow ----------------------------------------------------------------
scanner = SimulatedScanner()
scanner.open()
verifier = VerificationService()
event = ScanEvent("101", True)
ident = verifier.identify_event(event)
assert ident.success and ident.student["register_no"] == "101"
assert not verifier.identify_event(ScanEvent("999", True)).success

# 5. exam flow ---------------------------------------------------------------------------
exams_list = exam_service.list_exams()
assert exams_list, "seed should create an exam"
exam = exams_list[0]
assert exam_service.is_eligible(exam["id"], stu101["id"])
assert not exam_service.is_eligible(exam["id"], "nonexistent-id")

# fresh student not registered for exam
all_students = student_service.list_students()
extra = None
for s in all_students:
    if not exam_service.is_eligible(exam["id"], s["id"]):
        extra = s
        break
if extra:
    res = exam_service.mark_exam_present(exam["id"], extra)
    assert not res["ok"] and res["reason"] == "NOT ELIGIBLE FOR THIS EXAM"

# seat allocation
alloc_summary = exam_service.allocate_seats(exam["id"])
alloc = exam_service.allocation_for_student(exam["id"], stu101["id"])
assert alloc, "student 101 should have a seat"

res = exam_service.mark_exam_present(exam["id"], stu101)
assert res["ok"] and not res["duplicate"], "exam verification should succeed"
seat_id = alloc["seat_id"]
seat_status = [s["status"] for s in exam_service.seats_for_hall(alloc["hall_id"]) if s["id"] == seat_id][0]
assert seat_status == "PRESENT", f"seat should be PRESENT, got {seat_status}"

dup_exam = exam_service.mark_exam_present(exam["id"], stu101)
assert dup_exam["ok"] and dup_exam["duplicate"], "second exam scan must be duplicate"

# unique exam_id+seat: allocate again, ensure no seat reused for a new student
allocations = exam_service.allocations_for_exam(exam["id"])
seat_ids = [a["seat_id"] for a in allocations]
assert len(seat_ids) == len(set(seat_ids)), "no two students may share a seat"

# 6. excel export ------------------------------------------------------------------------
daily_path = export_daily()
assert daily_path.exists() and daily_path.stat().st_size > 0, "daily excel must be written"
exam_path = export_exam_attendance(exam)
assert exam_path.exists() and exam_path.stat().st_size > 0, "exam excel must be written"

# 7. staff CRUD --------------------------------------------------------------------------
staff_list = staff_service.list_staff()
assert len(staff_list) >= 4, f"expected at least 4 staff, got {len(staff_list)}"
new_staff = staff_service.add_staff("Dr. Smoke Test", "smoke@test.edu", "+1 555-0000", "tok_smoke")
assert new_staff["name"] == "Dr. Smoke Test"
assert staff_service.get_staff_by_email("smoke@test.edu") is not None
staff_service.update_staff(new_staff["id"], phone="+1 555-1111")
updated_stf = staff_service.get_staff(new_staff["id"])
assert updated_stf["phone"] == "+1 555-1111"
staff_service.delete_staff(new_staff["id"])
assert staff_service.get_staff(new_staff["id"]) is None

# 8. timetable CRUD ----------------------------------------------------------------------
tt_list = timetable_service.list_timetable()
assert len(tt_list) >= 1, "expected timetable slots from seed"
saved_slot = timetable_service.save_slot(
    class_name="CSE-A",
    day_of_week="Monday",
    period_no=6,
    start_time="15:00",
    end_time="16:00",
    room="Lab 5",
)
assert saved_slot["period_no"] == 6
fetched_slot = timetable_service.get_slot("CSE-A", "Monday", 6)
assert fetched_slot is not None and fetched_slot["room"] == "Lab 5"
# Upsert with different room
timetable_service.save_slot(
    class_name="CSE-A",
    day_of_week="Monday",
    period_no=6,
    start_time="15:00",
    end_time="16:00",
    room="Lab 6",
)
assert timetable_service.get_slot("CSE-A", "Monday", 6)["room"] == "Lab 6"
timetable_service.delete_slot("CSE-A", "Monday", 6)
assert timetable_service.get_slot("CSE-A", "Monday", 6) is None

# 9. period alerts & notifiers -----------------------------------------------------------
test_alerts_run()

print("SMOKE OK")
print("daily report :", daily_path)
print("exam report  :", exam_path)
