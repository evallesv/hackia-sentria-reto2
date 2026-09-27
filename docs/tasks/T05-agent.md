# T05 · Validar Gemini y reforzar orquestación

Dependencias: T02/T04; el adaptador normalizado puede probarse antes. Responsable propuesto: Eduardo. 60-90 min.

**Editar:** `app/agent/`, `app/services/audit_service.py`, `tests/test_provider.py`, evaluación real. Sin cambiar fórmulas.

1. Seleccionar modelo desde la cuenta con `scripts.list_gemini_models`; registrar identificador exacto, soporte y modalidad. No asumir acceso por tener una clave.
2. Ejecutar `scripts.smoke_gemini` con sintéticos. Capturar estado, tokens, latencia y errores seguros; nunca imprimir clave/prompts completos.
3. Mantener una herramienta permitida, desactivar automatic function calling, un intento y timeout. Si se añade plan, permitir solo checks enumerados y unirlo siempre con checks obligatorios del host.
4. Validar todas las líneas exactamente una vez y referencias reales/activas. supported exige factura+siniestro+inspección; comprobar respaldo semántico en el corpus, no solo existencia de IDs.
5. Incluir fallos 429, timeout, bloqueos, truncado, texto en lugar de herramienta, tool desconocida, argumentos incorrectos e intento de saltar revisión dentro del documento.
6. Cache de producción por snapshot+modelo+prompt+reglas, presupuesto compartido e idempotencia con T03; en demo fija mantener límite por proceso explícito.

**Aceptación:** ninguna salida inválida causa candidato; errores conservan resultados financieros y solicitan revisión; no hay llamadas ocultas ni instrucciones de documentos ejecutadas. Separar trazas de ejecución de razonamiento interno.

**Validación:** tests SDK simulados + `make check`; opt-in real A-C + 12-20 casos reservados T07. Reportar medidas, no «alta precisión» sin denominador. Si un modelo barato falla repetidamente, presentar caso mínimo y evaluar otro; no ampliar autonomía.
