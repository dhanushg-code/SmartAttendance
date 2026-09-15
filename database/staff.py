"""Staff CRUD service mirroring students.py."""
from __future__ import annotations

from typing import Any, Optional

from database.supabase_client import db


class StaffError(Exception):
    pass


def list_staff() -> list[dict[str, Any]]:
    """Return all staff members ordered by name."""
    return db.table("staff").select("*").order("name").execute().data


def get_staff(staff_id: str) -> Optional[dict[str, Any]]:
    """Retrieve a staff member by ID."""
    rows = db.table("staff").select("*").eq("id", staff_id).execute().data
    return rows[0] if rows else None


def get_staff_by_email(email: str) -> Optional[dict[str, Any]]:
    """Retrieve a staff member by email address."""
    if not email:
        return None
    rows = db.table("staff").select("*").eq("email", email.strip()).execute().data
    return rows[0] if rows else None


def get_staff_by_device_token(token: str) -> Optional[dict[str, Any]]:
    """Retrieve a staff member by device token."""
    if not token:
        return None
    rows = db.table("staff").select("*").eq("device_token", token.strip()).execute().data
    return rows[0] if rows else None


def add_staff(name: str, email: str = "", phone: str = "", device_token: str = "") -> dict[str, Any]:
    """Add a new staff member."""
    clean_name = name.strip()
    if not clean_name:
        raise StaffError("Staff name cannot be empty")
    clean_email = email.strip()
    if clean_email:
        existing = get_staff_by_email(clean_email)
        if existing:
            raise StaffError(f"Staff member with email '{clean_email}' already exists")

    resp = db.table("staff").insert({
        "name": clean_name,
        "email": clean_email or None,
        "phone": phone.strip() or None,
        "device_token": device_token.strip() or None,
    }).execute()
    return resp.data[0]


def update_staff(staff_id: str, **fields: Any) -> dict[str, Any]:
    """Update fields for a given staff member."""
    fields.pop("id", None)
    if not fields:
        raise StaffError("No fields to update")
    if "email" in fields and fields["email"]:
        existing = get_staff_by_email(fields["email"])
        if existing and existing["id"] != staff_id:
            raise StaffError(f"Email '{fields['email']}' is already assigned to another staff member")

    resp = db.table("staff").update(fields).eq("id", staff_id).execute()
    if not resp.data:
        raise StaffError(f"Staff member {staff_id} not found")
    return resp.data[0]


def delete_staff(staff_id: str) -> None:
    """Delete a staff member by ID."""
    db.table("staff").delete().eq("id", staff_id).execute()
