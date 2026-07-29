-- =====================================================================
-- 05_correcciones.sql
--
-- Corrige las llaves foráneas que apuntan a public.employees para que
-- se pueda dar de baja definitivamente a una persona.
--
-- Problema que resuelve: si un empleado tiene entradas en la bitácora,
-- excepciones que él creó o registros que editó, al intentar eliminar su
-- cuenta Supabase respondía "Database error deleting user" y la operación
-- fallaba a medias. Ahora esos campos quedan en NULL y el historial se
-- conserva, pero la cuenta se puede eliminar sin problemas.
--
-- Es seguro ejecutarlo varias veces.
-- Ejecutar en: Supabase → SQL Editor → New query → pegar → Run
-- =====================================================================

alter table public.attendance
    drop constraint if exists attendance_edited_by_fkey;
alter table public.attendance
    add constraint attendance_edited_by_fkey
    foreign key (edited_by) references public.employees (id) on delete set null;

alter table public.exceptions
    drop constraint if exists exceptions_created_by_fkey;
alter table public.exceptions
    add constraint exceptions_created_by_fkey
    foreign key (created_by) references public.employees (id) on delete set null;

alter table public.correction_requests
    drop constraint if exists correction_requests_reviewed_by_fkey;
alter table public.correction_requests
    add constraint correction_requests_reviewed_by_fkey
    foreign key (reviewed_by) references public.employees (id) on delete set null;

alter table public.audit_log
    drop constraint if exists audit_log_actor_id_fkey;
alter table public.audit_log
    add constraint audit_log_actor_id_fkey
    foreign key (actor_id) references public.employees (id) on delete set null;
