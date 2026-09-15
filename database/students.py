"""Student CRUD service (spec section 25: student management)."""
from __future__ import annotations

from typing import Any, Optional

from database.supabase_client import db


class StudentError(Exception):
    pass


def list_students() -> list[dict[str, Any]]:
    return db.table("students").select("*").order("register_no").execute().data


def get_student(student_id: str) -> Optional[dict[str, Any]]:
    rows = db.table("students").select("*").eq("id", student_id).execute().data
    return rows[0] if rows else None


def get_student_by_register_no(register_no: str) -> Optional[dict[str, Any]]:
    rows = db.table("students").select("*").eq("register_no", register_no).execute().data
    return rows[0] if rows else None


def get_student_by_fingerprint(template_id: str) -> Optional[dict[str, Any]]:
    rows = db.table("students").select("*").eq("fingerprint_id", template_id).execute().data
    return rows[0] if rows else None


def add_student(register_no: str, name: str, sclass: str, department: str,
                email: str = "", phone: str = "", batch: str = "") -> dict[str, Any]:
    if get_student_by_register_no(register_no):
        raise StudentError(f"Register number {register_no} already exists")
    resp = db.table("students").insert({
        "register_no": register_no,
        "name": name,
        "class": sclass,
        "department": department,
        "email": email or None,
        "phone": phone or None,
        "batch": batch or None,
        "fingerprint_id": None,
    }).execute()
    return resp.data[0]


def update_student(student_id: str, **fields: Any) -> dict[str, Any]:
    fields.pop("id", None)
    if not fields:
        raise StudentError("No fields to update")
    resp = db.table("students").update(fields).eq("id", student_id).execute()
    if not resp.data:
        raise StudentError(f"Student {student_id} not found")
    return resp.data[0]


def delete_student(student_id: str) -> None:
    db.table("students").delete().eq("id", student_id).execute()


def set_fingerprint(student_id: str, template_id: str) -> dict[str, Any]:
    """Bind a scanner template id. Raises if bound to another student."""
    other = get_student_by_fingerprint(template_id)
    if other and other["id"] != student_id:
        raise StudentError(
            f"Fingerprint already registered to {other['name']} ({other['register_no']})"
        )
    return update_student(student_id, fingerprint_id=template_id)


def subjects() -> list[dict[str, Any]]:
    return db.table("subjects").select("*").order("code").execute().data


def add_subject(code: str, name: str) -> dict[str, Any]:
    resp = db.table("subjects").insert({"code": code, "name": name}).execute()
    return resp.data[0]
