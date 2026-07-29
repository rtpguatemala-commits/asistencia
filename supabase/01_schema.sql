-- =====================================================================
-- Rescue de Planet de Guatemala — Control de Asistencia
-- 01_schema.sql  ·  Tablas base
-- Ejecutar en: Supabase → SQL Editor → New query → pegar → Run
-- =====================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- Configuración global (fila única)
-- ---------------------------------------------------------------------
create table if not exists public.settings (
    id                      int primary key default 1,
    org_name                text            not null default 'Rescue de Planet de Guatemala',
    building_lat            numeric(10, 7)  not null default 14.6062430,
    building_lng            numeric(10, 7)  not null default -90.4668340,
    building_radius_m       int             not null default 50,
    max_gps_accuracy_m      int             not null default 120,
    default_grace_minutes   int             not null default 15,
    auto_close_enabled      boolean         not null default true,
    timezone                text            not null default 'America/Guatemala',
    updated_at              timestamptz     not null default now(),
    constraint settings_singleton check (id = 1)
);

insert into public.settings (id) values (1) on conflict (id) do nothing;

comment on table public.settings is 'Parámetros globales del sistema. Solo existe la fila id = 1.';
comment on column public.settings.max_gps_accuracy_m is
    'Si el navegador reporta una precisión peor que este valor, se rechaza la marca en modo edificio.';

-- ---------------------------------------------------------------------
-- Empleados (perfil ligado a auth.users)
-- ---------------------------------------------------------------------
create table if not exists public.employees (
    id                      uuid primary key references auth.users (id) on delete cascade,
    full_name               text            not null,
    email                   text            not null unique,
    role                    text            not null default 'employee'
                                            check (role in ('admin', 'employee')),
    position                text,
    birth_date              date,
    phone                   text,
    shift_start             time            not null,
    shift_end               time            not null,
    work_days               smallint[]      not null default '{1,2,3,4,5}',
    lunch_threshold_hours   numeric(4, 2)   not null default 6.00,
    lunch_deduction_minutes int             not null default 60,
    grace_minutes           int             not null default 15,
    is_active               boolean         not null default true,
    created_at              timestamptz     not null default now(),
    updated_at              timestamptz     not null default now()
);

comment on column public.employees.work_days is
    'Días laborales en formato ISO: 1 = lunes ... 7 = domingo.';
comment on column public.employees.lunch_threshold_hours is
    'Solo se descuenta el almuerzo si la jornada bruta supera estas horas.';

create index if not exists employees_role_idx   on public.employees (role);
create index if not exists employees_active_idx on public.employees (is_active);

-- ---------------------------------------------------------------------
-- Asistencia: un registro por empleado por día
-- ---------------------------------------------------------------------
create table if not exists public.attendance (
    id                      uuid primary key default gen_random_uuid(),
    employee_id             uuid            not null references public.employees (id) on delete cascade,
    work_date               date            not null,

    clock_in_at             timestamptz,
    clock_out_at            timestamptz,

    clock_in_mode           text check (clock_in_mode  in ('building', 'other')),
    clock_out_mode          text check (clock_out_mode in ('building', 'other')),

    clock_in_lat            numeric(10, 7),
    clock_in_lng            numeric(10, 7),
    clock_in_accuracy_m     numeric(8, 2),
    clock_in_distance_m     numeric(10, 2),

    clock_out_lat           numeric(10, 7),
    clock_out_lng           numeric(10, 7),
    clock_out_accuracy_m    numeric(8, 2),
    clock_out_distance_m    numeric(10, 2),

    clock_in_reason         text,
    clock_out_reason        text,

    auto_closed             boolean         not null default false,
    needs_review            boolean         not null default false,

    gross_minutes           int,
    lunch_minutes           int,
    net_minutes             int,
    late_minutes            int             not null default 0,
    early_leave_minutes     int             not null default 0,
    overtime_minutes        int             not null default 0,
    status                  text            not null default 'open',

    note                    text,
    edited_by               uuid references public.employees (id) on delete set null,
    edited_at               timestamptz,
    created_at              timestamptz     not null default now(),

    constraint attendance_unique_day unique (employee_id, work_date)
);

comment on column public.attendance.status is
    'on_time | late | early_leave | late_and_early | open | absent';

create index if not exists attendance_date_idx     on public.attendance (work_date desc);
create index if not exists attendance_employee_idx on public.attendance (employee_id, work_date desc);
create index if not exists attendance_review_idx   on public.attendance (needs_review) where needs_review;

-- ---------------------------------------------------------------------
-- Excepciones registradas por la gerencia
-- ---------------------------------------------------------------------
create table if not exists public.exceptions (
    id              uuid primary key default gen_random_uuid(),
    employee_id     uuid        not null references public.employees (id) on delete cascade,
    date_from       date        not null,
    date_to         date        not null,
    type            text        not null check (type in (
                        'vacation',        -- vacaciones
                        'day_off',         -- día libre / compensatorio
                        'sick_leave',      -- incapacidad o permiso médico
                        'personal_leave',  -- permiso personal
                        'justified_late'   -- tardanza o salida temprana justificada
                    )),
    note            text,
    attachment_url  text,
    counts_as_paid  boolean     not null default true,
    created_by      uuid references public.employees (id) on delete set null,
    created_at      timestamptz not null default now(),
    constraint exceptions_range_ok check (date_to >= date_from)
);

create index if not exists exceptions_employee_idx on public.exceptions (employee_id, date_from, date_to);

-- ---------------------------------------------------------------------
-- Asuetos oficiales
-- ---------------------------------------------------------------------
create table if not exists public.holidays (
    id          uuid primary key default gen_random_uuid(),
    date        date        not null unique,
    name        text        not null,
    is_half_day boolean     not null default false,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Solicitudes de corrección
-- ---------------------------------------------------------------------
create table if not exists public.correction_requests (
    id                  uuid primary key default gen_random_uuid(),
    attendance_id       uuid references public.attendance (id) on delete cascade,
    employee_id         uuid        not null references public.employees (id) on delete cascade,
    work_date           date        not null,
    requested_clock_in  timestamptz,
    requested_clock_out timestamptz,
    reason              text        not null,
    status              text        not null default 'pending'
                                    check (status in ('pending', 'approved', 'rejected')),
    reviewed_by         uuid references public.employees (id) on delete set null,
    reviewed_at         timestamptz,
    review_note         text,
    created_at          timestamptz not null default now()
);

create index if not exists correction_status_idx on public.correction_requests (status, created_at desc);

-- ---------------------------------------------------------------------
-- Bitácora de auditoría
-- ---------------------------------------------------------------------
create table if not exists public.audit_log (
    id          bigserial primary key,
    actor_id    uuid references public.employees (id) on delete set null,
    actor_name  text,
    action      text        not null,
    entity      text        not null,
    entity_id   text,
    details     jsonb,
    created_at  timestamptz not null default now()
);

create index if not exists audit_created_idx on public.audit_log (created_at desc);
