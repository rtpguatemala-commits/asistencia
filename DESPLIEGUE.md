# Guía de despliegue

Tiempo estimado: **20 a 25 minutos**. No hace falta saber programar; son cinco
pasos de copiar y pegar.

Vas a necesitar las tres cuentas que ya tienes abiertas:

- GitHub: `rtpguatemala-commits`
- Supabase: proyecto *rtpguatemala-commits's Project*
- Streamlit Community Cloud: `rtpguatemala-commits`

---

## Paso 1 · Crear el repositorio en GitHub

1. En la pantalla **Create a new repository** que ya tienes abierta:
   - **Repository name:** `rdp-asistencia`
   - **Description:** `Control de asistencia · Rescue de Planet de Guatemala`
   - **Visibility:** elige **Private**. El repositorio no contiene contraseñas,
     pero es información interna de la organización.
   - Deja *Add README*, *.gitignore* y *license* como están (en Off / None).
2. Clic en **Create repository**.
3. En la página que aparece, clic en **uploading an existing file**.
4. Arrastra **todo el contenido** de la carpeta `rdp-asistencia` que te entregué
   (no la carpeta en sí, sino los archivos y subcarpetas que hay dentro).
5. Escribe como mensaje `Versión inicial` y clic en **Commit changes**.

> Si la carpeta `.github` no se sube al arrastrar (algunos navegadores ocultan las
> carpetas que empiezan con punto), no pasa nada: solo se pierde el cierre
> automático de jornadas. Puedes agregarla después con *Add file → Create new file*
> escribiendo la ruta `.github/workflows/auto_close.yml`.

---

## Paso 2 · Preparar la base de datos en Supabase

1. Entra a tu proyecto de Supabase y abre **SQL Editor** en el menú lateral.
2. Clic en **New query**.
3. Abre el archivo `supabase/01_schema.sql`, copia **todo** su contenido, pégalo
   en el editor y clic en **Run**. Debe decir *Success. No rows returned*.
4. Repite exactamente lo mismo, en este orden, con:
   - `supabase/02_functions.sql`
   - `supabase/03_rls.sql`
   - `supabase/04_seed_holidays.sql`

   Es normal que aparezcan avisos amarillos que dicen *does not exist, skipping*.
   Eso solo significa que no había nada previo que reemplazar.

5. Verifica que quedó bien: ve a **Table Editor**. Debes ver las tablas
   `settings`, `employees`, `attendance`, `exceptions`, `holidays`,
   `correction_requests` y `audit_log`. La tabla `holidays` debe traer 42 filas.

---

## Paso 3 · Copiar las llaves del proyecto

1. En Supabase, ve a **Project Settings → API**.
2. Anota estos tres valores (los vas a pegar en el paso 4):

   | Dato | Dónde está |
   |---|---|
   | **Project URL** | Arriba, algo como `https://nlugzjafvkfqlqghmuju.supabase.co` |
   | **anon public** | En *Project API keys* |
   | **service_role** | En *Project API keys*, hay que darle clic al ojito para verla |

> La llave `service_role` da acceso total a la base de datos. No la compartas ni
> la escribas en ningún archivo del repositorio. Solo va en los secretos de
> Streamlit, que están cifrados.

---

## Paso 4 · Publicar la app en Streamlit

1. Entra a `share.streamlit.io` y clic en **Create app** (arriba a la derecha).
2. Elige **Deploy a public app from GitHub**.
3. Llena así:
   - **Repository:** `rtpguatemala-commits/rdp-asistencia`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** elige algo corto y fácil de escribir en un celular, por ejemplo
     `asistencia-rdp`. Queda como `https://asistencia-rdp.streamlit.app`.
4. **Antes de darle Deploy**, clic en **Advanced settings** y en el cuadro
   *Secrets* pega esto, reemplazando los valores con los del paso 3:

   ```toml
   SUPABASE_URL = "https://xxxxxxxx.supabase.co"
   SUPABASE_ANON_KEY = "eyJ...la llave anon..."
   SUPABASE_SERVICE_KEY = "eyJ...la llave service_role..."
   ```

   En *Python version* elige **3.11** o **3.12**.
5. Clic en **Deploy**. La primera vez tarda entre 2 y 4 minutos instalando las
   librerías. Cuando termine verás la pantalla de inicio de sesión.

---

## Paso 5 · Crear los usuarios

Tienes dos caminos. El primero es más rápido.

### Opción A · Desde tu computadora (recomendado)

1. Abre el archivo `scripts/seed_users.py` y edita la lista `EMPLEADOS`:
   pon el **correo real** de cada persona y su **fecha de nacimiento** si ya la tienes.
2. En una terminal:

   ```bash
   pip install supabase
   export SUPABASE_URL="https://xxxxxxxx.supabase.co"
   export SUPABASE_SERVICE_KEY="eyJ...la llave service_role..."
   python scripts/seed_users.py
   ```

3. Al final imprime las contraseñas temporales de cada persona. Guárdalas y
   entrégaselas de forma segura; ellos podrán cambiarlas desde *Mi perfil*.

### Opción B · Desde la propia aplicación

1. Crea primero **solo la cuenta de Keren** en Supabase:
   **Authentication → Users → Add user → Create new user**.
   Marca *Auto Confirm User*, pon su correo y una contraseña.
2. Copia el **User UID** que aparece en la lista.
3. Ve a **Table Editor → employees → Insert row** y llena:

   | Campo | Valor |
   |---|---|
   | `id` | el User UID que copiaste |
   | `full_name` | `Keren Orozco` |
   | `email` | su correo |
   | `role` | `admin` |
   | `position` | `Gerente de Recursos Humanos` |
   | `birth_date` | `1991-12-28` |
   | `shift_start` | `07:00` |
   | `shift_end` | `16:00` |

   Los demás campos ya traen valor por defecto.
4. Entra a la app con esa cuenta. Desde **Gerencia → Empleados → Nuevo empleado**
   ya puedes crear a las otras cuatro personas con sus horarios:

   | Persona | Entrada | Salida |
   |---|---|---|
   | Edgar Dávila | 09:00 | 18:00 |
   | Eddie Bustamante | 07:30 | 16:30 |
   | Ellie Gonzáles | 10:00 | 19:00 |
   | José Izquierdo | 10:00 | 15:00 |

---

## Paso 6 · Activar el cierre automático (opcional pero recomendado)

Cierra cada noche las jornadas que alguien olvidó terminar y las deja marcadas
para tu revisión.

1. En GitHub, ve a tu repositorio → **Settings → Secrets and variables → Actions**.
2. Clic en **New repository secret** y crea dos:
   - `SUPABASE_URL` con el Project URL.
   - `SUPABASE_SERVICE_KEY` con la llave service_role.
3. Ve a la pestaña **Actions** del repositorio y activa los workflows si te lo pide.
4. Para probarlo ahora mismo: **Actions → Cierre automático de jornadas →
   Run workflow**.

Corre todos los días a las 11:00 de la noche, hora de Guatemala.

---

## Paso 7 · Instalar la app en los teléfonos

Manda el enlace de la app a cada persona y pídeles que hagan esto una vez:

**Android (Chrome)** — abrir el enlace, menú ⋮, *Agregar a pantalla principal*.

**iPhone (Safari)** — abrir el enlace, botón de compartir, *Agregar a inicio*.

Queda con el ícono de la organización y se abre a pantalla completa, sin barra
de navegador.

> En iPhone hay que asegurarse de que la ubicación esté permitida:
> *Ajustes → Safari → Ubicación → Preguntar* o *Permitir*.

---

## Después de instalar: prueba de campo

Antes de anunciarlo al equipo, haz esta prueba parada dentro del edificio:

1. Entra con tu cuenta desde el celular.
2. Elige **En el Edificio**. La app te va a mostrar la distancia al punto central
   y la precisión que reporta tu teléfono.
3. Si la distancia sale mayor a 50 metros aunque estés adentro, ve a
   **Gerencia → Configuración** y sube el radio a 75 u 80 metros.
4. Repite la prueba desde distintos puntos del edificio (recepción, oficinas del
   fondo, segundo nivel) antes de fijar el valor definitivo.

Es normal que el GPS de un celular tenga entre 20 y 50 metros de error dentro de
un edificio de concreto. Por eso el radio es configurable desde el panel.

---

## Preguntas frecuentes

**¿Qué pasa si alguien no tiene señal o niega el permiso de ubicación?**
No podrá usar el modo *En el Edificio*. Puede marcar como *Otro lugar* poniendo
el motivo; el registro queda visible para ti con esa nota.

**¿La app se puede usar sin internet?**
No. Necesita conexión para registrar la marca en la base de datos.

**¿Por qué la app tarda unos segundos en abrir la primera vez del día?**
Las apps del plan gratuito de Streamlit se duermen tras un rato sin uso y
despiertan solas. Después del primer acceso responde normal.

**¿Se pierden los datos si la app se duerme?**
No. Todo vive en Supabase, no en la app.

**¿Qué hago si un colaborador ya no trabaja aquí?**
En *Empleados → Editar*, desmarca **Usuario activo**. Así conservas todo su
historial para efectos de reportes y auditoría.
