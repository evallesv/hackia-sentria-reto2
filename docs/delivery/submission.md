# Borrador de presentación al filtro previo · Equipo Sentria

**Destinatario:** `hackiathon@viamatica.com`  
**Asunto:** Filtro previo hackIAthon Panamá - Reto 2 - Equipo Sentria

---

Estimado comité evaluador de hackIAthon Panamá:

El equipo **Sentria** presenta al **filtro previo de hackIAthon Panamá** su prototipo funcional para el **Reto 2**, orientado a revisar cotizaciones de talleres antes de autorizar reparaciones y emitir facturas.

Sentria contrasta la cotización con el reporte del siniestro, el informe de inspección y un tarifario estándar reutilizable. Prepara observaciones, referencias documentales y diferencias monetarias para la revisión del analista.

Es una **aplicación con IA integrada y un flujo agéntico acotado**. El servidor coordina las verificaciones y Gemini interpreta documentos mediante respuestas estructuradas y *function calling*. Python valida las referencias, aplica los controles obligatorios y realiza los cálculos financieros con aritmética exacta. El modelo no decide libremente la secuencia ni autoriza reparaciones o pagos.

El sistema emite únicamente tres estados: **candidato para aprobación**, **revisión requerida** o **información requerida**. La decisión final corresponde al analista humano.

### Material para la evaluación

1. **Aplicación de demostración:**
   * **Plataforma Web:** [https://sentria.fly.dev](https://sentria.fly.dev)
   * **Healthcheck del Sistema:** [https://sentria.fly.dev/healthz](https://sentria.fly.dev/healthz)
   * **Usuario:** `jurado` · **Contraseña:** `Sentria-Reto2-2026!`.

2. **Repositorio de Código:**
   * **GitHub:** [https://github.com/evallesv/hackia-sentria-reto2](https://github.com/evallesv/hackia-sentria-reto2)
   * Incluye código fuente completo, contratos Pydantic y JSON Schemas, suite automatizada de pruebas de comportamiento, datos de prueba sintéticos y pipelines de CI/CD (GitHub Actions).

3. **Registro de herramientas de IA:**
   * Documento para adjuntar: `docs/delivery/herramientas-ia.pdf`, con el registro de las herramientas utilizadas durante la preparación.

4. **Instrucciones para Evaluación Rápida:**
   * Acceder a [https://sentria.fly.dev](https://sentria.fly.dev). Usuario `jurado`, contraseña `Sentria-Reto2-2026!`.
   * **Caso A (Sin discrepancias):** Pulsa "Auditar". Los controles del caso sintético no detectan discrepancias (estado: candidato para aprobación, diferencia $0.00).
   * **Caso B (Discrepancia tarifaria):** Pulsa "Auditar". Detecta sobrecosto en tarifa de pintura: (55 − 45) × 8 = $80.00 USD (revisión requerida).
   * **Caso C (Múltiples anomalías):** Detecta alineación duplicada y sobrecosto tarifario ($250.00 USD de diferencia potencial). El respaldo de la reparación de dirección requiere revisión del analista.
   * Para probar archivos sintéticos propios, pulsa «Crear expediente y subir documentos». El tarifario se incorpora automáticamente; Gemini clasifica y extrae los tres PDF (cotización, declaración e inspección). Revisa y corrige los datos antes de confirmar y auditar. Los PDF escaneados requieren OCR pendiente.
   * En cada caso se puede expandir la traza de auditoría, las citas textuales de la evidencia y descargar el reporte estructurado en JSON.

### Equipo: Sentria

* **Eduardo Valle** (Representante) | [LinkedIn](https://linkedin.com/in/evallesv)
* **Jose Muñoz** | [LinkedIn](https://linkedin.com/in/jose-salcedo-442663293)
* **Santiago López** | [LinkedIn](https://linkedin.com/in/santiago-lopez-software-engineer)

### Alcance y evaluación pendiente

* **Determinismo financiero:** El LLM no calcula dinero ni determina el estado operativo final. Clasifica, extrae información y evalúa la correspondencia documental; Python valida sus resultados.
* **Seguridad y Privacidad:** Datos de prueba 100% sintéticos. Claves del proveedor fuera del control de versiones; credenciales compartidas del jurado documentadas para evaluación.
* **Trazabilidad:** Las referencias deben existir en los documentos activos. La pertinencia de la interpretación requiere revisión humana.
* **Límites de la evaluación:** Las pruebas automatizadas validan reglas, contratos y fallos del sistema. Los casos sintéticos y las comprobaciones puntuales con Gemini no demuestran precisión general con todos los formatos de proveedores ni ahorro de tiempo en operación real. Los PDF escaneados requieren OCR, pendiente de implementación.

Presentamos este prototipo como base para continuar su desarrollo y evaluación durante la hackIAthon.

Gracias por considerar nuestra propuesta.

Atentamente,\
**Eduardo Valle**\
Representante del equipo Sentria

---

**Registro de envío:** Eduardo Valle confirmó en la conversación que el correo fue enviado. Este archivo conserva el borrador preparado y sus límites en ese momento; no se verificó el buzón ni el contenido del mensaje enviado. Las mejoras posteriores al envío se documentan en la arquitectura y el README.
