# Ingeniería de IA y criterios de calidad

## Responsabilidad de la IA

Gemini interpreta relaciones entre siniestro, inspección y líneas. El host obliga una sola herramienta `submit_claim_assessments`, valida Pydantic, cobertura exacta de líneas y referencias activas. El SDK no ejecuta herramientas automáticamente. La herramienta registra evaluaciones; el servicio ejecuta verificaciones financieras y consolida. Es un workflow agéntico acotado, no un asistente con permisos generales.

En simulación se comparan códigos de daño; eso **no demuestra comprensión de documentos**. En modo Gemini se enviará texto de evidencia y descripciones; el proveedor puede ver cualquier dato incluido allí. El prompt no es un mecanismo suficiente de aislamiento.

Para extracción futura: primero parser local por página/celda; después Gemini solo sobre texto relevante. PDF escaneado sin texto → información requerida/OCR pendiente, nunca inventar lectura. JSON estructurado debe validarse y mostrar campos dudosos para confirmación. El modelo no decide moneda, impuestos o tarifa válida sin fuentes.

## Seguridad de herramientas

Documentos son entrada no confiable: separar instrucciones del sistema y datos serializados. No registrar herramientas de navegación, shell, correo, archivos arbitrarios ni pago. La lista permitida vive en código. Una instrucción incrustada no cambia checks, prompt, destino de red o estado final. Tratar también la salida del modelo como no confiable; rechazar IDs desconocidos, líneas omitidas, claves adicionales y salida truncada. La UI usa textContent y escape de plantillas.

No ocultar fallos: conservar cálculos obtenidos, devolver incertidumbre y ofrecer revisión. No usar un mock como fallback del LLM real.

## Coste y latencia

- Una llamada de consistencia, hasta 3.000 tokens de salida y 30 s por defecto. Incluye tokens de pensamiento reportados en métrica de salida.
- Entrada HTTP hasta 256 KiB; datos de dominio también acotados. En T02 usar presupuesto adicional de caracteres/páginas por archivo antes de enviar al LLM.
- SDK con un intento; no reparar JSON en un bucle. Como máximo una reparación explícita futura, incluida en presupuesto, si las evaluaciones lo justifican.
- Caché de cuatro casos de prueba por proceso. La cuota de 20 intentos por proceso es barrera de demo, no techo de gasto mensual. Configurar límites del proyecto Gemini y alertas de facturación por separado.
- Seleccionar el modelo pequeño que pase el corpus; escalar por fallos medidos, no por marca. Dejar GEMINI_MODEL explícito y registrar versión devuelta.
- Estimar coste con tarifas verificadas de la cuenta: entrada_tokens × tarifa_entrada + salida_tokens × tarifa_salida, por millón si esa es la unidad tarifaria. No se inventan precios en el repositorio.

## Evaluaciones

| Nivel | Qué prueba | Puerta de aceptación |
|---|---|---|
| Unitario | Decimal, redondeo, duplicados, conflictos, referencias, faltantes | 100% de importes/estados esperados; ningún candidato con bloqueo |
| API | Validación, límites reales de bytes, modo, casos de prueba, HTML | Todos los casos y errores definidos |
| Adaptador con doble SDK | Argumentos, herramienta permitida, truncado, errores, límites | Sin ejecución libre ni resultados falsamente exitosos |
| Gemini real opt-in | Conectividad y contrato con A-C | Tres salidas válidas, conservar discrepancias financieras; no prueba generalización |
| Dataset reservado T07 | 12-20 expedientes sintéticos distintos de prompts/examples | Cero falsos candidatos en casos críticos; 100% de citas existentes; exactitud financiera 100% |
| End-to-end T07 | Archivos → extracción → confirmación → auditoría → reporte | A-D desde PDF/XLSX y expediente no visto, en URL pública |

Medir por separado exactitud de campos extraídos, cobertura de evidencia, tasa de citas respaldadas revisada por humano, precisión/recall por tipo de hallazgo, tasa de abstención, latencia p50/p95, tokens y coste por expediente. Objetivos iniciales de extracción ≥95% en campos críticos y recall de anomalías ≥90% sobre corpus reservado; son metas del equipo, **no resultados medidos**. Cualquier fallo en importe crítico obliga confirmación aunque mejore la media.

Dataset adicional: siniestro frontal/reparación trasera, tarifa hora versus unidad, dos versiones, sin tarifario, PDF sin texto, total alterado, duplicado legítimo en zonas distintas, línea repetida sobrevalorada, tasa efectiva fuera de fecha, moneda no soportada, prompt injection, timeout. Separar casos de desarrollo de casos reservados y no afinar prompts contra el reservado.

Trazas permitidas: run_id, hashes, modelo, versiones, tools ejecutadas, códigos, latencia, tokens, resultado. No guardar secretos, texto íntegro de documentos o cadena de pensamiento en logs. Cambiar prompt/modelo/regla exige repetir evaluación relevante y guardar comparación con baseline.

## Fuentes técnicas consultadas

- [Google Gen AI SDK](https://googleapis.github.io/python-genai/): cliente, function declarations, timeout y control de ejecución automática.
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling): funciones con argumentos estructurados.
- [OWASP: prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): separación de datos y autoridad, validación y permisos mínimos.
- [Pydantic: validación estricta](https://docs.pydantic.dev/latest/concepts/strict_mode/): controlar coerción; aquí dinero añade validación específica para rechazar floats.
