# Contratos v1 y API

Fuente ejecutable: `app/models.py`. Derivados en `contracts/`; regenerar con `make contracts`.

## Entrada

AuditInput: claim_id, billing_kind INVOICE/QUOTE, currency USD, documentos, evidencia, daños reportados/inspeccionados, líneas, tarifas, subtotal/impuestos/total. Importes como cadenas (`"55.00"`); rechazar floats, NaN, infinito y negativos. Cantidad positiva con hasta cuatro decimales; ausentes como null.

Línea: ID estable, servicio, daño, unidad HOUR/UNIT, importes y evidencia. El starter exige códigos normalizados. T02 debe devolver mapeo confirmado o desconocido, nunca forzar coincidencia; evolucionar contrato con tests. Solo USD, sin conversión. `taxes` es declarado: se verifica suma, no validez fiscal.

Documento: ID, rol, nombre descriptivo, SHA-256 y selección activa. Referencias de línea al rol correcto y documento activo; evidencia a documento existente. JSON personalizado declara hashes: **el futuro intake debe verificarlos contra bytes**. Los hashes de casos de prueba sí se comprueban contra archivos locales.

## Salida

| Campo | Semántica |
|---|---|
| billed_amount | Total declarado, incluyendo impuestos declarados |
| flagged_difference | Diferencia potencial sin impuestos, no ahorro realizado |
| reference_subtotal | Subtotal menos diferencias sin solapamiento; null ante bloqueo |
| findings | Código, descripción, línea, cálculo, impacto, referencias y blocking |
| trace | Etapas, sin cadena de pensamiento |
| mode/model | Simulado o Gemini y modelo reportado |
| rule_version/prompt_version/input_sha256 | Reproducción y comparación |

Precedencia: bloqueo → información requerida; otros hallazgos → revisión requerida; ninguno → candidato para aprobación. Las evaluaciones semánticas del modelo (respaldado/no respaldado/incierto) no son estados finales.

Exceso por línea: `max(0, precio − tarifa) × cantidad`, redondeado. Duplicado: firma exacta de campos normalizados y descripción sin distinguir mayúsculas; es posible duplicado, no fraude. Máximo impacto por línea evita sumar precio completo y sobreprecio. Se conserva la primera aparición. Reparación sin respaldo produce revisión sin descuento arbitrario.

## API actual

| Método/ruta | Función |
|---|---|
| GET `/` | Interfaz guiada |
| GET `/healthz` | Salud del proceso/modo; no prueba conexión Gemini |
| GET `/api/demo/{A\|B\|C\|D}` | Entrada sintética |
| POST `/api/demo/{A\|B\|C\|D}/audit` | Auditoría de caso de prueba, almacenada en memoria por proceso |
| POST `/api/audits` | JSON local; requiere ENABLE_CUSTOM_INPUT=true |
| GET `/docs` | OpenAPI; Swagger puede requerir internet |

```bash
curl -X POST http://127.0.0.1:8000/api/demo/B/audit
```

## API Documental y de Ingesta (v1)

Los endpoints de gestión de expedientes implementados en `app/api/documents.py` (creación de expedientes, carga de documentos, extracción, confirmación de normalización y auditoría en vivo) están documentados automáticamente en la especificación OpenAPI:

```bash
curl http://127.0.0.1:8000/openapi.json
```

O explorar visualmente en [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (requiere internet para cargar Swagger UI).
