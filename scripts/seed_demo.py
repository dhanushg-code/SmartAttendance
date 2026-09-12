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

    print("Demo data ready. Students:", len(student_service.list_students()))


if __name__ == "__main__":
    main()
