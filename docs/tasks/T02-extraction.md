# T02 · Extracción con evidencia y confirmación

Dependencia: T01. Responsable propuesto: Jose + revisión de Eduardo. Estimación 90-150 min; dividir en parser PDF, XLSX y normalizador si excede contexto.

**Leer:** modelos, T01, ai-engineering.md. **Editar:** `app/services/extraction.py`, `app/agent/extraction.py`, `tests/test_extraction.py`, fixtures documentales sintéticos. Integrador agrega dependencias de runtime pypdf/openpyxl desde el grupo documents actual.

1. PDF: extraer texto por página con pypdf y conservar página/rango. Máximo 30 páginas; cifrado, corrupto, sin texto o densidad insuficiente devuelve estado de revisión/ilegible; jamás inventar texto.
2. XLSX: openpyxl read_only, no ejecutar fórmulas; hoja/encabezados explícitos (service_code, description, unit, allowed_rate, currency, valid_from, valid_to, workshop). Rechazar fórmula en importe crítico, múltiples coincidencias y fechas ambiguas. Leer Decimal desde cadena, no desde float sin normalización documentada.
3. Contrato de extracción por campo: valor o null, evidencia de origen y motivo de revisión. Los extractores producen candidatos, no AuditInput validado automáticamente.
4. Gemini para texto ambiguo usando salida estructurada y máximo de caracteres/tokens; evidencia debe referirse a chunks creados por servidor. Describir factura frente a cotización; no mezclar versiones.
5. Normalizar líneas/tarifas y proponer equivalencias semánticas solo entre códigos existentes. Desconocido permanece desconocido y requiere confirmación. Validar vigencia/taller/unidad/moneda antes de dar tarifa única.
6. Endpoint de confirmación persiste correcciones y snapshot; solo después puede auditarse. No convertir null en cero.

**Aceptación:** A-D desde PDF con texto y XLSX sintéticos producen campos esperados; evidencia localizable por humano; caso nuevo funciona sin depender del nombre del archivo; tarifa 55/45×8 conserva 80; PDF escaneado no produce datos falsos.

**Pruebas:** unitarias sin API pagada; doble Gemini con JSON inválido/IDs falsos; prueba real opt-in aparte. `uv run pytest tests/test_extraction.py -q`, `make check`. Entregar PDF/XLSX sintéticos reproducibles, no datos reales ni copia completa de documentos oficiales. No añadir OCR externo, Pandas o RAG sin necesidad probada.
