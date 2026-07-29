# Control de Asistencia · Rescue de Planet de Guatemala

Aplicación web para llevar el control de asistencia del equipo: marcaje de
entrada y salida con validación por ubicación, cálculo automático de horas,
excepciones, historial personal y reportes en Excel.

**Stack:** Streamlit (interfaz) · Supabase / PostgreSQL (base de datos y
autenticación) · GitHub (código y tarea programada).

---

## Qué hace

**Para cada colaborador**

- Botón grande de *Empezar Jornada* / *Terminar Jornada* con reloj en hora de Guatemala.
- Dos modos de marcaje: **En el Edificio** (validado por GPS dentro de un radio configurable)
  y **Otro lugar** (sin restricción de distancia, pero con motivo obligatorio).
- Historial propio con calendario de colores, tabla filtrable y gráficas.
- Solicitud de corrección cuando algo quedó mal registrado.
- Cumpleaños del equipo.

**Para la gerencia (Keren Orozco)**

- Panel en vivo: quién está en jornada, quién no ha marcado, quién llegó tarde, alertas.
- Todos los registros con filtro por empleado, por fecha o por rango de fechas.
- Alta y edición de empleados: horario, días laborales, tolerancia, fecha de nacimiento.
- Excepciones: vacaciones, incapacidades, permisos, tardanzas justificadas y asuetos.
- Aprobación o rechazo de solicitudes de corrección.
- Reporte de Excel con cuatro hojas y gráficas incrustadas.
- Configuración de la geocerca y bitácora de auditoría.

---

## Reglas de cálculo

| Regla | Comportamiento |
|---|---|
| Almuerzo | Se descuenta 1 hora **solo si la jornada bruta supera 6 horas**. Configurable por empleado. |
| Tolerancia | 15 minutos antes y después de la hora de entrada y de salida. Configurable por empleado. |
| Tarde | Entrada posterior a la hora programada + tolerancia. |
| Salida temprana | Salida anterior a la hora programada − tolerancia. |
| Ausente | Día laboral sin marca y sin excepción registrada. |
| Jornada olvidada | Se cierra automáticamente a la hora programada de salida y queda marcada para revisión. |
| Horas extra | Se registran aparte; no se suman a las horas requeridas. |
| Zona horaria | Todo se calcula en `America/Guatemala` (UTC−6). |

---

## Estructura

```
streamlit_app.py            Punto de entrada y navegación
app/
  config.py                 Paleta, etiquetas y constantes
  tz.py                     Utilidades de fecha y hora de Guatemala
  db.py                     Cliente de Supabase y consultas
  auth.py                   Sesión, roles y alta de usuarios
  geo.py                    Geolocalización y distancia al edificio
  theme.py                  CSS, encabezado y capa PWA
  analytics.py              Malla diaria, resúmenes e incidencias
  reports.py                Generación del Excel
  views/                    Una pantalla por archivo
supabase/
  01_schema.sql             Tablas
  02_functions.sql          Funciones, triggers y RPC de marcaje
  03_rls.sql                Seguridad a nivel de fila
  04_seed_holidays.sql      Asuetos de Guatemala 2026–2028
scripts/
  seed_users.py             Alta inicial de los cinco usuarios
  selftest_app.py           Prueba de humo: renderiza todas las pantallas sin red
static/                     Logo, íconos y manifiesto de la PWA
.github/workflows/          Cierre automático diario de jornadas
```

---

## Seguridad

- Las marcas **nunca** se insertan directamente desde el navegador: pasan por las
  funciones `clock_in` y `clock_out` de PostgreSQL, que validan la geocerca del lado
  del servidor. Nadie puede falsificar coordenadas desde la consola del navegador.
- Row Level Security activo en todas las tablas: cada colaborador solo ve sus
  propios registros; la gerencia ve todo.
- La clave `service_role` vive solo en los secretos del servidor de Streamlit y
  nunca llega al navegador. Se usa únicamente para crear usuarios y restablecer
  contraseñas.
- Toda acción administrativa queda en la tabla `audit_log`.

---

## Instalación

Ver [DESPLIEGUE.md](DESPLIEGUE.md) para la guía paso a paso.

Para correrlo localmente:

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y llenar los valores
streamlit run streamlit_app.py
```
