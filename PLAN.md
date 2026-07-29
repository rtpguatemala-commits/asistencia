# Sistema de Control de Asistencia
## Rescue de Planet de Guatemala (ONG)

**Versión del plan:** 1.0 — 29 de julio de 2026
**Stack:** GitHub + Supabase (PostgreSQL + Auth) + Streamlit Community Cloud
**Zona horaria:** América/Guatemala (UTC-6, sin horario de verano)

---

## 1. Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Login | Email + contraseña vía Supabase Auth. Keren crea los usuarios. |
| Almuerzo | Se descuenta 1 hora solo si la jornada supera 6 horas. José Izquierdo conserva sus 5 h. |
| PWA | Streamlit responsivo + manifiesto e ícono para "Agregar a pantalla de inicio". |
| Olvidos | Cierre automático a la hora programada, marcado "pendiente de revisión" + solicitud de corrección que Keren aprueba o rechaza. |
| Geocerca | "En el Edificio" bloquea totalmente fuera de los 50 m. |
| Otro lugar | Motivo obligatorio + se guardan las coordenadas reales igual. |
| Excepciones | Vacaciones, incapacidad/médico, permiso personal, asuetos oficiales de Guatemala. |
| Reporte Excel | Detalle diario + resumen consolidado + hoja de incidencias + gráficas incrustadas. |
| Keren | Doble rol en una sola cuenta: marca su asistencia y administra. |
| Marcas por día | Una jornada: Empezar Jornada / Terminar Jornada. |
| Alertas | Panel interno de alertas + aviso de cumpleaños próximos. |

---

## 2. Empleados y horarios

| Empleado | Entrada | Salida | Jornada bruta | Almuerzo | Horas netas/día | Horas/semana |
|---|---|---|---|---|---|---|
| Edgar Dávila | 9:00 | 18:00 | 9 h | −1 h | **8 h** | 40 h |
| Eddie Bustamante | 7:30 | 16:30 | 9 h | −1 h | **8 h** | 40 h |
| Ellie Gonzáles | 10:00 | 19:00 | 9 h | −1 h | **8 h** | 40 h |
| Keren Orozco (gerente) | 7:00 | 16:00 | 9 h | −1 h | **8 h** | 40 h |
| José Izquierdo | 10:00 | 15:00 | 5 h | 0 h | **5 h** | 25 h |

Todos trabajan de lunes a viernes.
Tolerancia: **15 minutos antes y después** de la hora de entrada y de salida.

### Cómo se clasifica cada día

- **A tiempo:** marca de entrada dentro de `[entrada − 15 min, entrada + 15 min]`.
- **Tarde:** entrada después de `entrada + 15 min`. Se guardan los minutos de retraso.
- **Salida temprana:** salida antes de `salida − 15 min`.
- **Ausente:** día laboral sin ninguna marca y sin excepción registrada.
- **Jornada abierta:** hay entrada pero no salida al cierre del día → cierre automático y bandera de revisión.
- **Justificado:** existe una excepción aprobada por Keren para ese día.

---

## 3. Modelo de datos (Supabase / PostgreSQL)

### `employees`
Perfil de cada persona, ligado a `auth.users`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | = `auth.users.id` |
| `full_name` | text | |
| `email` | text | único |
| `role` | text | `admin` \| `employee` |
| `birth_date` | date | para el módulo de cumpleaños |
| `position` | text | cargo dentro de la ONG |
| `shift_start` | time | ej. 09:00 |
| `shift_end` | time | ej. 18:00 |
| `works_days` | int[] | `{1,2,3,4,5}` = lunes a viernes |
| `lunch_threshold_hours` | numeric | 6 por defecto |
| `lunch_deduction_minutes` | int | 60 por defecto |
| `grace_minutes` | int | 15 por defecto |
| `is_active` | boolean | para dar de baja sin borrar historial |
| `avatar_url` | text | opcional |

### `attendance`
Un registro por empleado por día.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `employee_id` | uuid FK | |
| `work_date` | date | fecha en hora de Guatemala |
| `clock_in_at` | timestamptz | |
| `clock_out_at` | timestamptz | |
| `clock_in_mode` | text | `building` \| `other` |
| `clock_out_mode` | text | `building` \| `other` |
| `clock_in_lat/lng` | numeric | coordenadas reales capturadas |
| `clock_out_lat/lng` | numeric | |
| `clock_in_distance_m` | numeric | distancia al edificio |
| `clock_out_distance_m` | numeric | |
| `other_location_reason` | text | obligatorio si el modo es `other` |
| `auto_closed` | boolean | true si lo cerró el sistema |
| `needs_review` | boolean | |
| `gross_minutes` | int | calculado |
| `lunch_minutes` | int | calculado |
| `net_minutes` | int | calculado |
| `late_minutes` | int | |
| `early_leave_minutes` | int | |
| `status` | text | `on_time` \| `late` \| `early_leave` \| `late_and_early` \| `open` \| `absent` |

Restricción: `UNIQUE (employee_id, work_date)`.

### `exceptions`
Excepciones que registra Keren.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `employee_id` | uuid FK | |
| `date_from` / `date_to` | date | permite rangos (vacaciones) |
| `type` | text | `vacation` \| `sick_leave` \| `personal_leave` \| `justified_late` \| `day_off` |
| `note` | text | |
| `attachment_url` | text | nota médica, etc. (Supabase Storage) |
| `paid` | boolean | si cuenta como horas trabajadas |
| `created_by` | uuid | |

### `holidays`
Asuetos oficiales de Guatemala, precargados y editables.

| Campo | Tipo |
|---|---|
| `id`, `date`, `name`, `is_national` |

**Asuetos de Guatemala precargados:** 1 de enero, Jueves Santo, Viernes Santo, Sábado de Gloria, 1 de mayo, 30 de junio, 15 de septiembre, 20 de octubre, 1 de noviembre, 24 de diciembre (medio día), 25 de diciembre, 31 de diciembre (medio día). Semana Santa se calcula automáticamente cada año.

### `correction_requests`
Solicitudes de corrección de los empleados.

| Campo | Tipo |
|---|---|
| `id`, `attendance_id`, `employee_id`, `requested_clock_in`, `requested_clock_out`, `reason`, `status` (`pending`/`approved`/`rejected`), `reviewed_by`, `reviewed_at`, `review_note` |

### `audit_log`
Bitácora de todo cambio hecho por la administración: quién, qué, cuándo, valor anterior y nuevo.

### `settings`
Configuración global editable por Keren: coordenadas del edificio, radio en metros, minutos de tolerancia, hora de cierre automático.

### Seguridad (Row Level Security)
- Un empleado solo puede **leer y escribir** sus propios registros de asistencia.
- Un empleado solo puede **leer** su propio perfil, sus excepciones y sus solicitudes.
- El rol `admin` puede leer y escribir todo.
- Toda la validación de geocerca y de horarios se hace del lado del servidor (funciones RPC en Postgres), no en el navegador, para que nadie pueda falsificar coordenadas desde la consola.

---

## 4. Pantallas

### Empleado
1. **Inicio / Marcar** — reloj grande con hora de Guatemala, tarjeta de estado ("Aún no has marcado" / "Jornada iniciada a las 9:03"), selector **En el Edificio / Otro lugar**, botón grande **Empezar Jornada** o **Terminar Jornada**, y el resumen de horas del día.
2. **Mi historial** — calendario mensual con colores por estado, tabla filtrable por rango de fechas.
3. **Mis estadísticas** — horas trabajadas por semana, puntualidad, comparación contra horas esperadas.
4. **Cumpleaños del equipo** — próximos cumpleaños del mes.
5. **Solicitar corrección** — formulario ligado a un día específico.

### Gerente (Keren) — todo lo anterior más:
6. **Panel en vivo** — quién está dentro ahora mismo, quién no ha marcado, alertas del día.
7. **Todos los registros** — filtro por empleado, por fecha o rango de fechas, por estado.
8. **Empleados** — alta, edición de horarios, fecha de nacimiento, cargo, activar/desactivar.
9. **Excepciones** — registrar vacaciones, incapacidades, permisos, asuetos.
10. **Solicitudes** — aprobar o rechazar correcciones pendientes.
11. **Reportes** — generar el Excel por rango de fechas y por empleado o todos.
12. **Configuración** — coordenadas, radio, tolerancia, hora de cierre automático.

---

## 5. Reporte en Excel

Un solo archivo `.xlsx` con cuatro hojas:

1. **Detalle diario** — fila por empleado por día: fecha, día de la semana, horario programado, entrada real, salida real, modo de marca, ubicación, minutos de retraso, salida temprana, almuerzo descontado, horas netas, estado, observaciones.
2. **Resumen** — por empleado: días laborales, días trabajados, horas esperadas, horas trabajadas, diferencia, tardanzas, salidas tempranas, ausencias, excepciones.
3. **Incidencias** — solo los días con problema.
4. **Gráficas** — barras de horas trabajadas vs. esperadas por empleado, y tendencia de puntualidad.

Con formato: encabezados en la paleta de la ONG, celdas condicionales (verde a tiempo, ámbar tarde, rojo ausente), anchos automáticos y filtros activados.

---

## 6. Diseño visual

Tomando el logo (águila + león + ballena en blanco sobre negro):

| Uso | Color |
|---|---|
| Fondo principal | `#0B0B0D` (negro carbón) |
| Superficies / tarjetas | `#17181C` |
| Texto principal | `#F5F5F4` |
| Acento primario | `#E8B84B` (dorado cálido — botones de acción) |
| Éxito / a tiempo | `#3FB27F` |
| Advertencia / tarde | `#E9A13B` |
| Error / ausente | `#D2544B` |

Tipografía Inter. Interfaz completa en español. Botones de marcar de al menos 56 px de alto para uso con el pulgar. Todo el layout se adapta a teléfono, tablet, laptop y monitor.

---

## 7. Estructura del repositorio

```
rdp-asistencia/
├── streamlit_app.py          # punto de entrada y enrutador
├── requirements.txt
├── .streamlit/
│   ├── config.toml           # tema visual
│   └── secrets.toml.example  # plantilla de credenciales
├── app/
│   ├── auth.py               # login, sesión, roles
│   ├── db.py                 # cliente de Supabase
│   ├── timezone.py           # utilidades de hora de Guatemala
│   ├── attendance.py         # lógica de marcas y cálculo de horas
│   ├── geo.py                # distancia haversine y validación de geocerca
│   ├── reports.py            # generación del Excel
│   ├── theme.py              # CSS y paleta
│   └── views/                # una pantalla por archivo
├── supabase/
│   ├── 01_schema.sql
│   ├── 02_rls.sql
│   ├── 03_functions.sql
│   ├── 04_seed_holidays.sql
│   └── 05_seed_employees.sql
├── static/
│   ├── logo.png
│   ├── icon-192.png
│   ├── icon-512.png
│   └── manifest.json
└── README.md
```

---

## 8. Plan de trabajo

1. Esquema SQL, RLS, funciones y datos semilla (asuetos + empleados).
2. Núcleo de la app: autenticación, tema visual, utilidades de zona horaria y geolocalización.
3. Pantallas del empleado: marcar, historial, estadísticas, cumpleaños.
4. Panel de la gerente: en vivo, registros, empleados, excepciones, solicitudes.
5. Motor de reportes en Excel.
6. Capa PWA: manifiesto, íconos, meta etiquetas.
7. Cierre automático de jornadas (tarea programada).
8. Pruebas con datos de ejemplo y despliegue en Streamlit Community Cloud.

---

## 9. Riesgos y consideraciones

- **Precisión del GPS.** Elegiste bloqueo total dentro de los 50 m para el modo "Edificio". En celulares el GPS típico tiene un error de 5 a 20 m, y bajo techo puede llegar a 50 m o más. Recomiendo: (a) que la app muestre en pantalla la distancia y la precisión reportada por el dispositivo, y (b) considerar un radio de 75–100 m si en las pruebas hay falsos rechazos. La opción "Otro lugar" sigue disponible, así que nadie queda sin poder marcar.
- **Permisos del navegador.** El empleado debe autorizar la ubicación una vez. Si la deniega, no podrá usar el modo "Edificio".
- **Suspensión de Streamlit Cloud.** Las apps gratuitas se duermen tras un periodo de inactividad y tardan unos segundos en despertar. Es aceptable para 5 usuarios, pero conviene saberlo.
- **Cierre automático.** Streamlit no ejecuta tareas en segundo plano. Se resuelve con una función programada de Supabase (`pg_cron`) o una GitHub Action diaria.
- **Nivel gratuito de Supabase.** Los proyectos gratuitos se pausan tras una semana sin actividad. Con uso diario no ocurrirá.
