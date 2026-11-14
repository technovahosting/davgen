# Prompts del proyecto — GENERADOS por davgen (se regeneran en cada corrida)

Cada archivo es un prompt listo para usar en el orden del proceso:

1. `prompt-1-mockup.md` — requisitos → mockup .html (01-Mockups).
2. `prompt-2-tablas-desde-mockup.md` — mockup → tablas + vistas de negocio
   (ejecutar el SQL en la BD antes de `davgen generar` con tipo=bd).
3. `prompt-3-sp-dominio.md` — operaciones de negocio (SPs `pag_*`).
4. `prompt-4-personalizacion.md` — lógica/pantallas a medida sin tocar
   el código generado.
5. `prompt-5-implementar-diseno-react.md` — implementar el diseño de los
   mockups en el proyecto React. Ejecutar con Claude Code desde la raíz
   del proyecto: primero verifica tablas y backend, luego modifica el
   frontend para que coincida visualmente con 01-Mockups/.
