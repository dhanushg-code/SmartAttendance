"""Timetable management UI: weekly scheduling grid per class."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from database import staff as staff_service
from database import students as student_service
from database import timetable as timetable_service
from ui.common import StatusPill, set_pill

PERIODS_FILE = Path(__file__).resolve().parent.parent / "config" / "periods.json"

DEFAULT_PERIODS = {
    1: ("09:00", "10:00"),
    2: ("10:00", "11:00"),
    3: ("11:15", "12:15"),
    4: ("12:15", "13:15"),
    5: ("14:00", "15:00"),
    6: ("15:00", "16:00"),
    7: ("16:00", "17:00"),
}

def load_periods() -> dict[int, tuple[str, str]]:
    periods = DEFAULT_PERIODS.copy()
    if PERIODS_FILE.exists():
        try:
            with open(PERIODS_FILE, "r") as f:
                data = json.load(f)
                for k, v in data.items():
                    periods[int(k)] = tuple(v)
        except Exception:
            pass
    return periods

def save_periods(periods: dict[int, tuple[str, str]]) -> None:
    try:
        PERIODS_FILE.parent.mkdir(exist_ok=True, parents=True)
        with open(PERIODS_FILE, "w") as f:
            json.dump(periods, f, indent=4)
    except Exception as e:
        print(f"Error saving periods: {e}")

PERIOD_DEFAULT_TIMES = load_periods()


class ConfigurePeriodsDialog(QDialog):
    """Dialog to configure the default start and end times for all periods."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Period Timings")
        self.setFixedWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        head_title = QLabel("Period Timings")
        head_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        root.addWidget(head_title)

        card = QFrame()
        card.setObjectName("formCard")
        card.setStyleSheet(
            """
            QFrame#formCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            """
        )
        form = QVBoxLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        self.time_edits = {}
        for p in range(1, 8):
            row = QHBoxLayout()
            lbl = QLabel(f"Period {p}")
            lbl.setFixedWidth(60)
            lbl.setStyleSheet("font-weight: 700; color: #94A3B8;")
            
            def_start, def_end = PERIOD_DEFAULT_TIMES.get(p, ("00:00", "00:00"))
            
            t_start = QTimeEdit()
            t_start.setDisplayFormat("hh:mm AP")
            sh, sm = map(int, def_start.split(":"))
            t_start.setTime(QTime(sh, sm))
            
            t_end = QTimeEdit()
            t_end.setDisplayFormat("hh:mm AP")
            eh, em = map(int, def_end.split(":"))
            t_end.setTime(QTime(eh, em))
            
            row.addWidget(lbl)
            row.addWidget(t_start)
            row.addWidget(QLabel("to"))
            row.addWidget(t_end)
            form.addLayout(row)
            
            self.time_edits[p] = (t_start, t_end)

        root.addWidget(card)

        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Timings")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(save_btn)

        root.addLayout(btn_box)

    def _save(self) -> None:
        for p, (ts, te) in self.time_edits.items():
            if ts.time() >= te.time():
                QMessageBox.warning(self, "Invalid Timings", f"Period {p} end time must be after start time.")
                return
            
            start_str = ts.time().toString("HH:mm")
            end_str = te.time().toString("HH:mm")
            PERIOD_DEFAULT_TIMES[p] = (start_str, end_str)
            
        save_periods(PERIOD_DEFAULT_TIMES)
        self.accept()


class TimetableSlotDialog(QDialog):
    """Dialog to configure or clear an individual timetable slot."""

    def __init__(
        self,
        parent=None,
        class_name: str = "CSE-A",
        day_of_week: str = "Monday",
        period_no: int = 1,
        slot_data: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.class_name = class_name
        self.day_of_week = day_of_week
        self.period_no = period_no
        self.slot_data = slot_data
        self.cleared = False

        self.setWindowTitle(f"Configure Schedule Slot — {day_of_week} (Period {period_no})")
        self.setFixedWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        head_title = QLabel(f"Slot Editor: {class_name} • {day_of_week}")
        head_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        head_sub = QLabel(f"Assign academic subject, faculty instructor, room, and timings for Period #{period_no}.")
        head_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        head_box.addWidget(head_title)
        head_box.addWidget(head_sub)
        root.addLayout(head_box)

        # Form Card
        card = QFrame()
        card.setObjectName("formCard")
        card.setStyleSheet(
            """
            QFrame#formCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            """
        )
        form = QVBoxLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        # Subject Selector
        box_sub = QVBoxLayout()
        lbl_sub = QLabel("SUBJECT / COURSE *")
        lbl_sub.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.subject_combo = QComboBox()
        self.subject_combo.addItem("— Select Subject —", None)
        all_subjects = student_service.subjects()
        for s in all_subjects:
            self.subject_combo.addItem(f"{s['code']} — {s['name']}", s["id"])
        box_sub.addWidget(lbl_sub)
        box_sub.addWidget(self.subject_combo)
        form.addLayout(box_sub)

        # Staff Selector
        box_staff = QVBoxLayout()
        lbl_staff = QLabel("FACULTY / INSTRUCTOR")
        lbl_staff.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.staff_combo = QComboBox()
        self.staff_combo.addItem("— Select Faculty Member —", None)
        all_staff = staff_service.list_staff()
        for st in all_staff:
            email_info = f" ({st['email']})" if st.get("email") else ""
            self.staff_combo.addItem(f"{st['name']}{email_info}", st["id"])
        box_staff.addWidget(lbl_staff)
        box_staff.addWidget(self.staff_combo)
        form.addLayout(box_staff)

        # Time Pickers Row
        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        def_start, def_end = PERIOD_DEFAULT_TIMES.get(period_no, ("09:00", "10:00"))

        box_start = QVBoxLayout()
        lbl_start = QLabel("START TIME *")
        lbl_start.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("hh:mm AP")
        sh, sm = map(int, def_start.split(":"))
        self.start_time.setTime(QTime(sh, sm))
        box_start.addWidget(lbl_start)
        box_start.addWidget(self.start_time)
        time_row.addLayout(box_start, 1)

        box_end = QVBoxLayout()
        lbl_end = QLabel("END TIME *")
        lbl_end.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("hh:mm AP")
        eh, em = map(int, def_end.split(":"))
        self.end_time.setTime(QTime(eh, em))
        box_end.addWidget(lbl_end)
        box_end.addWidget(self.end_time)
        time_row.addLayout(box_end, 1)

        form.addLayout(time_row)

        # Classroom / Room
        box_room = QVBoxLayout()
        lbl_room = QLabel("CLASSROOM / LAB / ROOM")
        lbl_room.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.room = QLineEdit()
        self.room.setPlaceholderText("e.g. Room B-101 or Lab 2")
        box_room.addWidget(lbl_room)
        box_room.addWidget(self.room)
        form.addLayout(box_room)

        root.addWidget(card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        if slot_data:
            clear_btn = QPushButton("Clear Slot")
            clear_btn.setObjectName("dangerBtn")
            clear_btn.setFixedHeight(38)
            clear_btn.clicked.connect(self._clear_slot)
            btn_box.addWidget(clear_btn)

        btn_box.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Slot")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(save_btn)

        root.addLayout(btn_box)

        # Prepopulate if editing existing slot
        if slot_data:
            sid = slot_data.get("subject_id")
            if sid:
                idx = self.subject_combo.findData(sid)
                if idx >= 0:
                    self.subject_combo.setCurrentIndex(idx)

            st_id = slot_data.get("staff_id")
            if st_id:
                idx = self.staff_combo.findData(st_id)
                if idx >= 0:
                    self.staff_combo.setCurrentIndex(idx)

            st_time = slot_data.get("start_time")
            if st_time:
                parts = str(st_time).split(":")
                self.start_time.setTime(QTime(int(parts[0]), int(parts[1])))

            ed_time = slot_data.get("end_time")
            if ed_time:
                parts = str(ed_time).split(":")
                self.end_time.setTime(QTime(int(parts[0]), int(parts[1])))

            self.room.setText(slot_data.get("room") or "")

    def _clear_slot(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Clear Slot",
            f"Are you sure you want to remove the schedule for {self.day_of_week} Period {self.period_no}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            timetable_service.delete_slot(self.class_name, self.day_of_week, self.period_no)
            self.cleared = True
            self.accept()

    def _save(self) -> None:
        subject_id = self.subject_combo.currentData()
        staff_id = self.staff_combo.currentData()
        start_str = self.start_time.time().toString("HH:mm")
        end_str = self.end_time.time().toString("HH:mm")
        room_str = self.room.text().strip()

        if self.start_time.time() >= self.end_time.time():
            QMessageBox.warning(self, "Invalid Timings", "End time must be after start time.")
            return

        try:
            timetable_service.save_slot(
                class_name=self.class_name,
                day_of_week=self.day_of_week,
                period_no=self.period_no,
                start_time=start_str,
                end_time=end_str,
                subject_id=subject_id,
                staff_id=staff_id,
                room=room_str,
            )
        except timetable_service.TimetableError as exc:
            QMessageBox.warning(self, "Schedule Error", str(exc))
            return

        self.accept()


class TimetableWidget(QWidget):
    """Weekly academic schedule matrix grid per class."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.days = timetable_service.DAYS_OF_WEEK
        self.period_count = 7
        self._grid_cache: dict[str, dict[int, dict]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Filter & Action Bar
        # -------------------------------------------------------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)

        lbl_year = QLabel("YEAR:")
        lbl_year.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        action_bar.addWidget(lbl_year)

        self.year_selector = QComboBox()
        self.year_selector.setFixedHeight(38)
        self.year_selector.setMinimumWidth(120)
        self.year_selector.addItems(["1st Year", "2nd Year", "3rd Year", "4th Year"])
        self.year_selector.currentTextChanged.connect(self.refresh)
        action_bar.addWidget(self.year_selector)

        lbl_class = QLabel("CLASS / SECTION:")
        lbl_class.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        action_bar.addWidget(lbl_class)

        self.class_selector = QComboBox()
        self.class_selector.setFixedHeight(38)
        self.class_selector.setMinimumWidth(180)
        self.class_selector.currentTextChanged.connect(self.refresh)
        action_bar.addWidget(self.class_selector)

        action_bar.addStretch(1)

        edit_btn = QPushButton("➕ Configure Slot")
        edit_btn.setObjectName("primaryBtn")
        edit_btn.setFixedHeight(38)
        edit_btn.clicked.connect(self._edit_selected_slot)
        action_bar.addWidget(edit_btn)

        timings_btn = QPushButton("⚙️ Set Timings")
        timings_btn.setFixedHeight(38)
        timings_btn.clicked.connect(self._configure_periods)
        action_bar.addWidget(timings_btn)

        clear_btn = QPushButton("🗑️ Clear Slot")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.setFixedHeight(38)
        clear_btn.clicked.connect(self._clear_selected_slot)
        action_bar.addWidget(clear_btn)

        refresh_btn = QPushButton("🔄 Refresh Grid")
        refresh_btn.setFixedHeight(38)
        refresh_btn.clicked.connect(self.refresh)
        action_bar.addWidget(refresh_btn)

        root.addLayout(action_bar)

        # -------------------------------------------------------------
        # 2. Header Strip
        # -------------------------------------------------------------
        summary_strip = QHBoxLayout()
        summary_title = QLabel("WEEKLY ACADEMIC SCHEDULE MATRIX")
        summary_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        summary_strip.addWidget(summary_title)
        summary_strip.addStretch(1)

        self.status_pill = StatusPill("0 Scheduled Periods", "neutral")
        summary_strip.addWidget(self.status_pill)
        root.addLayout(summary_strip)

        # -------------------------------------------------------------
        # 3. Weekly Grid Table
        # -------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.days))
        self.table.setHorizontalHeaderLabels([f"📅  {d}" for d in self.days])
        self.table.setRowCount(self.period_count)

        self.update_headers()

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda r, c: self._open_slot_dialog(r, c))

        # First corner box header text: Period / Day
        corner_btn = self.table.findChild(QAbstractButton)
        if corner_btn:
            corner_lay = QVBoxLayout(corner_btn)
            corner_lay.setContentsMargins(4, 4, 4, 4)
            lbl_corner = QLabel("Period / Day")
            lbl_corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_corner.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
            corner_lay.addWidget(lbl_corner)

        root.addWidget(self.table, 1)

        # Populate classes and load
        self._populate_classes()

    def _populate_classes(self) -> None:
        self.class_selector.blockSignals(True)
        self.class_selector.clear()
        classes = timetable_service.list_distinct_classes()
        self.class_selector.addItems(classes)
        self.class_selector.blockSignals(False)
        self.refresh()

    def current_class(self) -> str:
        yr = self.year_selector.currentText().strip() or "1st Year"
        cls = self.class_selector.currentText().strip() or "CSE-A"
        return f"{yr} {cls}"

    def refresh(self) -> None:
        cls_name = self.current_class()
        self._grid_cache = timetable_service.get_weekly_grid(cls_name)

        scheduled_count = 0
        for r in range(self.period_count):
            period_no = r + 1
            for c, day in enumerate(self.days):
                slot = self._grid_cache.get(day, {}).get(period_no)
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if slot and (slot.get("subject_name") or slot.get("subject_code")):
                    scheduled_count += 1
                    sub_title = slot.get("subject_code") or slot.get("subject_name")
                    full_name = slot.get("subject_name") or ""
                    staff_name = slot.get("staff_name") or "Staff"
                    room = slot.get("room") or "TBA"
                    st = slot.get('start_time')
                    et = slot.get('end_time')
                    st_fmt = QTime.fromString(st, "HH:mm").toString("hh:mm AP") if st else ""
                    et_fmt = QTime.fromString(et, "HH:mm").toString("hh:mm AP") if et else ""
                    times = f"{st_fmt} - {et_fmt}"

                    cell_text = (
                        f"📘 {sub_title} — {full_name}\n"
                        f"👨‍🏫 {staff_name}\n"
                        f"📍 {room}  •  🕒 {times}"
                    )
                    item.setText(cell_text)
                    item.setToolTip(f"{day} Period {period_no}\n{full_name}\nInstructor: {staff_name}\nRoom: {room}")
                else:
                    item.setText("➕\nEmpty Slot")
                    item.setForeground(Qt.GlobalColor.darkGray)

                self.table.setItem(r, c, item)

        set_pill(
            self.status_pill,
            f"{cls_name} • {scheduled_count} Scheduled Periods",
            "success" if scheduled_count > 0 else "neutral",
        )

    def _get_selected_cell(self) -> tuple[int, int] | None:
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r < 0 or c < 0:
            return None
        return r, c

    def _open_slot_dialog(self, row: int, col: int) -> None:
        period_no = row + 1
        day = self.days[col]
        cls_name = self.current_class()
        slot = self._grid_cache.get(day, {}).get(period_no)

        dlg = TimetableSlotDialog(
            self,
            class_name=cls_name,
            day_of_week=day,
            period_no=period_no,
            slot_data=slot,
        )
        if dlg.exec():
            self.refresh()

    def _edit_selected_slot(self) -> None:
        cell = self._get_selected_cell()
        if not cell:
            QMessageBox.information(self, "Selection Required", "Please click on a slot cell in the weekly grid first.")
            return
        self._open_slot_dialog(*cell)

    def _clear_selected_slot(self) -> None:
        cell = self._get_selected_cell()
        if not cell:
            QMessageBox.information(self, "Selection Required", "Please click on a slot cell in the weekly grid first.")
            return
        r, c = cell
        period_no = r + 1
        day = self.days[c]
        cls_name = self.current_class()

        confirm = QMessageBox.question(
            self,
            "Confirm Clear Slot",
            f"Are you sure you want to clear {day} Period {period_no} for {cls_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            timetable_service.delete_slot(cls_name, day, period_no)
            self.refresh()

    def update_headers(self) -> None:
        period_headers = []
        for p in range(1, self.period_count + 1):
            def_start, def_end = PERIOD_DEFAULT_TIMES.get(p, ("", ""))
            ds_fmt = QTime.fromString(def_start, "HH:mm").toString("hh:mm AP") if def_start else ""
            de_fmt = QTime.fromString(def_end, "HH:mm").toString("hh:mm AP") if def_end else ""
            period_headers.append(f"Period {p}\n({ds_fmt} - {de_fmt})")
        self.table.setVerticalHeaderLabels(period_headers)

    def _configure_periods(self) -> None:
        dlg = ConfigurePeriodsDialog(self)
        if dlg.exec():
            self.update_headers()

