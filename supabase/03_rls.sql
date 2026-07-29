-- =====================================================================
-- 03_rls.sql  ·  Seguridad a nivel de fila (Row Level Security)
-- Ejecutar DESPUÉS de 02_functions.sql
--
-- Regla general:
--   · Un empleado solo VE sus propios datos.
--   · Un empleado NUNCA escribe directamente en attendance:
--     todas las marcas pasan por las funciones clock_in / clock_out,
--     que validan la geocerca del lado del servidor. Así nadie puede
--     falsificar coordenadas desde la consola del navegador.
--   · El rol 'admin' (Keren) ve y edita todo.
-- =====================================================================

alter table public.settings            enable row level security;
alter table public.employees           enable row level security;
alter table public.attendance          enable row level security;
alter table public.exceptions          enable row level security;
alter table public.holidays            enable row level security;
alter table public.correction_requests enable row level security;
alter table public.audit_log           enable row level security;

-- ---------------------------------------------------------------------
-- settings
-- ---------------------------------------------------------------------
drop policy if exists settings_read  on public.settings;
drop policy if exists settings_write on public.settings;

create policy settings_read on public.settings
    for select to authenticated using (true);

create policy settings_write on public.settings
    for update to authenticated using (public.is_admin()) with check (public.is_admin());

-- ---------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------
drop policy if exists employees_select        on public.employees;
drop policy if exists employees_admin_insert  on public.employees;
drop policy if exists employees_admin_update  on public.employees;
drop policy if exists employees_admin_delete  on public.employees;

-- Todos los autenticados pueden ver el directorio (nombre, cargo, cumpleaños).
-- Los datos sensibles de asistencia siguen protegidos en su propia tabla.
create policy employees_select on public.employees
    for select to authenticated using (true);

create policy employees_admin_insert on public.employees
    for insert to authenticated with check (public.is_admin());

create policy employees_admin_update on public.employees
    for update to authenticated using (public.is_admin()) with check (public.is_admin());

create policy employees_admin_delete on public.employees
    for delete to authenticated using (public.is_admin());

-- ---------------------------------------------------------------------
-- attendance
-- ---------------------------------------------------------------------
drop policy if exists attendance_select       on public.attendance;
drop policy if exists attendance_admin_insert on public.attendance;
drop policy if exists attendance_admin_update on public.attendance;
drop policy if exists attendance_admin_delete on public.attendance;

create policy attendance_select on public.attendance
    for select to authenticated
    using (employee_id = auth.uid() or public.is_admin());

create policy attendance_admin_insert on public.attendance
    for insert to authenticated with check (public.is_admin());

create policy attendance_admin_update on public.attendance
    for update to authenticated using (public.is_admin()) with check (public.is_admin());

create policy attendance_admin_delete on public.attendance
    for delete to authenticated using (public.is_admin());

-- ---------------------------------------------------------------------
-- exceptions
-- ---------------------------------------------------------------------
drop policy if exists exceptions_select on public.exceptions;
drop policy if exists exceptions_write  on public.exceptions;

create policy exceptions_select on public.exceptions
    for select to authenticated
    using (employee_id = auth.uid() or public.is_admin());

create policy exceptions_write on public.exceptions
    for all to authenticated
    using (public.is_admin()) with check (public.is_admin());

-- ---------------------------------------------------------------------
-- holidays
-- ---------------------------------------------------------------------
drop policy if exists holidays_select on public.holidays;
drop policy if exists holidays_write  on public.holidays;

create policy holidays_select on public.holidays
    for select to authenticated using (true);

create policy holidays_write on public.holidays
    for all to authenticated
    using (public.is_admin()) with check (public.is_admin());

-- ---------------------------------------------------------------------
-- correction_requests
-- ---------------------------------------------------------------------
drop policy if exists corrections_select     on public.correction_requests;
drop policy if exists corrections_insert_own on public.correction_requests;
drop policy if exists corrections_admin_all  on public.correction_requests;

create policy corrections_select on public.correction_requests
    for select to authenticated
    using (employee_id = auth.uid() or public.is_admin());

create policy corrections_insert_own on public.correction_requests
    for insert to authenticated
    with check (employee_id = auth.uid() and status = 'pending');

create policy corrections_admin_all on public.correction_requests
    for update to authenticated
    using (public.is_admin()) with check (public.is_admin());

-- ---------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------
drop policy if exists audit_select on public.audit_log;
drop policy if exists audit_insert on public.audit_log;

create policy audit_select on public.audit_log
    for select to authenticated using (public.is_admin());

-- Cualquier usuario autenticado puede dejar constancia de sus propias acciones,
-- pero solo la gerencia puede leer la bitácora. Nadie puede editarla ni borrarla.
create policy audit_insert on public.audit_log
    for insert to authenticated
    with check (actor_id = auth.uid() or actor_id is null);

-- ---------------------------------------------------------------------
-- Permisos de tabla (Supabase ya otorga estos por defecto, se dejan
-- explícitos para que el script sea reproducible en un proyecto nuevo)
-- ---------------------------------------------------------------------
grant usage on schema public to authenticated;
grant select on public.settings, public.employees, public.attendance,
                public.exceptions, public.holidays, public.correction_requests,
                public.audit_log to authenticated;
grant insert, update, delete on public.employees, public.attendance,
                public.exceptions, public.holidays to authenticated;
grant insert, update on public.correction_requests to authenticated;
grant insert on public.audit_log to authenticated;
grant usage, select on sequence public.audit_log_id_seq to authenticated;
grant update on public.settings to authenticated;
