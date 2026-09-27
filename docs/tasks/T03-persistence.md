# T03 · Persistencia y auditorías reproducibles

Dependencia: contrato documental T01; puede diseñarse con doble de repositorio mientras termina intake. Responsable propuesto: Jose, integración Eduardo. 60-90 min.

**Editar:** `app/db/`, `app/repositories/`, `migrations/`, tests de integración DB. Settings, compose y pyproject coordinados con integrador. No tocar motor ni proveedor.

Implementar SQLAlchemy 2 + Alembic y PostgreSQL en red interna Docker. Tablas Claim, Document, ExtractionSnapshot, AuditRun; claves foráneas, timestamps UTC, hashes e índices de claim. Numerics exactos cuando haya importes; snapshots JSON serializan Decimal como cadena. Auditoría inmutable con entrada/salida, versión de regla/prompt/esquema, modelo, latencia/tokens y modo.

Registro de archivo + metadatos debe compensar fallos para evitar huérfanos. Selección activa transaccional; una por rol. Idempotencia por claim+snapshot_hash+rule_version+prompt_version+model; no reutilizar resultado tras cambios. No cachear información de un usuario bajo otro.

Crear migración inicial, comando de upgrade, volumen persistente privado y prueba de reinicio. Credenciales vía entorno; DB sin puerto público. Borrado de claim debe eliminar documentos/snapshots/resultados y archivos de forma observable/reintentable. Añadir purge por política con dry-run y pruebas; no borrar archivos ajenos.

**Aceptación:** resultado idéntico tras reinicio; sin doble auditoría por retry; snapshot anterior preservado al corregir datos; fallo DB deja respuesta controlada; migración desde DB vacía; aislamiento entre claims. Documentar backup/restore y retención.

**Validación:** tests transaccionales contra PostgreSQL de prueba y `make check`. Las pruebas de memoria no bastan para declarar PostgreSQL verificado. No ejecutar migraciones destructivas en datos existentes.
