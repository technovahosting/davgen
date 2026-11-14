# Prompt — implementar el diseño React en base a los mockups (fase 5)

> Uso: ejecutar con Claude Code (claude) desde la raíz del proyecto, una vez
> que los mockups estén listos en 01-Mockups/ y davgen haya generado el backend.
> Claude leerá los mockups, verificará las tablas y el backend, y solo entonces
> modificará el proyecto React para que el diseño coincida con lo planificado.
>
> NO hace falta pegar nada al final: Claude Code lee los archivos directamente.

---

# Rol
Eres un desarrollador full-stack. Tu misión es hacer que el frontend React
del proyecto coincida VISUALMENTE y FUNCIONALMENTE con los mockups de
`01-Mockups/`. Sigues un proceso en 3 fases con VERIFICACIÓN en cada puerta:
NO avanzas a la siguiente fase si la anterior no está completa.

---

# FASE 1 — Analizar los mockups y validar las tablas en la BD

## Paso 1.1 — Leer los mockups
Lee TODOS los archivos de la carpeta `01-Mockups/` (HTML, imágenes, PDF o
Bolt.new bundles). Por cada pantalla o sección del mockup, identifica:
- Las **entidades** representadas (formularios, listados, tarjetas).
- Los **campos** visibles y sus tipos de dato esperados.
- La **navegación** (menú lateral, tabs, breadcrumbs) y el flujo entre pantallas.
- Los **componentes visuales** clave: tablas con paginación, modales, filtros,
  gráficos, KPIs, cards de resumen.

## Paso 1.2 — Verificar tablas en la base de datos
Con los datos de `[bd]` de `_configtotal.ini`, conecta a la BD y consulta
`INFORMATION_SCHEMA.TABLES` para verificar si existen las tablas necesarias
(`tbl___MODULO___*`). Compara contra las entidades del mockup.

**Si faltan tablas → DETENER y reportar:**
```
⛔ No se puede continuar. Faltan las siguientes tablas en la BD:
  - tbl___MODULO___{entidad1}
  - tbl___MODULO___{entidad2}

Pasos requeridos antes de continuar:
  1. Ejecutar el prompt-2-tablas-desde-mockup.md para generar el SQL.
  2. Aplicar el SQL en la BD.
  3. Ejecutar: davgen generar
  4. Volver a ejecutar este prompt.
```

**Si todas las tablas existen → continuar a Fase 2.**

---

# FASE 2 — Verificar que el backend está funcional

## Paso 2.1 — Verificar artefactos generados por davgen
Comprueba que para cada tabla existan:
- `app/Http/Controllers/{Entidad}Controller.php`
- `app/Services/{Entidad}Service.php`
- La ruta en `routes/api.php` (buscar `/{tabla}/sel`)
- El service JS `src/services/{Entidad}Service.js`

**Si faltan artefactos → DETENER y reportar:**
```
⛔ El backend no está generado para algunas entidades.
  Ejecutar: davgen generar
  Luego volver a ejecutar este prompt.
```

## Paso 2.2 — Verificar SPs en la BD
Consulta `INFORMATION_SCHEMA.ROUTINES` para confirmar que existen los
procedimientos `pcru{Entidad}` para cada tabla del proyecto.

**Si faltan SPs → DETENER y reportar:**
```
⛔ Faltan procedimientos almacenados: pcru{Entidad}
  Ejecutar: davgen generar  (con aplicar_sps=si)
```

**Si backend y SPs están completos → continuar a Fase 3.**

---

# FASE 3 — Implementar el diseño React

Ahora sí: modifica el frontend para que coincida con los mockups.
Sigue ESTRICTAMENTE estas reglas:

## Reglas OBLIGATORIAS
1. **NO editar** archivos generados por davgen:
   - `src/services/*Service.js` — solo importarlos.
   - `src/routes.jsx` — no modificar; agregar rutas propias en `App.jsx`.
   - `src/pages/generados/*` — no tocar; crear páginas propias fuera de esa carpeta.
2. **SÍ editar / crear**:
   - `src/App.jsx` — menú, rutas, layout principal.
   - `src/pages/{NombrePantalla}.jsx` — páginas con el diseño del mockup.
   - `src/components/` — componentes visuales reutilizables (cards, gráficos, etc.).
   - `src/styles/` o clases CSS/Tailwind — estilo visual.
3. **Consumir la API generada** usando los services existentes:
   ```js
   import { ProductoService } from '../services/ProductoService'
   const { info } = await ProductoService.sel({ page: 1, per_page: 25 })
   ```
4. La API siempre devuelve `{ info: { item: [...], pagination: {...} } }`.
   Implementar paginación si el mockup la muestra.
5. Los ENUM ya llegan con sus valores desde la BD; usar el service para
   mostrar las opciones en `<select>`.

## Qué implementar (derivado del mockup)
Para cada pantalla del mockup, en orden de dependencia:

### Por cada entidad
- **Listado**: tabla con las columnas del mockup, búsqueda/filtros, paginación
  (anterior/siguiente + selector de filas por página + "Mostrando X–Y de N").
- **Formulario alta/edición**: modal o página según el mockup; campos con los
  tipos correctos (ENUM → `<select>`, FK → dropdown con datos del service
  relacionado, fecha → date-picker, etc.).
- **Baja lógica**: botón "Dar de baja" / confirmación si el mockup lo muestra.

### Dashboard / pantalla principal
Si el mockup tiene KPIs, gráficos o resúmenes: implementarlos consumiendo
el endpoint `sel` de cada entidad con los filtros adecuados.

### Navegación
Replicar el menú lateral / barra superior del mockup en `App.jsx`.
Los items del menú deben corresponder a las entidades del sistema.

## Proceso de implementación
1. Explicar brevemente el plan: qué páginas se crearán/modificarán.
2. Implementar pantalla por pantalla, empezando por las entidades base
   (sin FK) y avanzando a las dependientes.
3. Después de cada pantalla, verificar que el JSX sea válido.
4. Al terminar todas las pantallas, revisar la navegación completa y
   reportar qué queda pendiente (si hay partes del mockup que requieren
   personalización adicional de backend).

## Restricciones de estilo
- Mantener la paleta de colores y tipografía del mockup.
- Si el mockup usa un framework CSS (Tailwind, daisyUI, Bootstrap),
  verificar que esté instalado antes de usarlo.
- Componentes responsive por defecto.
