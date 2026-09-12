# SmartAttend

Smart college attendance and examination management system:
USB fingerprint scanner → Python (PySide6) → Supabase (PostgreSQL) → Excel reports.

## Modules

1. **Regular classroom attendance** — fingerprint scan → identify → duplicate check → mark present (date + time).
2. **Exam hall attendance** — fingerprint → eligibility check → hall/seat lookup → verified screen; plus hall/seat management with automatic seat allocation.

## Quick start (demo mode — no hardware, no Supabase needed)

```bash
pip install -r requirements.txt
python -m scripts.seed_demo   # sample students, subjects, exam, hall, seats
python main.py
```

- Login: **admin / admin123**
- The simulated scanner asks you to type the fingerprint id (demo students are bound to ids `101`–`120`).
- All data lives in an in-memory database that mirrors the Supabase API.

## Going live

1. **Supabase** — create a project, open SQL Editor, run [`database/schema.sql`](database/schema.sql).
2. **.env** — copy `.env.example` to `.env`:
   ```
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_KEY=your-anon-or-service-key
   DEMO_MODE=false
   ```
3. **Admin** — the schema seeds `admin` / `admin123` (change it; the app hashes with PBKDF2).
4. **Scanner** — install your scanner's driver + SDK, then wire the four marked hooks in
   [`fingerprint/scanner.py`](fingerprint/scanner.py) (`SDKScanner.open/close/capture/identify`).
   No other file changes are needed — the rest of the app only sees the
   `FingerprintScanner` interface.

## Database (Supabase)

Tables: `students`, `subjects`, `attendance`, `exams`, `exam_students`, `halls`,
`seats`, `seat_allocations`, `exam_attendance`, `admins` — see `database/schema.sql`.

Key guarantees built in:

- Duplicate classroom attendance blocked by `UNIQUE(student_id, subject_id, date)`.
- Duplicate exam verification blocked by `UNIQUE(exam_id, student_id)`.
- One student per seat per exam: `UNIQUE(exam_id, seat_id)`.
- Fingerprint ids are unique per student; raw fingerprint images are never stored.
- Admin passwords stored as PBKDF2 hashes. Enable Supabase Row Level Security
  before exposing the project (service key stays server-side).

## Excel reports

Generated into `reports/`:

- `Attendance_<date>.xlsx` — daily classroom report (Date, Time, Register No, Name, Class, Department, Subject, Status)
- `Attendance_<start>_to_<end>.xlsx` — date-range report
- `Exam_<name>.xlsx` — exam report with Hall, Seat No, Status, Verification Time
- `chart_<date>.png` — monthly attendance chart (matplotlib)

## Project layout

```
SmartAttend/
├── main.py                  # entry point (login → main window)
├── config/settings.py       # .env config
├── database/                # supabase client, schema.sql, auth, students
├── fingerprint/             # scanner abstraction (sim + SDK hooks), enrollment, verification
├── attendance/              # attendance service, report aggregations
├── exams/                   # exams, halls, seats, allocation
├── ui/                      # PySide6: login, dashboard, students, attendance, exams
├── excel/                   # pandas + openpyxl report writers
├── scripts/seed_demo.py     # demo seed data
└── reports/                 # generated .xlsx / .png output
```

## Scanner SDK integration notes

Different vendors (Mantra MFS110, SecuGen Hamster Pro, ZKTeco, ...) expose very
different APIs, so the adapter in `fingerprint/scanner.py` isolates them:

| Hook            | Typical SDK call                              |
|-----------------|-----------------------------------------------|
| `open()`        | device init / DLL load / RD service connect   |
| `close()`       | device release                                |
| `capture()`     | capture image → extract template → return id  |
| `identify()`    | 1:N match against enrolled templates          |

Enrollment stores only the scanner's template identifier in
`students.fingerprint_id` — never raw fingerprint images.
