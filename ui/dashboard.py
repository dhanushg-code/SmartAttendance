"""Admin dashboard: today's attendance summary + embedded analytics chart."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from attendance.attendance import AttendanceService
from config import settings
from ui.common import StatCardWidget, StatusPill


class DashboardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.attendance = AttendanceService()
        self._chart_path = None

        # Scroll area to handle smaller screens gracefully
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(20)

        # -------------------------------------------------------------
        # 1. Welcome Banner
        # -------------------------------------------------------------
        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner.setStyleSheet(
            """
            QFrame#welcomeBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #162447, stop:1 #121A2F);
                border: 1px solid #22355A;
                border-radius: 14px;
            }
            """
        )
        b_lay = QHBoxLayout(banner)
        b_lay.setContentsMargins(22, 18, 22, 18)

        left_b = QVBoxLayout()
        left_b.setSpacing(4)
        greeting = QLabel("Campus Biometric Operations Dashboard")
        greeting.setStyleSheet("font-size: 20px; font-weight: 800; color: #F8FAFC;")
        sub_greeting = QLabel("Real-time telemetry, daily attendance metrics, and historical verification trends.")
        sub_greeting.setStyleSheet("font-size: 13px; color: #94A3B8;")
        left_b.addWidget(greeting)
        left_b.addWidget(sub_greeting)
        b_lay.addLayout(left_b, 1)

        today_pill = StatusPill(f"📅 {date.today().strftime('%B %d, %Y')}", "primary", self)
        today_pill.setFixedHeight(30)
        b_lay.addWidget(today_pill)

        lay.addWidget(banner)

        # -------------------------------------------------------------
        # 2. 4 Modern KPI Cards
        # -------------------------------------------------------------
        grid = QGridLayout()
        grid.setSpacing(16)

        self.kpi_total = StatCardWidget(
            "Total Students", "0", "Enrolled in active directory", "👥", "#6366F1", self
        )
        self.kpi_present = StatCardWidget(
            "Present Today", "0", "Verified via biometric scan", "✔", "#10B981", self
        )
        self.kpi_absent = StatCardWidget(
            "Absent Today", "0", "Unverified or on leave", "✖", "#EF4444", self
        )
        self.kpi_percent = StatCardWidget(
            "Attendance Rate", "0.0%", "Daily campus percentage", "📊", "#8B5CF6", self
        )

        grid.addWidget(self.kpi_total, 0, 0)
        grid.addWidget(self.kpi_present, 0, 1)
        grid.addWidget(self.kpi_absent, 0, 2)
        grid.addWidget(self.kpi_percent, 0, 3)

        lay.addLayout(grid)

        # Compatibility dictionary
        self.stat_cards = {
            "Total Students": self.kpi_total.value_label,
            "Present": self.kpi_present.value_label,
            "Absent": self.kpi_absent.value_label,
            "Attendance %": self.kpi_percent.value_label,
        }

        # -------------------------------------------------------------
        # 3. Action Toolbar & Summary Strip
        # -------------------------------------------------------------
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(12)

        refresh_btn = QPushButton("🔄 Refresh Stats")
        refresh_btn.setFixedHeight(38)
        refresh_btn.clicked.connect(self.refresh)
        actions_bar.addWidget(refresh_btn)

        chart_btn = QPushButton("📈 Render Monthly Analytics")
        chart_btn.setObjectName("primaryBtn")
        chart_btn.setFixedHeight(38)
        chart_btn.clicked.connect(self.show_chart)
        actions_bar.addWidget(chart_btn)

        export_btn = QPushButton("📑 Export Daily Excel Report")
        export_btn.setObjectName("successBtn")
        export_btn.setFixedHeight(38)
        export_btn.clicked.connect(self.export_daily)
        actions_bar.addWidget(export_btn)

        actions_bar.addStretch(1)

        self.summary = QLabel("")
        self.summary.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        actions_bar.addWidget(self.summary)

        lay.addLayout(actions_bar)

        # -------------------------------------------------------------
        # 4. Embedded Analytics Chart Card
        # -------------------------------------------------------------
        chart_frame = QFrame()
        chart_frame.setObjectName("chartCard")
        chart_frame.setStyleSheet(
            """
            QFrame#chartCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 14px;
            }
            """
        )
        c_lay = QVBoxLayout(chart_frame)
        c_lay.setContentsMargins(20, 20, 20, 20)
        c_lay.setSpacing(12)

        chart_header = QHBoxLayout()
        chart_title = QLabel("ATTENDANCE TREND (THIS MONTH)")
        chart_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        chart_header.addWidget(chart_title)
        chart_header.addStretch(1)

        self.chart_status_badge = StatusPill("HISTORICAL TELEMETRY", "info", self)
        chart_header.addWidget(self.chart_status_badge)
        c_lay.addLayout(chart_header)

        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setMinimumHeight(280)
        self.chart_label.setStyleSheet(
            """
            background-color: #0F172A;
            border: 1px dashed #243452;
            border-radius: 10px;
            color: #64748B;
            font-size: 14px;
            font-weight: 500;
            """
        )
        self.chart_label.setText("Click 'Render Monthly Analytics' to generate high-resolution attendance trends.")
        c_lay.addWidget(self.chart_label, 1)

        lay.addWidget(chart_frame, 1)

        self.refresh()

    def refresh(self) -> None:
        stats = self.attendance.dashboard_stats()
        self.kpi_total.set_value(str(stats["total"]))
        self.kpi_present.set_value(str(stats["present"]))
        self.kpi_absent.set_value(str(stats["absent"]))
        self.kpi_percent.set_value(f"{stats['percent']:.1f}%")

        self.summary.setText(
            f"Active Session Date: {stats['date']}   •   Verified Present: {stats['present']}/{stats['total']}"
        )

    def show_chart(self) -> None:
        import matplotlib
        matplotlib.use("Agg")  # Non-GUI backend for rendering to image
        import matplotlib.pyplot as plt
        from attendance.reports import monthly_summary

        today = date.today()
        summary = monthly_summary(today.year, today.month)
        days = list(summary["per_day"].keys())
        counts = [summary["per_day"][d] for d in days]

        if not days:
            self.chart_label.setText("No attendance records recorded for this month yet.")
            return

        # Modern Dark-theme figure styling
        fig, ax = plt.subplots(figsize=(9, 3.6), dpi=120)
        fig.patch.set_facecolor("#141E33")
        ax.set_facecolor("#0F172A")

        x_labels = [d[8:] for d in days]
        bars = ax.bar(x_labels, counts, color="#6366F1", edgecolor="#818CF8", width=0.55, linewidth=1.2)

        # Highlight highest day
        if counts:
            max_c = max(counts)
            for bar, c in zip(bars, counts):
                if c == max_c and max_c > 0:
                    bar.set_color("#10B981")
                    bar.set_edgecolor("#34D399")

        ax.set_title(
            f"Daily Verified Students ({today.strftime('%B %Y')})",
            color="#F8FAFC",
            fontsize=12,
            fontweight="bold",
            pad=14,
        )
        ax.set_xlabel("Day of Month", color="#94A3B8", fontsize=10, labelpad=8)
        ax.set_ylabel("Students Present", color="#94A3B8", fontsize=10, labelpad=8)

        ax.tick_params(colors="#94A3B8", which="both", labelsize=9)
        ax.grid(axis="y", color="#1E293B", linestyle="--", linewidth=0.8, alpha=0.7)

        for spine in ("top", "right", "left", "bottom"):
            ax.spines[spine].set_color("#22314E")

        fig.tight_layout()

        out = settings.REPORTS_DIR / f"chart_{today.isoformat()}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)

        self._chart_path = str(out)

        # Display directly on label
        pixmap = QPixmap(str(out))
        if not pixmap.isNull():
            self.chart_label.setStyleSheet("background-color: transparent; border: none;")
            self.chart_label.setPixmap(
                pixmap.scaled(
                    self.chart_label.width() if self.chart_label.width() > 100 else 800,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.chart_status_badge.setText(f"UPDATED {today.strftime('%I:%M %p')}")

    def export_daily(self) -> None:
        from excel.excel_export import export_daily

        path = export_daily()
        QMessageBox.information(
            self,
            "Excel Export Successful",
            f"Daily attendance report exported successfully:\n\n{path}",
        )
