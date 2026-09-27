# Verificación de la preparación

Fecha: 27/09/2026. Cambios locales sin commit/push. Esta tabla acredita el starter, no el MVP documental futuro.

| Comprobación | Resultado | Alcance |
|---|---|---|
| `uv sync --all-groups` y lock/export | PASS | Entorno Python 3.13.13 creado; dependencias bloqueadas y hashes |
| `make check` | PASS | Ruff lint/formato, 38 pruebas, cuatro golden cases |
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
| Navegador integrado | PASS | Casos B y D: 1930/80/1850 con evidencia; incompleto con No evaluado/No disponible |
| Compose local y Oracle `config --quiet` | PASS | Configuración validada; dominio ficticio solo para validación Oracle |
| Caddy `validate` | PASS | Configuración de proxy/HTTPS válida, sin emitir certificado público |
| PDF de herramientas (`make tools-pdf`) | PASS | Dos páginas renderizadas e inspeccionadas con reportlab, sin texto cortado |
| Sincronización lock/requirements (`make lock`) | PASS | uv.lock y requirements.txt sincronizados con hashes reproducibles |
| Autoformato y lint (`make format`) | PASS | Corrección automática y formato ruff sin regresiones |
| Gemini real | NO EJECUTADO | No se proporcionaron claves/modelo; no se midió calidad real |
| OpenCode Go | NO EJECUTADO | Guía y configuración preparadas; ningún trabajo atribuido a ese proveedor |
| CI remota y Python 3.12 | NO EJECUTADO | Workflow preparado, sin push; local probado con 3.13 |
| Oracle, DNS, TLS público | NO EJECUTADO | No se recibió host/dominio/acceso |
| PDF/XLSX → auditoría | PENDIENTE | T01-T06; fixtures actuales ya están normalizados |

Observación de dependencias: Starlette emitió una advertencia de deprecación del TestClient basado en httpx. Las 38 pruebas pasaron. Migrar el cliente de prueba al actualizar ese stack; no se ocultó la advertencia.

## Entorno que queda funcionando

Demo simulada local: http://127.0.0.1:8000. Proyecto Compose `hackia-sentria-reto2`, servicio `web`. No se publicó en internet ni se enviaron entregables.

```bash
docker compose ps
docker compose stop                  # detener sin borrar imagen ni configuración
docker compose up -d                 # volver a arrancar
```

Para seguir desde código: detener el contenedor antes de `make dev` si ambos usan 8000. Nunca convertir resultados mock en métricas de precisión del modelo. Actualizar esta tabla después de T07 con commit, URL real, modelo, corpus y resultados.
