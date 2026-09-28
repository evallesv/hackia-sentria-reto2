# Verificación de la preparación

Fecha: 27/09/2026. Cambios locales sin commit/push. Esta tabla acredita el starter, no el MVP documental futuro.

| Comprobación | Resultado | Alcance |
|---|---|---|
| `uv sync --all-groups` y lock/export | PASS | Entorno Python 3.13.13 creado; dependencias bloqueadas y hashes |
| `make check` | PASS | Ruff lint/formato, 64 pruebas, cuatro golden cases |
| SDK Gemini con doble de respuesta | PASS | Tipos reales del SDK; herramienta permitida, presupuesto, errores y salida inválida |
| Evaluación mock A-D | PASS | A candidato/0; B revisión/80; C revisión/250; D información/0 no evaluado |
| Hashes de documentos sintéticos | PASS | SHA-256 comparado con archivos de data/demo/sources |
| Requirements vs export frozen | PASS | Sin diferencias, export sin encabezado dependiente de ruta |
| JSON Schemas | GENERADOS | Exportados desde Pydantic; CI verificará drift |
| `node --check static/app.js` | PASS | Sintaxis JS |
| `git diff --check` | PASS | Cambios tracked sin errores de whitespace |
| Enlaces Markdown locales | PASS | Destinos de enlaces relativos existentes |
| `docker build` / `docker compose up -d --build` | PASS | Imagen Linux aarch64; dependencias hash-checked instaladas |
| Contenedor | PASS | Proceso con UID 10001, healthz OK, read-only y puerto 127.0.0.1:8000 |
| A-D por HTTP dentro del contenedor | PASS | Estados y diferencias esperadas |
| Navegador integrado | PASS | Caso B: $2,065.10 facturado / $80.00 diferencia / $1,850.00 subtotal con evidencia; D: sin tarifario / INFORMATION_REQUIRED |
| Despliegue en la nube (Fly.io) | PASS | Producción activa en Ashburn (iad) con HTTPS: https://sentria.fly.dev |
| Auditoría en vivo en producción | PASS | Caso A en https://sentria.fly.dev/api/demo/A/audit (1.6s, 760 in / 159 out tokens) |
| PDF de herramientas (make tools-pdf) | PASS | Dos páginas compiladas con ReportLab y actualizadas con métricas de entrega |
| PDF/XLSX → normalización (T06) | PASS | T01-T03 y T06: subida interactiva, extracción con evidencia localizable y auditoría en vivo |

Starlette emitió una advertencia de deprecación del TestClient basado en httpx. Las 64 pruebas pasaron. Migrar el cliente de prueba al actualizar ese stack; no se ocultó la advertencia.

## Entorno que queda funcionando

Demo simulada local: http://127.0.0.1:8000. Proyecto Compose `hackia-sentria-reto2`, servicio `web`. No se publicó en internet ni se enviaron entregables.

```bash
docker compose ps
docker compose stop                  # detener sin borrar imagen ni configuración
docker compose up -d                 # volver a arrancar
```

Para seguir desde código: detener el contenedor antes de `make dev` si ambos usan 8000. Nunca convertir resultados mock en métricas de precisión del modelo. Actualizar esta tabla después de T07 con commit, URL real, modelo, corpus y resultados.
