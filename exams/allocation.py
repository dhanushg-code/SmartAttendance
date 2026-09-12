"""Seat allocation helpers (thin re-exports from exams.exams)."""
from exams.exams import allocate_seats, allocations_for_exam

__all__ = ["allocate_seats", "allocations_for_exam"]
