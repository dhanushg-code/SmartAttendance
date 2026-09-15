"""Seed demo data so the UI has something to show.

Run:  python -m scripts.seed_demo
(DEMO_MODE=true only — uses the same in-memory DB as the running app.)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from database import students as student_service
from database.supabase_client import db
from exams import exams as exam_service
from fingerprint.verification import VerificationService


def main() -> None:
    if not student_service.subjects():
        for code, name in (("CN", "Computer Networks"), ("DS", "Data Structures"), ("DBMS", "Databases")):
            student_service.add_subject(code, name)

    if not student_service.list_students():
        for i in range(1, 21):  # 20 students
            student_service.add_student(
                register_no=str(100 + i),
                name=f"Student {i}",
                sclass="CSE-A",
                department="CSE",
            )
        # Bind demo fingerprints (simulated scanner: template id = register no)
        for stu in student_service.list_students():
            student_service.set_fingerprint(stu["id"], stu["register_no"])

    # Sample classroom attendance for the last 5 weekdays
    if not db.table("attendance").select("*").limit(1).execute().data:
        subject_id = student_service.subjects()[0]["id"]
        for d in range(5, 0, -1):
            day = (date.today() - timedelta(days=d)).isoformat()
            for stu in student_service.list_students()[:15]:
                t = (datetime.now() - timedelta(days=d)).strftime("%H:%M:%S")
                db.table("attendance").insert({
                    "student_id": stu["id"], "subject_id": subject_id,
                    "date": day, "entry_time": t, "status": "Present",
                }).execute()

    # Exam + hall + seats + eligibility + allocation
    if not exam_service.list_exams():
        exam = exam_service.create_exam(
            "Midterm DS", "Data Structures", date.today().isoformat(), "09:00", "11:00"
        )
        hall = exam_service.create_hall("Hall A", "B-101", 60)
        exam_service.create_seats(hall["id"], 60)
        ids = [s["id"] for s in student_service.list_students()[:20]]
        exam_service.set_eligible_students(exam["id"], ids)
        print(exam_service.allocate_seats(exam["id"]))

    # Staff members
    from database import staff as staff_service
    from database import timetable as timetable_service

    if not staff_service.list_staff():
        staff_data = [
            ("Dr. Alan Turing", "alan.turing@university.edu", "+1 555-0101", "tok_turing_01"),
            ("Prof. Ada Lovelace", "ada.lovelace@university.edu", "+1 555-0102", "tok_lovelace_02"),
            ("Dr. Grace Hopper", "grace.hopper@university.edu", "+1 555-0103", "tok_hopper_03"),
            ("Dr. Claude Shannon", "claude.shannon@university.edu", "+1 555-0104", "tok_shannon_04"),
        ]
        for name, email, phone, token in staff_data:
            staff_service.add_staff(name=name, email=email, phone=phone, device_token=token)

    # Weekly Timetable Schedule
    if not timetable_service.list_timetable():
        all_stf = staff_service.list_staff()
        all_sub = student_service.subjects()
        if all_stf and all_sub:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            period_times = {
                1: ("09:00", "10:00"),
                2: ("10:00", "11:00"),
                3: ("11:15", "12:15"),
                4: ("12:15", "13:15"),
            }
            rooms = ["Hall B-101", "Lab 2", "Hall B-103", "Seminar Hall 1"]
            for d_idx, day in enumerate(days):
                for p_no, (st, et) in period_times.items():
                    sub = all_sub[(d_idx + p_no) % len(all_sub)]
                    stf = all_stf[(d_idx + p_no) % len(all_stf)]
                    rm = rooms[(d_idx + p_no) % len(rooms)]
                    timetable_service.save_slot(
                        class_name="CSE-A",
                        day_of_week=day,
                        period_no=p_no,
                        start_time=st,
                        end_time=et,
                        subject_id=sub["id"],
                        staff_id=stf["id"],
                        room=rm,
                    )

    print("Demo data ready. Students:", len(student_service.list_students()), "Staff:", len(staff_service.list_staff()))


if __name__ == "__main__":
    main()
