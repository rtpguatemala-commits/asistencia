-- =====================================================================
-- 02_functions.sql  ·  Funciones, triggers y RPC
-- Ejecutar DESPUÉS de 01_schema.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- ¿El usuario autenticado es administrador?
-- SECURITY DEFINER para evitar recursión infinita con las políticas RLS.
-- ---------------------------------------------------------------------
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select coalesce(
        (select e.role = 'admin' and e.is_active
           from public.employees e
          where e.id = auth.uid()),
        false);
$$;

-- ---------------------------------------------------------------------
-- Distancia en metros entre dos coordenadas (fórmula de Haversine)
-- ---------------------------------------------------------------------
create or replace function public.haversine_m(
    lat1 numeric, lng1 numeric, lat2 numeric, lng2 numeric
) returns numeric
language sql
immutable
as $$
    select (
        2 * 6371000 * asin(
            sqrt(
                power(sin(radians(lat2::double precision - lat1::double precision) / 2), 2)
                + cos(radians(lat1::double precision))
                * cos(radians(lat2::double precision))
                * power(sin(radians(lng2::double precision - lng1::double precision) / 2), 2)
            )
        )
    )::numeric;
$$;

-- ---------------------------------------------------------------------
-- Recalcula horas y estado cada vez que cambia un registro de asistencia
-- ---------------------------------------------------------------------
create or replace function public.recompute_attendance()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_emp        public.employees%rowtype;
    v_in_local   timestamp;
    v_out_local  timestamp;
    v_sched_in   timestamp;
    v_sched_out  timestamp;
    v_gross      int;
    v_lunch      int;
    v_late       int := 0;
    v_early      int := 0;
    v_overtime   int := 0;
    v_late_flag  boolean;
    v_early_flag boolean;
begin
    select * into v_emp from public.employees where id = new.employee_id;
    if not found then
        raise exception 'Empleado % no existe', new.employee_id;
    end if;

    -- Horario programado para ese día, en hora local
    v_sched_in  := (new.work_date + v_emp.shift_start)::timestamp;
    v_sched_out := (new.work_date + v_emp.shift_end)::timestamp;
    if v_emp.shift_end <= v_emp.shift_start then
        v_sched_out := v_sched_out + interval '1 day';   -- turno que cruza medianoche
    end if;

    -- Sin entrada: ausencia
    if new.clock_in_at is null then
        new.status              := 'absent';
        new.gross_minutes       := null;
        new.lunch_minutes       := null;
        new.net_minutes         := null;
        new.late_minutes        := 0;
        new.early_leave_minutes := 0;
        new.overtime_minutes    := 0;
        return new;
    end if;

    v_in_local := (new.clock_in_at at time zone 'America/Guatemala');
    v_late := greatest(0, ceil(extract(epoch from (v_in_local - v_sched_in)) / 60))::int;

    -- Jornada abierta
    if new.clock_out_at is null then
        new.status              := 'open';
        new.gross_minutes       := null;
        new.lunch_minutes       := null;
        new.net_minutes         := null;
        new.late_minutes        := v_late;
        new.early_leave_minutes := 0;
        new.overtime_minutes    := 0;
        return new;
    end if;

    v_out_local := (new.clock_out_at at time zone 'America/Guatemala');
    v_gross := greatest(0, floor(extract(epoch from (v_out_local - v_in_local)) / 60))::int;

    -- Almuerzo: solo si la jornada bruta supera el umbral del empleado
    if v_gross > (v_emp.lunch_threshold_hours * 60) then
        v_lunch := v_emp.lunch_deduction_minutes;
    else
        v_lunch := 0;
    end if;
    v_lunch := least(v_lunch, v_gross);

    v_early    := greatest(0, ceil(extract(epoch from (v_sched_out - v_out_local)) / 60))::int;
    v_overtime := greatest(0, floor(extract(epoch from (v_out_local - v_sched_out)) / 60))::int;

    v_late_flag  := v_late  > v_emp.grace_minutes;
    v_early_flag := v_early > v_emp.grace_minutes;

    new.gross_minutes       := v_gross;
    new.lunch_minutes       := v_lunch;
    new.net_minutes         := v_gross - v_lunch;
    new.late_minutes        := v_late;
    new.early_leave_minutes := v_early;
    new.overtime_minutes    := v_overtime;
    new.status := case
        when v_late_flag and v_early_flag then 'late_and_early'
        when v_late_flag                  then 'late'
        when v_early_flag                 then 'early_leave'
        else 'on_time'
    end;

    if new.auto_closed then
        new.needs_review := true;
    end if;

    return new;
end;
$$;

drop trigger if exists trg_recompute_attendance on public.attendance;
create trigger trg_recompute_attendance
    before insert or update of clock_in_at, clock_out_at, employee_id, work_date, auto_closed
    on public.attendance
    for each row execute function public.recompute_attendance();

-- ---------------------------------------------------------------------
-- Marcar ENTRADA
-- ---------------------------------------------------------------------
create or replace function public.clock_in(
    p_mode      text,
    p_lat       numeric default null,
    p_lng       numeric default null,
    p_accuracy  numeric default null,
    p_reason    text    default null
) returns public.attendance
language plpgsql
security definer
set search_path = public
as $$
declare
    v_uid  uuid := auth.uid();
    v_emp  public.employees%rowtype;
    v_set  public.settings%rowtype;
    v_date date;
    v_dist numeric;
    v_row  public.attendance%rowtype;
begin
    if v_uid is null then
        raise exception 'Sesión no válida. Vuelve a iniciar sesión.';
    end if;

    select * into v_emp from public.employees where id = v_uid;
    if not found then
        raise exception 'Tu usuario no tiene perfil de empleado. Contacta a la gerencia.';
    end if;
    if not v_emp.is_active then
        raise exception 'Tu usuario está inactivo. Contacta a la gerencia.';
    end if;

    select * into v_set from public.settings where id = 1;
    v_date := (now() at time zone 'America/Guatemala')::date;

    if exists (
        select 1 from public.attendance a
         where a.employee_id = v_uid and a.work_date = v_date and a.clock_in_at is not null
    ) then
        raise exception 'Ya registraste tu entrada el día de hoy.';
    end if;

    if p_mode = 'building' then
        if p_lat is null or p_lng is null then
            raise exception 'No se pudo obtener tu ubicación. Activa el GPS y autoriza la ubicación en el navegador.';
        end if;
        if p_accuracy is not null and p_accuracy > v_set.max_gps_accuracy_m then
            raise exception 'La señal de GPS es demasiado imprecisa (± % m). Sal al aire libre e inténtalo de nuevo.',
                round(p_accuracy);
        end if;
        v_dist := public.haversine_m(p_lat, p_lng, v_set.building_lat, v_set.building_lng);
        if v_dist > v_set.building_radius_m then
            raise exception 'Estás a % metros del edificio y el máximo permitido es % metros. Acércate o marca como "Otro lugar".',
                round(v_dist), v_set.building_radius_m;
        end if;

    elsif p_mode = 'other' then
        if p_reason is null or length(btrim(p_reason)) < 5 then
            raise exception 'Debes indicar el motivo cuando marcas desde otro lugar (mínimo 5 caracteres).';
        end if;
        if p_lat is not null and p_lng is not null then
            v_dist := public.haversine_m(p_lat, p_lng, v_set.building_lat, v_set.building_lng);
        end if;

    else
        raise exception 'Modo de marcaje inválido.';
    end if;

    insert into public.attendance (
        employee_id, work_date, clock_in_at, clock_in_mode,
        clock_in_lat, clock_in_lng, clock_in_accuracy_m, clock_in_distance_m, clock_in_reason
    ) values (
        v_uid, v_date, now(), p_mode,
        p_lat, p_lng, p_accuracy, v_dist, nullif(btrim(coalesce(p_reason, '')), '')
    )
    on conflict (employee_id, work_date) do update set
        clock_in_at         = excluded.clock_in_at,
        clock_in_mode       = excluded.clock_in_mode,
        clock_in_lat        = excluded.clock_in_lat,
        clock_in_lng        = excluded.clock_in_lng,
        clock_in_accuracy_m = excluded.clock_in_accuracy_m,
        clock_in_distance_m = excluded.clock_in_distance_m,
        clock_in_reason     = excluded.clock_in_reason
    returning * into v_row;

    insert into public.audit_log (actor_id, actor_name, action, entity, entity_id, details)
    values (v_uid, v_emp.full_name, 'clock_in', 'attendance', v_row.id::text,
            jsonb_build_object('mode', p_mode, 'distance_m', v_dist, 'accuracy_m', p_accuracy));

    return v_row;
end;
$$;

-- ---------------------------------------------------------------------
-- Marcar SALIDA
-- ---------------------------------------------------------------------
create or replace function public.clock_out(
    p_mode      text,
    p_lat       numeric default null,
    p_lng       numeric default null,
    p_accuracy  numeric default null,
    p_reason    text    default null
) returns public.attendance
language plpgsql
security definer
set search_path = public
as $$
declare
    v_uid  uuid := auth.uid();
    v_emp  public.employees%rowtype;
    v_set  public.settings%rowtype;
    v_open public.attendance%rowtype;
    v_dist numeric;
    v_row  public.attendance%rowtype;
begin
    if v_uid is null then
        raise exception 'Sesión no válida. Vuelve a iniciar sesión.';
    end if;

    select * into v_emp from public.employees where id = v_uid;
    if not found then
        raise exception 'Tu usuario no tiene perfil de empleado. Contacta a la gerencia.';
    end if;

    select * into v_set from public.settings where id = 1;

    select * into v_open
      from public.attendance a
     where a.employee_id = v_uid
       and a.clock_in_at is not null
       and a.clock_out_at is null
     order by a.work_date desc
     limit 1;

    if not found then
        raise exception 'No tienes una jornada abierta. Primero marca tu entrada.';
    end if;

    if p_mode = 'building' then
        if p_lat is null or p_lng is null then
            raise exception 'No se pudo obtener tu ubicación. Activa el GPS y autoriza la ubicación en el navegador.';
        end if;
        if p_accuracy is not null and p_accuracy > v_set.max_gps_accuracy_m then
            raise exception 'La señal de GPS es demasiado imprecisa (± % m). Sal al aire libre e inténtalo de nuevo.',
                round(p_accuracy);
        end if;
        v_dist := public.haversine_m(p_lat, p_lng, v_set.building_lat, v_set.building_lng);
        if v_dist > v_set.building_radius_m then
            raise exception 'Estás a % metros del edificio y el máximo permitido es % metros. Acércate o marca como "Otro lugar".',
                round(v_dist), v_set.building_radius_m;
        end if;

    elsif p_mode = 'other' then
        if p_reason is null or length(btrim(p_reason)) < 5 then
            raise exception 'Debes indicar el motivo cuando marcas desde otro lugar (mínimo 5 caracteres).';
        end if;
        if p_lat is not null and p_lng is not null then
            v_dist := public.haversine_m(p_lat, p_lng, v_set.building_lat, v_set.building_lng);
        end if;

    else
        raise exception 'Modo de marcaje inválido.';
    end if;

    update public.attendance set
        clock_out_at         = now(),
        clock_out_mode       = p_mode,
        clock_out_lat        = p_lat,
        clock_out_lng        = p_lng,
        clock_out_accuracy_m = p_accuracy,
        clock_out_distance_m = v_dist,
        clock_out_reason     = nullif(btrim(coalesce(p_reason, '')), '')
     where id = v_open.id
    returning * into v_row;

    insert into public.audit_log (actor_id, actor_name, action, entity, entity_id, details)
    values (v_uid, v_emp.full_name, 'clock_out', 'attendance', v_row.id::text,
            jsonb_build_object('mode', p_mode, 'distance_m', v_dist, 'accuracy_m', p_accuracy));

    return v_row;
end;
$$;

-- ---------------------------------------------------------------------
-- Cierre automático de jornadas que quedaron abiertas en días anteriores
-- Se invoca desde pg_cron o desde la GitHub Action diaria.
-- ---------------------------------------------------------------------
create or replace function public.auto_close_open_shifts()
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
    v_count int := 0;
    v_today date := (now() at time zone 'America/Guatemala')::date;
    r record;
    v_sched_out timestamptz;
begin
    if not (select auto_close_enabled from public.settings where id = 1) then
        return 0;
    end if;

    for r in
        select a.id, a.work_date, a.clock_in_at, e.shift_end, e.shift_start
          from public.attendance a
          join public.employees e on e.id = a.employee_id
         where a.clock_in_at is not null
           and a.clock_out_at is null
           and a.work_date < v_today
    loop
        v_sched_out := ((r.work_date + r.shift_end)::timestamp
                        + case when r.shift_end <= r.shift_start then interval '1 day' else interval '0' end)
                       at time zone 'America/Guatemala';

        update public.attendance set
            clock_out_at   = greatest(v_sched_out, r.clock_in_at),
            clock_out_mode = clock_in_mode,
            auto_closed    = true,
            needs_review   = true,
            note = btrim(coalesce(note, '') || ' [Cerrada automáticamente por el sistema]')
         where id = r.id;

        v_count := v_count + 1;
    end loop;

    if v_count > 0 then
        insert into public.audit_log (action, entity, details)
        values ('auto_close', 'attendance', jsonb_build_object('rows', v_count));
    end if;

    return v_count;
end;
$$;

-- ---------------------------------------------------------------------
-- Aprobar una solicitud de corrección (solo administración)
-- ---------------------------------------------------------------------
create or replace function public.approve_correction(
    p_request_id uuid,
    p_review_note text default null
) returns public.attendance
language plpgsql
security definer
set search_path = public
as $$
declare
    v_uid uuid := auth.uid();
    v_req public.correction_requests%rowtype;
    v_row public.attendance%rowtype;
begin
    if not public.is_admin() then
        raise exception 'Solo la gerencia puede aprobar correcciones.';
    end if;

    select * into v_req from public.correction_requests where id = p_request_id;
    if not found then
        raise exception 'Solicitud no encontrada.';
    end if;
    if v_req.status <> 'pending' then
        raise exception 'Esta solicitud ya fue procesada.';
    end if;

    insert into public.attendance (employee_id, work_date, clock_in_at, clock_out_at, note, edited_by, edited_at)
    values (v_req.employee_id, v_req.work_date, v_req.requested_clock_in, v_req.requested_clock_out,
            'Corregida por la gerencia', v_uid, now())
    on conflict (employee_id, work_date) do update set
        clock_in_at  = coalesce(excluded.clock_in_at,  public.attendance.clock_in_at),
        clock_out_at = coalesce(excluded.clock_out_at, public.attendance.clock_out_at),
        needs_review = false,
        auto_closed  = false,
        note         = 'Corregida por la gerencia',
        edited_by    = v_uid,
        edited_at    = now()
    returning * into v_row;

    update public.correction_requests
       set status = 'approved', reviewed_by = v_uid, reviewed_at = now(), review_note = p_review_note
     where id = p_request_id;

    insert into public.audit_log (actor_id, action, entity, entity_id, details)
    values (v_uid, 'approve_correction', 'correction_requests', p_request_id::text,
            jsonb_build_object('attendance_id', v_row.id));

    return v_row;
end;
$$;

-- ---------------------------------------------------------------------
-- Permisos de ejecución
-- ---------------------------------------------------------------------
grant execute on function public.clock_in(text, numeric, numeric, numeric, text)  to authenticated;
grant execute on function public.clock_out(text, numeric, numeric, numeric, text) to authenticated;
grant execute on function public.approve_correction(uuid, text)                   to authenticated;
grant execute on function public.auto_close_open_shifts()                         to authenticated, service_role;
grant execute on function public.is_admin()                                       to authenticated;
grant execute on function public.haversine_m(numeric, numeric, numeric, numeric)  to authenticated;
