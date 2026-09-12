"""Seat management helpers (thin re-exports from exams.exams)."""
from exams.exams import allocate_seats, create_seats, seats_for_hall

__all__ = ["allocate_seats", "create_seats", "seats_for_hall"]
