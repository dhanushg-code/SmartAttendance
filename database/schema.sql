-- SmartAttend schema (spec sections 16-24)
-- Run in Supabase Dashboard → SQL Editor.
-- UUIDs are used for primary keys; Supabase auth admins are optional (auth schema) —
-- a simple admins table is included for local app-level login.

create extension if not exists "pgcrypto";

-- 17. Students ---------------------------------------------------------------
create table if not exists students (
    id             uuid primary key default gen_random_uuid(),
    register_no    text not null unique,
    name           text not null,
    class          text not null,
    department     text not null,
    email          text,
    phone          text,
    fingerprint_id text unique,
    created_at     timestamptz not null default now()
);

-- 18. Subjects ----------------------------------------------------------------
create table if not exists subjects (
    id          uuid primary key default gen_random_uuid(),
    code        text not null unique,
    name        text not null,
    created_at  timestamptz not null default now()
);

-- 18. Attendance (regular classroom) -------------------------------------------
create table if not exists attendance (
    id          uuid primary key default gen_random_uuid(),
    student_id  uuid not null references students(id) on delete cascade,
    subject_id  uuid not null references subjects(id) on delete restrict,
    date        date not null,
    entry_time  time not null,
    status      text not null default 'Present' check (status in ('Present', 'Absent', 'Late')),
    created_at  timestamptz not null default now(),
    -- 8. Duplicate prevention: one record per student/subject/day
    unique (student_id, subject_id, date)
);

-- 19. Exams --------------------------------------------------------------------
create table if not exists exams (
    id          uuid primary key default gen_random_uuid(),
    exam_name   text not null,
    subject     text not null,
    exam_date   date not null,
    start_time  time not null,
    end_time    time not null,
    created_at  timestamptz not null default now()
);

-- 20. Exam students (eligibility) ------------------------------------------------
create table if not exists exam_students (
    id          uuid primary key default gen_random_uuid(),
    exam_id     uuid not null references exams(id) on delete cascade,
    student_id  uuid not null references students(id) on delete cascade,
    eligible    boolean not null default true,
    unique (exam_id, student_id)
);

-- 21. Halls -----------------------------------------------------------------------
create table if not exists halls (
    id           uuid primary key default gen_random_uuid(),
    hall_name    text not null unique,
    room_number  text,
    capacity     integer not null default 0,
    created_at   timestamptz not null default now()
);

-- 22. Seats -----------------------------------------------------------------------
create table if not exists seats (
    id           uuid primary key default gen_random_uuid(),
    hall_id      uuid not null references halls(id) on delete cascade,
    seat_number  text not null,
    status       text not null default 'AVAILABLE'
                 check (status in ('AVAILABLE', 'ALLOCATED', 'PRESENT', 'ABSENT')),
    unique (hall_id, seat_number)
);

-- 23. Seat allocations --------------------------------------------------------------
create table if not exists seat_allocations (
    id           uuid primary key default gen_random_uuid(),
    exam_id      uuid not null references exams(id) on delete cascade,
    student_id   uuid not null references students(id) on delete cascade,
    hall_id      uuid not null references halls(id) on delete cascade,
    seat_id      uuid not null references seats(id) on delete cascade,
    allocated_at timestamptz not null default now(),
    unique (exam_id, student_id),
    unique (exam_id, seat_id)   -- 14. one student per seat per exam
);

-- 24. Exam attendance -----------------------------------------------------------------
create table if not exists exam_attendance (
    id                uuid primary key default gen_random_uuid(),
    exam_id           uuid not null references exams(id) on delete cascade,
    student_id        uuid not null references students(id) on delete cascade,
    hall_id           uuid not null references halls(id) on delete cascade,
    seat_id           uuid not null references seats(id) on delete cascade,
    verification_time timestamptz not null default now(),
    status            text not null default 'Present' check (status in ('Present', 'Absent')),
    unique (exam_id, student_id)  -- duplicate exam verification prevention
);

-- Admins (app-level login; see also spec section 28 for RLS guidance) -------------------
create table if not exists admins (
    id            uuid primary key default gen_random_uuid(),
    username      text not null unique,
    password_hash text not null,
    created_at    timestamptz not null default now()
);

-- Helpful indexes ------------------------------------------------------------------------
create index if not exists idx_attendance_date on attendance(date);
create index if not exists idx_attendance_student on attendance(student_id);
create index if not exists idx_exam_attendance_exam on exam_attendance(exam_id);
create index if not exists idx_seats_hall on seats(hall_id);
create index if not exists idx_alloc_exam on seat_allocations(exam_id);

-- Seed default admin (username: admin, password: admin123 — change after first login)
insert into admins (username, password_hash)
values ('admin', crypt('admin123', gen_salt('bf')))
on conflict (username) do nothing;
