# Proceso de Desarrollo de Software desde Cero

Guía práctica de la secuencia de fases para construir un software, aplicable tanto en cascada como en metodologías ágiles (en ágil, la secuencia se repite por iteración/sprint sobre incrementos pequeños).

---

## 1. Orden lógico recomendado

| # | Fase | Por qué va en este orden |
|---|------|--------------------------|
| 0 | **Levantamiento de requisitos** | Sin requisitos claros, todo lo demás es especulación. Define alcance, usuarios y casos de uso. |
| 1 | **Desarrollo de mockups** | Valida con el cliente/usuario el flujo y las pantallas **antes** de escribir código. Es la forma más barata de detectar errores de concepto. Además, los mockups revelan qué datos necesita cada pantalla. |
| 2 | **Diseño de base de datos** | Los mockups exponen las entidades y relaciones reales (qué se muestra, qué se captura). Diseñar el modelo de datos después de los mockups evita re-trabajo en el esquema. El modelo de datos es el cimiento: cambiarlo tarde es lo más costoso. |
| 3 | **Desarrollo del backend** | Con el esquema definido, se construyen la lógica de negocio y la API. Definir primero el **contrato de la API** (ej. OpenAPI/Swagger) permite que el frontend trabaje en paralelo contra mocks. |
| 4 | **Desarrollo del frontend** | Consume la API y materializa los mockups. Hacerlo después (o en paralelo con contrato definido) evita construir pantallas contra endpoints que no existen o cambiarán. |
| 5 | **Testing** | Pruebas de integración, E2E y UAT sobre el sistema completo. **Ojo:** el testing unitario NO espera hasta aquí — se escribe junto con backend y frontend (ver sección 2). |
| 6 | **Despliegue y monitoreo** | Release a producción, observabilidad y feedback para la siguiente iteración. |

**Regla de oro:** cada fase reduce la incertidumbre de la siguiente. Mockups → qué datos; modelo de datos → qué API; API → qué consume el frontend.

---

## 2. Carpetas de este proyecto (creadas por davgen)

| Carpeta | Fase | Qué va aquí |
|---|---|---|
| `00-Requisitos/` | 0 | Alcance, usuarios, casos de uso |
| `01-Mockups/` | 1 | Wireframes y mockups (.html o carpeta React) |
| `02-Base-de-datos/` | 2 | Modelo ER, diccionario, scripts (davgen copia `00-seguridad.sql` + `readme_cero.md`) |
| `03-Backend/` | 3 | Proyecto Laravel + `_backendGenerado/` (davgen lo crea/genera) |
| `04-Frontend/` | 4 | Proyecto React (davgen genera servicios y páginas en `frontend/src/`) |
| `05-Testing/` | 5 | Pruebas (davgen copia `api.http`, checklist y configuración en `generados/`) |

**Siguiente paso:** completar `_configtotal.ini` ([proyecto], [entrada] y [bd]) y volver a ejecutar `davgen generar`.
