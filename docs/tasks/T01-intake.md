# T01 · Intake seguro y contratos documentales

Dependencia: baseline T00. Responsable propuesto: Jose; contratos revisados por Eduardo. Estimación 60-90 min. Modelo económico primero; escalar solo por esquema/seguridad.

**Leer:** models.py, contracts.md, privacy.md. **Editar:** nuevos `app/services/intake.py`, `app/api/documents.py`, `tests/test_intake.py`; contratos/main/dependencias solo con integrador. No implementar IA ni UI aquí.

1. Acordar contratos 1.1: Claim, StoredDocument (UUID, claim_id, rol, mime, byte_count, sha256, versión, activo, ruta interna no expuesta), ExtractionJob. No sobrecargar AuditInput con estado de almacenamiento.
2. Recibir streams con límites reales (10 MiB/archivo, 4 roles; versiones adicionales acotadas), comprobar PDF/XLSX por contenido y extensión. Rechazar ejecutables, XLSM, path traversal, archivo vacío y exceso de ZIP expandido.
3. Calcular SHA-256 de bytes; guardar en ruta generada fuera de static; metadatos y permisos por expediente. Mismo hash no se borra automáticamente: devolver duplicado y pedir selección.
4. Versiones: ninguna selección automática por nombre «final»; el usuario elige una activa. Cambio invalida snapshot pendiente, no auditorías históricas.
5. Añadir API definida en contracts.md con repositorio inyectable; usar doble de memoria mientras T03 se integra.

**Aceptación:** cuatro archivos válidos se registran con hashes reproducibles; faltantes producen información requerida; dos facturas activas producen conflicto; documento de otro claim no es accesible; PDF corrupto y ZIP excesivo fallan de forma controlada; no hay rutas absolutas en respuesta.

**Pruebas:** `uv run pytest tests/test_intake.py -q`, `make check`, `make contracts`. Casos límite: nombre `../../x`, MIME falso, 10 MiB+1, archivo repetido, versión inactiva, acceso cruzado. Entregar contratos y ejemplos para T02/T03/T06. No afirmar soporte OCR.
