# Guía de uso de la plataforma

## Probar la preparación actual

1. Arranca con los comandos del README y abre http://127.0.0.1:8000.
2. Lee la banda de modo. **Simulación** no llama a IA; **Gemini** solicita la revisión al proveedor, pero cualquier fallo aparece en el resultado.
3. Elige B y pulsa Auditar expediente. El botón se desactiva mientras se procesa.
4. Comprueba factura 1.930 USD, diferencia potencial 80 USD y subtotal de referencia 1.850 USD.
5. Abre RATE_MISMATCH. Lee la fórmula y las dos fuentes: línea de pintura y tarifa contratada.
6. Abre el recorrido para ver integridad, checks y consolidación. Descarga el reporte JSON.
7. Ejecuta A: sin discrepancias, candidato para revisión final humana. Ejecuta C: tarifa + duplicado + reparación sin respaldo. Ejecuta D: falta tarifario; pedir información.

Los ejemplos ya están normalizados. «Consultar datos de entrada» abre el JSON del fixture. Todavía no hay botón de carga documental; será T01/T02/T06. No cargar datos reales en esta preparación.

## Interpretar el resultado

- **Candidato para aprobación:** los checks ejecutados no detectaron discrepancias. No es pago autorizado.
- **Revisión requerida:** analizar los hallazgos y su evidencia; solicitar explicación o corrección.
- **Información requerida:** falta algo necesario o no pudo completarse el análisis. Corregir antes de decidir.

La diferencia es potencial y sin impuestos; no es ahorro probado. Un posible duplicado necesita confirmación. Una reparación sin respaldo no se descuenta automáticamente. «No disponible» no equivale a cero. D muestra «No evaluado»; el JSON conserva un acumulado cero y una traza sin comprobación tarifaria.

## Probar Gemini

Configura la clave localmente en `.env`, consulta modelos con `scripts.list_gemini_models`, fija GEMINI_MODEL y AI_MODE=gemini. Reinicia servidor y vuelve a B. Revisa que aparezcan modelo y tokens. SEMANTIC_UNAVAILABLE significa que no hubo revisión semántica completa; revisar configuración/cuota sin exponer la clave. `healthz` solo verifica proceso.

La demo conserva el primer resultado de cada caso en memoria; repetir no repite gasto. Reiniciar vacía cache, también errores. `scripts.smoke_gemini` hace hasta tres llamadas nuevas y no reutiliza la cache del servidor.

## Laboratorio JSON local

Solo si necesitas probar contratos, configura ENABLE_CUSTOM_INPUT=true en entorno local; reinicia y envía un fixture modificado a POST /api/audits mediante `/docs`. Los compose públicos fuerzan esta opción a false. No existe upload binario por este endpoint; importes deben ser cadenas decimales.

## Guion de demostración (opcional, 2-3 min)

0:00 problema: factura de 2.430 USD. 0:20 ejecutar C. 0:45 explicar 80 USD de tarifa y 170 USD de posible duplicado; abrir evidencia. 1:20 señalar reparación que requiere justificación. 1:40 mostrar A como control. 2:00 mostrar D y abstención. 2:20 explicar IA para interpretación y Python para importes, con decisión humana. Identificar modo mock si eso se está mostrando; para entrega final usar Gemini real y flujo documental completo.

## Flujo objetivo, pendiente de implementación

Nuevo expediente → cuatro archivos → tipo/versión → revisión de campos y fuentes → confirmar → auditar → hallazgos → decisión humana fuera del sistema. Los pasos pendientes están en docs/tasks/ y deben actualizar esta guía al implementarse.
