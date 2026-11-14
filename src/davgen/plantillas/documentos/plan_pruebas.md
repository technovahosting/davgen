# Plan de pruebas — (nombre del proyecto)

> PLANTILLA davgen · fase 5 — el smoke test E2E ya lo genera davgen en
> `generados\pruebas-api.ps1` (login+2FA+CRUD por tabla, local o nube).
> Aquí se planifican y registran las pruebas MANUALES (UAT).

## 1. Smoke test generado

```powershell
.\generados\pruebas-api.ps1                    # backend local
.\generados\pruebas-api.ps1 -Api {url}/servicio/api   # nube
```

PASS = correcto · WARN = escritura rechazada por regla de dominio (normal)
· FAIL = defecto a corregir.

## 2. Casos de prueba manuales (UAT)

| # | Caso | Pasos | Resultado esperado | Estado |
|---|---|---|---|---|
| 1 | (ej: confirmar pedido sin stock) | (completar) | (mensaje de error claro) | pendiente |

## 3. Reporte de ejecución

| Fecha | Versión | PASS | WARN | FAIL | Observaciones |
|---|---|---|---|---|---|
| (completar) | | | | | |
