"""Fingerprint enrollment: bind a scanner template id to a student row.

Spec section 17: the students table stores the scanner's template identifier
(``fingerprint_id``) — never raw fingerprint images.
"""
from __future__ import annotations

from typing import Any, Optional

from database.supabase_client import db
from fingerprint.scanner import ScannerService


class EnrollmentError(Exception):
    pass


class EnrollmentService:
    def __init__(self, scanner_service: Optional[ScannerService] = None) -> None:
        self.scanner_service = scanner_service or ScannerService()

    def scan_template(self) -> str:
        """Capture one scan and return the template id."""
        event = self.scanner_service.capture_once()
        if not event.success or not event.template_id:
            raise EnrollmentError(event.message or "Scan failed")
        return event.template_id

    def enroll_student(self, student_id: str, template_id: str) -> dict[str, Any]:
        """Save fingerprint_id on the student. Raises if the template is
        already bound to another student (one finger = one student)."""
        existing = (
            db.table("students")
            .select("*")
            .eq("fingerprint_id", template_id)
            .execute()
            .data
        )
        if existing:
            other = existing[0]
            if other.get("id") != student_id:
                raise EnrollmentError(
                    f"Fingerprint already registered to {other.get('name')} "
                    f"({other.get('register_no')})"
                )
        resp = db.table("students").update({"fingerprint_id": template_id}).eq("id", student_id).execute()
        if not resp.data:
            raise EnrollmentError(f"Student {student_id} not found")
        return resp.data[0]

    def is_enrolled(self, student_id: str) -> bool:
        rows = db.table("students").select("fingerprint_id").eq("id", student_id).execute().data
        return bool(rows and rows[0].get("fingerprint_id"))
