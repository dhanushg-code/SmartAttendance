"""Hall management helpers (thin re-exports from exams.exams)."""
from exams.exams import create_hall, create_seats, list_halls, seats_for_hall

__all__ = ["create_hall", "create_seats", "list_halls", "seats_for_hall"]
