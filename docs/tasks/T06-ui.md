# T06 · Plataforma documental y guiado

Dependencias: T01/T03; trabajar primero contra contratos y fixtures. Responsable propuesto: Santiago. 75-120 min.

**Editar:** templates/, static/, `app/api/ui.py` y pruebas de interfaz. Integrador conecta router. No recalcular dinero en JavaScript.

Construir flujo: crear expediente → subir siniestro/inspección/factura o cotización/tarifario → seleccionar versiones → ver extracción → confirmar/corregir datos → auditar → revisar hallazgos/evidencia → descargar reporte.

Cada rol indica formato/límite/ejemplo. Mostrar nombres y errores sin exponer ruta. Estado de procesamiento y botón deshabilitado durante operación; retry visible y seguro. Unknown no se muestra como 0. Las correcciones piden fuente/motivo y conservan original. No ocultar funciones faltantes detrás de botones que simulan éxito.

Vista de resultados: tres estados traducidos, importe declarado, diferencias potenciales, subtotal de referencia, moneda, cálculo, evidencia navegable por página/celda, modo/modelo y aviso de decisión humana. No sumar impacts de findings en navegador; usar agregado del servidor. Descargar JSON y vista imprimible si cabe, sin añadir librería pesada.

Guía contextual de tres pasos y enlace a explicación detallada. Teclado, foco visible, labels, mensajes aria-live y vista móvil 375px. Renderizar texto no confiable con escape/textContent; no innerHTML con salida IA.

**Aceptación:** usuario nuevo completa A-D sin explicación oral, identifica caso incompleto, cambia versión y corrige campo antes de auditar; evidencia corresponde a archivo mostrado. Demo pública restringida a sintéticos; uploads privados requieren controles de T07.

**Validación:** `make check`, recorrido real navegador desktop/móvil, teclado y fallo proveedor. Actualizar user-guide.md con comportamiento real. No introducir React/chat/dashboard.
