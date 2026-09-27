# T07 · Evaluación integrada y Oracle ARM64

Dependencias: T02-T06. Responsable propuesto: Eduardo con validación Santiago. 90-120 min más DNS.

**Editar:** tests/e2e, scripts de evaluación, deploy/, compose, docs/verification.md y deployment-oracle.md. No tocar reglas para acomodar expected sin justificar defecto.

1. Corpus reservado 12-20 sintéticos distinto de prompts. Anotar expected y fuentes antes de ejecutar. Medir métricas de ai-engineering.md; guardar modelo/commit/fecha, denominadores, falsos candidatos y límites.
2. E2E desde cuatro archivos de A-D; incluir factura nueva, no solo fixture. Validar borrado y separación de expedientes.
3. Build nativo ARM64 con dependencias locked; tests CI en 3.12/3.13. Verificar Docker health/read_only/usuario no root. Si se requiere DB, migración y volumen privado.
4. Seguir runbook Oracle: DNS, NSG/security list y firewall SO, SSH restringido, HTTPS Caddy, sin puerto DB/web directo público. Registrar commit e imagen reproducible; no usar «latest» como identificación de release.
5. Activar Gemini con secretos locales; controlar presupuesto; no publicar uploads libres hasta auth/rate limiting y validaciones completadas. Demo fija puede abrirse antes, identificada con su alcance.
6. Probar desde red externa: HTTPS, A-D, modo real, citas, errores, límites y reinicio. Smoke local no demuestra enlace público.
7. Ensayar rollback a imagen/commit anterior sin destruir volumen; backup de DB antes de migraciones.

**Aceptación:** URL pública real, checks verdes y resultados reproducibles; cero falsos candidatos críticos. No datos personales en logs/screenshots. Reportar explícitamente controles no implementados.

**Entrega:** URL, commit, comandos ejecutados, métricas y matriz PASS/FAIL/NO EJECUTADO; nunca declarar despliegue por tener un compose válido.
