# Arquitectura y decisiones

```mermaid
flowchart LR
  U[Auditor humano] --> UI[FastAPI + Jinja + JS]
  UI --> I[Intake: límites, hash, roles, versión]
  I --> X[PDF texto / XLSX + extracción Gemini]
  X --> V[Pydantic + evidencia + confirmación]
  V --> W[Servicio de auditoría acotado]
  W --> C[Gemini: consistencia semántica]
  W --> R[Python: tarifas, duplicados, totales]
  C --> E[Consolidación determinística]
  R --> E
  E --> UI
  I --> FS[Archivos privados fuera de Git]
  V --> DB[(SQLite WAL)]
  E --> DB
```

**Implementado:** UI, contratos, fixtures normalizados, servicio de auditoría, extracción documental, persistencia SQLite WAL, reglas, mock y adaptador Gemini, CI/CD y despliegue en Fly.io.

| ADR | Elección | Coste / revisión futura |
|---|---|---|
| 01 | Monolito, un proceso Python para demo | Cola durable solo con concurrencia real |
| 02 | FastAPI/Pydantic; Jinja + JS local | Sin build Node; HTMX opcional si simplifica formularios |
| 03 | Gemini detrás de SemanticProvider | SDK directo, sin framework de agentes |
| 04 | Workflow con function calling acotado | El modelo aporta assessments; host valida y ejecuta; no hay bucle abierto |
| 05 | Decimal; ausentes nullable | Desconocido no equivale a cero; HALF_UP por línea |
| 06 | SQLite WAL + SQLAlchemy 2 + Alembic | Migrar a PostgreSQL si se requieren múltiples instancias |
| 07 | Volumen privado, IDs internos | Object storage al escalar horizontalmente; nombre nunca es ruta |
| 08 | Fly.io con TLS automático | Despliegue contenedor gestionado; sin servidor VPS manual |
| 09 | Demo pública solo cuatro fixtures | Entrada libre requiere auth, cuotas y validación de archivos |
| 10 | Subtotal de referencia | Impuestos y justificaciones no se resuelven restando anomalías |

## Responsabilidades

- `models.py`: única fuente de esquemas, sin I/O. Exportar contracts, no editarlos a mano.
- `audit/engine.py`: funciones puras; sin SDK IA, FastAPI, SQLAlchemy ni entorno.
- `agent/provider.py`: clasificar relaciones y validar citas; sin mutar importes.
- `services/audit_service.py`: integridad, checks financieros/semánticos, estado y reporte.
- `main.py`: transporte, límites y composición. Intake, extracción y repositorios en `app/api/documents.py` y `app/services/`.

## Reproducibilidad

Documentos inmutables por hash, selección activa por rol e `input_sha256` de entrada normalizada. La persistencia guardará snapshot, versiones de prompt/reglas/esquema, modelo resuelto, resultado, latencia y uso. Corregir extracción crea snapshot nuevo; nunca reescribe auditorías.

Evidence une documento, localizador y texto. Ahora línea/registro de fixture; después página/rango PDF o hoja/celda XLSX. Validar existencia de cita no garantiza respaldo semántico: medirlo con evaluación humana.

## Fallos y límites

422 entrada inválida; 413 exceso de bytes; 404 caso inexistente; 403 entrada personalizada deshabilitada.
LLM inaccesible, bloqueado, truncado o salida inválida → SEMANTIC_UNAVAILABLE/INFORMATION_REQUIRED; conservar cálculos disponibles. Tarifa no única, unidad incompatible o totales inconciliables bloquean subtotal de referencia.

Una llamada IA por auditoría normalizada; 30 s, 3.000 tokens de salida y un intento SDK por defecto. Cuatro fixtures cacheados por proceso. Reiniciar invalida cache y presupuesto: el límite local no es cuota global ni control de facturación. Un error cacheado requiere reinicio para reintentar. No hay fallback silencioso.

Antes de uploads públicos: presupuesto/idempotencia persistidos por hash+modelo+prompt, límite de concurrencia y timeout del trabajo. No abrir ingreso libre hasta completar controles.
