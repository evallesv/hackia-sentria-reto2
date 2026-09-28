# T04 · Completar reglas documentales sin IA

Dependencia: T00. Responsable propuesto: Jose; revisión financiera por Eduardo. 45-75 min.

**Editar:** `app/audit/engine.py`, módulos puros adicionales en `app/audit/`, tests de reglas. Contratos solo mediante integrador. No importar SDK ni persistencia.

Baseline (montos con 7% ITBMS incluido / diferencia neta sin impuestos): A=1979.50/0; B=2065.10/80; C=2600.10/250; D=sin tarifa/INFORMATION_REQUIRED. Mantener esos resultados y no usar cálculos del LLM.

1. Integrar tarifa aplicable por taller, unidad, moneda y fecha según contrato T02. Sin coincidencia/varias → información requerida. No convertir divisas ni inferir tipo de cambio.
2. Separar total declarado, total calculado, diferencias propuestas y base de impuesto. Política configurable de tolerancia decimal (default exactitud a centavos); no ocultar diferencias con tolerancia implícita.
3. Duplicados: firma incluye alcance/parte/zona cuando exista; una repetición legítima puede representar dos partes distintas. Mantener hallazgo de posible duplicado, no imputar fraude. Exacto ≠ semántico.
4. Precedencia de hallazgos e impactos explícita; sobreprecio en duplicado no se suma dos veces. Incertidumbre semántica no genera importe.
5. Cantidad atípica solo con umbral de negocio documentado y fuente/configuración; no inventar «80 horas imposible» como regla universal.

**Aceptación:** tests de frontera por centavo, cantidad fraccionaria, tarifa vencida, moneda/unidad incompatible, duplicado legítimo, triple repetición y sobreprecio repetido; no candidato con información faltante. Invariante `0 ≤ diferencia ≤ base calculada` para entradas coherentes; reordenación no altera agregados de grupos idénticos.

**Validación:** tests de escenarios (no copiar algoritmo como expected), `make check`. Entregar fórmula/política en contracts.md si cambia semántica. No denominar subtotal de referencia «monto aprobado».
