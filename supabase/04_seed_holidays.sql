-- =====================================================================
-- 04_seed_holidays.sql  ·  Asuetos oficiales de Guatemala 2026 – 2028
--
-- Incluye los feriados nacionales del Código de Trabajo más el
-- 15 de agosto (Virgen de la Asunción), que es asueto local para la
-- Ciudad de Guatemala, donde está el edificio de la organización.
--
-- El 24 y el 31 de diciembre están marcados como medio día.
-- El 10 de mayo (Día de la Madre) aplica solo a trabajadoras madres:
-- se deja registrado para referencia; puedes borrarlo desde el panel.
-- =====================================================================

insert into public.holidays (date, name, is_half_day) values
    -- ---------------- 2026 ----------------
    ('2026-01-01', 'Año Nuevo',                            false),
    ('2026-04-02', 'Jueves Santo',                         false),
    ('2026-04-03', 'Viernes Santo',                        false),
    ('2026-04-04', 'Sábado Santo',                         false),
    ('2026-05-01', 'Día del Trabajo',                      false),
    ('2026-05-10', 'Día de la Madre',                      false),
    ('2026-06-30', 'Día del Ejército',                     false),
    ('2026-08-15', 'Virgen de la Asunción (Ciudad de Guatemala)', false),
    ('2026-09-15', 'Día de la Independencia',              false),
    ('2026-10-20', 'Día de la Revolución',                 false),
    ('2026-11-01', 'Día de Todos los Santos',              false),
    ('2026-12-24', 'Nochebuena',                           true),
    ('2026-12-25', 'Navidad',                              false),
    ('2026-12-31', 'Fin de Año',                           true),

    -- ---------------- 2027 ----------------
    ('2027-01-01', 'Año Nuevo',                            false),
    ('2027-03-25', 'Jueves Santo',                         false),
    ('2027-03-26', 'Viernes Santo',                        false),
    ('2027-03-27', 'Sábado Santo',                         false),
    ('2027-05-01', 'Día del Trabajo',                      false),
    ('2027-05-10', 'Día de la Madre',                      false),
    ('2027-06-30', 'Día del Ejército',                     false),
    ('2027-08-15', 'Virgen de la Asunción (Ciudad de Guatemala)', false),
    ('2027-09-15', 'Día de la Independencia',              false),
    ('2027-10-20', 'Día de la Revolución',                 false),
    ('2027-11-01', 'Día de Todos los Santos',              false),
    ('2027-12-24', 'Nochebuena',                           true),
    ('2027-12-25', 'Navidad',                              false),
    ('2027-12-31', 'Fin de Año',                           true),

    -- ---------------- 2028 ----------------
    ('2028-01-01', 'Año Nuevo',                            false),
    ('2028-04-13', 'Jueves Santo',                         false),
    ('2028-04-14', 'Viernes Santo',                        false),
    ('2028-04-15', 'Sábado Santo',                         false),
    ('2028-05-01', 'Día del Trabajo',                      false),
    ('2028-05-10', 'Día de la Madre',                      false),
    ('2028-06-30', 'Día del Ejército',                     false),
    ('2028-08-15', 'Virgen de la Asunción (Ciudad de Guatemala)', false),
    ('2028-09-15', 'Día de la Independencia',              false),
    ('2028-10-20', 'Día de la Revolución',                 false),
    ('2028-11-01', 'Día de Todos los Santos',              false),
    ('2028-12-24', 'Nochebuena',                           true),
    ('2028-12-25', 'Navidad',                              false),
    ('2028-12-31', 'Fin de Año',                           true)
on conflict (date) do nothing;
