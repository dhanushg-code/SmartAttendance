"""Main application window with modern left sidebar navigation and executive layout."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from fingerprint.scanner import ScannerService
from timetable.alerts import (
    CompositeNotifier,
    DesktopNotifier,
    EmailNotifier,
    check_upcoming_periods,
)
from ui.attendance import AttendanceWidget
from ui.common import StatusPill
from ui.dashboard import DashboardWidget
from ui.exams import ExamScanWidget, ExamsWidget
from ui.staff import StaffWidget
from ui.students import StudentsWidget
from ui.timetable import TimetableWidget


class MainWindow(QMainWindow):
    def __init__(self, admin: dict) -> None:
        super().__init__()
        self.admin = admin
        self.scanner_service = ScannerService()
        self.setWindowTitle(f"SmartAttend — Campus Biometric Management Console")
        self.resize(1200, 780)
        self.setMinimumSize(1020, 640)

        # Central container
        central = QWidget()
        self.setCentralWidget(central)
        main_hlay = QHBoxLayout(central)
        main_hlay.setContentsMargins(0, 0, 0, 0)
        main_hlay.setSpacing(0)

        # -------------------------------------------------------------
        # 1. Left Sidebar Navigation
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("appSidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(
            """
            QFrame#appSidebar {
                background-color: #0D1527;
                border-right: 1px solid #1B253B;
            }
            """
        )
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(16, 20, 16, 20)
        side_lay.setSpacing(12)

        # Brand header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_icon = QLabel()
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(38, 38)

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "grt_logo.png"
        if not logo_path.exists():
            logo_path = Path(__file__).resolve().parent.parent / "assets" / "grt_logo.jpg"

        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                brand_icon.setPixmap(
                    pix.scaled(
                        38,
                        38,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                brand_icon.setStyleSheet("background: transparent;")
                self.setWindowIcon(QIcon(str(logo_path)))
        else:
            brand_icon.setText("🏛️")
            brand_icon.setStyleSheet(
                """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E2C4F, stop:1 #141E33);
                border: 1px solid #6366F1;
                border-radius: 10px;
                font-size: 18px;
                """
            )
        brand_row.addWidget(brand_icon)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(0)
        b_title = QLabel("SmartAttend")
        b_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.3px;")
        b_sub = QLabel("BIOMETRIC v2.4")
        b_sub.setStyleSheet("font-size: 9px; font-weight: 700; color: #6366F1; letter-spacing: 1px;")
        brand_text_box.addWidget(b_title)
        brand_text_box.addWidget(b_sub)
        brand_row.addLayout(brand_text_box)
        side_lay.addLayout(brand_row)

        # System Status Pill
        mode_pill = StatusPill(
            "⚡ DEMO MODE" if self._demo() else "🟢 LIVE SUPABASE",
            "warning" if self._demo() else "success",
            self,
        )
        mode_pill.setFixedHeight(24)
        side_lay.addWidget(mode_pill)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1B253B; margin-top: 4px; margin-bottom: 4px;")
        side_lay.addWidget(sep)

        # Section Label
        nav_label = QLabel("NAVIGATION")
        nav_label.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #475569; letter-spacing: 1px; padding-left: 4px;"
        )
        side_lay.addWidget(nav_label)

        # Nav Buttons List
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("📊  Dashboard", 0),
            ("🎓  Students", 1),
            ("👥  Staff", 2),
            ("🗓️  Timetable", 3),
            ("📋  Attendance", 4),
            ("📝  Exams", 5),
            ("🛡️  Exam Kiosk", 6),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=index: self._set_active_view(idx))
            side_lay.addWidget(btn)
            self.nav_buttons.append(btn)

        side_lay.addStretch(1)

        # Administrator Profile Box at bottom of sidebar
        user_card = QFrame()
        user_card.setObjectName("userCard")
        user_card.setStyleSheet(
            """
            QFrame#userCard {
                background-color: #141E33;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 4px;
            }
            """
        )
        u_lay = QHBoxLayout(user_card)
        u_lay.setContentsMargins(10, 10, 10, 10)
        u_lay.setSpacing(10)

        avatar = QLabel(self.admin.get("username", "AD")[:2].upper())
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(32, 32)
        avatar.setStyleSheet(
            """
            background-color: #4F46E5;
            color: #FFFFFF;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 800;
            """
        )
        u_lay.addWidget(avatar)

        u_info = QVBoxLayout()
        u_info.setSpacing(1)
        u_name = QLabel(self.admin.get("username", "Admin").title())
        u_name.setStyleSheet("font-size: 12px; font-weight: 700; color: #F8FAFC;")
        u_role = QLabel("Administrator")
        u_role.setStyleSheet("font-size: 10px; color: #64748B;")
        u_info.addWidget(u_name)
        u_info.addWidget(u_role)
        u_lay.addLayout(u_info, 1)

        side_lay.addWidget(user_card)

        main_hlay.addWidget(sidebar)

        # -------------------------------------------------------------
        # 2. Main Content Area (Header + Stacked Pages)
        # -------------------------------------------------------------
        content_container = QWidget()
        content_lay = QVBoxLayout(content_container)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet(
            """
            QFrame#topBar {
                background-color: #0B101D;
                border-bottom: 1px solid #1B253B;
            }
            """
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 0, 24, 0)

        self.screen_title = QLabel("Dashboard")
        self.screen_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #F8FAFC;")
        tb_lay.addWidget(self.screen_title)

        tb_lay.addStretch(1)

        # Live Clock & Date Badge
        self.clock_badge = QLabel("")
        self.clock_badge.setStyleSheet(
            """
            background-color: #141E33;
            color: #94A3B8;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            """
        )
        tb_lay.addWidget(self.clock_badge)
        self._update_clock()

        # Timer for live clock
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        # Quick refresh button
        quick_refresh = QPushButton("🔄 Refresh View")
        quick_refresh.setStyleSheet(
            """
            QPushButton {
                background-color: #141E33;
                border: 1px solid #22314E;
                color: #CBD5E1;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E2C4F;
                color: #FFFFFF;
                border-color: #6366F1;
            }
            """
        )
        quick_refresh.clicked.connect(self._refresh_current_view)
        tb_lay.addWidget(quick_refresh)

        content_lay.addWidget(top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.dashboard_tab = DashboardWidget()
        self.students_tab = StudentsWidget(scanner_service=self.scanner_service)
        self.staff_tab = StaffWidget()
        self.timetable_tab = TimetableWidget()
        self.attendance_tab = AttendanceWidget(scanner_service=self.scanner_service)
        self.exams_tab = ExamsWidget(scanner_service=self.scanner_service)
        self.exam_scan_tab = ExamScanWidget(scanner_service=self.scanner_service)

        self.stack.addWidget(self.dashboard_tab)      # 0
        self.stack.addWidget(self.students_tab)       # 1
        self.stack.addWidget(self.staff_tab)          # 2
        self.stack.addWidget(self.timetable_tab)      # 3
        self.stack.addWidget(self.attendance_tab)     # 4
        self.stack.addWidget(self.exams_tab)          # 5
        self.stack.addWidget(self.exam_scan_tab)      # 6

        content_lay.addWidget(self.stack, 1)
        main_hlay.addWidget(content_container, 1)

        # -------------------------------------------------------------
        # 3. Status Bar
        # -------------------------------------------------------------
        status = QStatusBar()
        scanner_type = type(self.scanner_service.scanner).__name__
        mode_text = "DEMO SIMULATOR (In-Memory Mock DB)" if self._demo() else "LIVE DATABASE (Connected)"
        status.addWidget(QLabel(f"  ● Scanner Hardware: {scanner_type}    |    ● Environment: {mode_text}"))
        self.setStatusBar(status)

        # -------------------------------------------------------------
        # 4. Desktop Tray Icon & Timetable Period Alerts (every 60s)
        # -------------------------------------------------------------
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        self.tray_icon.show()

        self.desktop_notifier = DesktopNotifier(tray_icon=self.tray_icon)
        self.email_notifier = EmailNotifier()
        self.composite_notifier = CompositeNotifier([self.desktop_notifier, self.email_notifier])

        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self._check_timetable_alerts)
        self.alert_timer.start(60000)  # Check every 60 seconds
        QTimer.singleShot(2000, self._check_timetable_alerts)

        # Set initial active view
        self._set_active_view(0)

    @staticmethod
    def _demo() -> bool:
        from config import settings

        return settings.DEMO_MODE

    def _update_clock(self) -> None:
        now = datetime.now().strftime("%a, %b %d • %I:%M:%S %p")
        self.clock_badge.setText(f"🕒  {now}")

    def _set_active_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        titles = [
            "Dashboard / System Overview",
            "Students / Enrollment & Directory",
            "Staff / Faculty Directory & Contact Endpoints",
            "Timetable / Weekly Academic Schedule Matrix",
            "Attendance / Live Classroom Biometric Scanner",
            "Exams / Scheduling & Seat Allocations",
            "Exam Kiosk / Live Biometric Hall Gate Terminal",
        ]
        if 0 <= index < len(titles):
            self.screen_title.setText(titles[index])

        # Update button styling
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setChecked(True)
                btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #1E2C4F;
                        color: #FFFFFF;
                        border: none;
                        border-left: 3px solid #6366F1;
                        border-radius: 8px;
                        padding: 10px 14px;
                        text-align: left;
                        font-size: 13px;
                        font-weight: 700;
                    }
                    """
                )
            else:
                btn.setChecked(False)
                btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent;
                        color: #94A3B8;
                        border: none;
                        border-radius: 8px;
                        padding: 10px 14px;
                        text-align: left;
                        font-size: 13px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #141E33;
                        color: #F8FAFC;
                    }
                    """
                )

        self._on_tab_changed(index)

    def _refresh_current_view(self) -> None:
        idx = self.stack.currentIndex()
        self._on_tab_changed(idx)

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self.dashboard_tab.refresh()
        elif index == 1:
            self.students_tab.refresh()
        elif index == 2:
            self.staff_tab.refresh()
        elif index == 3:
            self.timetable_tab.refresh()
        elif index == 4:
            self.attendance_tab.refresh()
        elif index == 5:
            self.exams_tab.refresh()

    def _check_timetable_alerts(self) -> None:
        try:
            check_upcoming_periods(notifiers=self.composite_notifier)
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self.scanner_service.close()
        super().closeEvent(event)
