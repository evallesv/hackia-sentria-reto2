let selectedCase = 'B';
let activeClaimId = 'CLM-2026-DEMO-B';
let currentSnapshot = null;
let lastAuditResult = null;

const byId = id => document.getElementById(id);
const currency = value => (value === null || value === undefined)
  ? 'No disponible'
  : new Intl.NumberFormat('es-PA', {style: 'currency', currency: 'USD'}).format(Number(value));

const labels = {
  CANDIDATE_FOR_APPROVAL: 'Candidato para aprobación · requiere decisión humana',
  REVIEW_REQUIRED: 'Revisión requerida',
  INFORMATION_REQUIRED: 'Información requerida'
};

const roleNames = {
  BILLING_DOCUMENT: 'Cotización del taller',
  INCIDENT_REPORT: 'Declaración de siniestro',
  WORKSHOP_REPORT: 'Informe pericial',
  TARIFF: 'Tarifario de convenio'
};

const findingTitles = {
  RATE_MISMATCH: 'Discrepancia en tarifa convenida',
  DUPLICATE_ITEM: 'Cobro posiblemente duplicado',
  CLAIM_INCONSISTENCY: 'Reparación ajena o no respaldada en el siniestro',
  TARIFF_UNRESOLVED: 'Tarifario inexistente o no convenido',
  MISSING_INFORMATION: 'Información obligatoria faltante en el expediente',
  TOTAL_MISMATCH: 'Discrepancia en la sumatoria de totales declarados',
  TAX_CALCULATION_MISMATCH: 'Cálculo de impuestos incorrecto en cotización',
  LINE_TOTAL_MISMATCH: 'Error de cálculo aritmético en línea de cobro',
  SEMANTIC_UNCERTAIN: 'Correspondencia de daño incierta',
  SEMANTIC_UNAVAILABLE: 'Revisión asistida no disponible temporalmente',
  DOCUMENTS_MISSING: 'Documentos contractuales obligatorios no cargados',
  DOCUMENTS_AMBIGUOUS: 'Conflicto entre versiones de documentos activos'
};

const traceStepsInfo = {
  'integrity_check': {
    title: 'Comprobación de integridad documental',
    description: 'Verificación de autenticidad, unicidad de hashes SHA-256 por archivo y disponibilidad de los documentos requeridos del expediente.'
  },
  'quote_check': {
    title: 'Validación del tipo de comprobante',
    description: 'Cotejo de la modalidad de liquidación (factura final de cobro vs. cotización de taller).'
  },
  'tariff_check': {
    title: 'Auditoría determinista de tarifas y duplicados',
    description: 'Contraste matemático exacto de precios unitarios contra el tarifario convenido y detección de posibles cobros redundantes.'
  },
  'submit_claim_assessments:validated': {
    title: 'Evaluación de consistencia de daños (Gemini IA)',
    description: 'Análisis de correspondencia semántica asistida entre la descripción del choque y los componentes reparados o sustituidos.'
  },
  'claim_check:simulated': {
    title: 'Evaluación de consistencia de daños (Modo local)',
    description: 'Validación de correspondencia entre los códigos de daño del siniestro y las líneas cotizadas.'
  },
  'claim_check:unavailable': {
    title: 'Evaluación de correspondencia interrumpida',
    description: 'El servicio asistido no completó la revisión; el caso queda marcado para intervención humana obligatoria.'
  },
  'deterministic_consolidation': {
    title: 'Consolidación financiera y clasificación final',
    description: 'Cálculo de diferencias potenciales sin impuestos, proyección del subtotal de referencia y determinación del estado operativo.'
  }
};

// 1. Selector de casos preparados (A, B, C, D)
document.querySelectorAll('[data-case]').forEach(button => {
  button.addEventListener('click', () => {
    selectedCase = button.dataset.case;
    document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    activeClaimId = `CLM-2026-DEMO-${selectedCase}`;
    const claimInput = byId('claim-id-input');
    if (claimInput) claimInput.value = activeClaimId;
    loadPresetIntoWorkbench(selectedCase);
    byId('run').textContent = `⚡ Auditar expediente ${selectedCase} inmediatamente →`;
    byId('run').hidden = false;
    byId('input-link').hidden = false;
    byId('input-link').href = `/api/demo/${selectedCase}`;
    byId('result').hidden = true;
    byId('progress').textContent = '';
  });
});

// Botón para alternar formulario de subida
const toggleUploadBtn = byId('toggle-upload-btn');
const wbUploadPanel = byId('wb-upload-panel');
if (toggleUploadBtn && wbUploadPanel) {
  toggleUploadBtn.addEventListener('click', () => {
    wbUploadPanel.hidden = !wbUploadPanel.hidden;
    toggleUploadBtn.textContent = wbUploadPanel.hidden ? '+ Subir o reemplazar documento' : '✕ Ocultar formulario';
  });
}

// Botón para alternar visualizador de datos extraídos
const toggleDataBtn = byId('toggle-data-btn');
const wbViewer = byId('wb-extraction-viewer');
if (toggleDataBtn && wbViewer) {
  toggleDataBtn.addEventListener('click', () => {
    wbViewer.hidden = !wbViewer.hidden;
    toggleDataBtn.textContent = wbViewer.hidden ? 'Inspeccionar ítems y tarifas extraídos ↓' : 'Ocultar datos extraídos ↑';
  });
}

// 2. Renderizado de resultados de auditoría
function renderAuditResult(auditResult) {
  lastAuditResult = auditResult;
  byId('status').textContent = labels[auditResult.status] || auditResult.status;
  byId('status').dataset.status = auditResult.status;
  byId('billed').textContent = currency(auditResult.billed_amount);
  byId('difference').textContent = (auditResult.trace && auditResult.trace.includes('tariff_check'))
    ? currency(auditResult.flagged_difference)
    : 'No evaluado';
  byId('reference').textContent = currency(auditResult.reference_subtotal);

  const findingsContainer = byId('findings');
  findingsContainer.replaceChildren();

  if (!auditResult.findings || !auditResult.findings.length) {
    const p = document.createElement('p');
    p.textContent = 'No se detectaron discrepancias en las comprobaciones ejecutadas.';
    findingsContainer.append(p);
  } else {
    auditResult.findings.forEach(finding => {
      const card = document.createElement('details');
      card.open = true;

      const summary = document.createElement('summary');
      const friendlyTitle = findingTitles[finding.code] || finding.code;
      const itemLabel = finding.item_id ? ` · Ítem: ${finding.item_id}` : '';
      summary.textContent = `${friendlyTitle}${itemLabel}`;

      const p = document.createElement('p');
      p.textContent = finding.description;
      card.append(summary, p);

      if (finding.calculation) {
        const calc = document.createElement('pre');
        calc.textContent = finding.calculation;
        card.append(calc);
      }

      if (finding.evidence_ids && auditResult.evidence) {
        finding.evidence_ids.forEach(id => {
          const ev = auditResult.evidence.find(e => e.id === id);
          if (!ev) return;
          const quote = document.createElement('blockquote');
          const cite = document.createElement('cite');
          cite.textContent = `${ev.document_id} / ${ev.location}`;
          const text = document.createElement('p');
          text.textContent = ev.text;
          quote.append(cite, text);
          card.append(quote);
        });
      }
      findingsContainer.append(card);
    });
  }

  const traceContainer = byId('trace');
  traceContainer.replaceChildren();
  if (auditResult.trace) {
    auditResult.trace.forEach((step, idx) => {
      const info = traceStepsInfo[step] || {
        title: step.replace(/_/g, ' '),
        description: 'Fase de validación completada durante la auditoría.'
      };
      const li = document.createElement('li');
      li.className = 'trace-step';

      const header = document.createElement('div');
      header.className = 'trace-step-header';

      const badge = document.createElement('span');
      badge.className = 'trace-badge';
      badge.textContent = `Paso 0${idx + 1}`;

      const title = document.createElement('strong');
      title.textContent = info.title;

      header.append(badge, title);

      const desc = document.createElement('p');
      desc.className = 'trace-step-desc';
      desc.textContent = info.description;

      const codeTag = document.createElement('span');
      codeTag.className = 'trace-code-tag';
      codeTag.textContent = `Referencia interna: ${step}`;

      li.append(header, desc, codeTag);
      traceContainer.append(li);
    });
  }

  byId('versions').textContent = `${auditResult.rule_version} · ${auditResult.prompt_version} · ${auditResult.mode} · ${auditResult.duration_ms} ms. Modelo: ${auditResult.model || 'simulado'}.`;
  byId('result').hidden = false;
  byId('result').scrollIntoView({behavior: 'smooth'});
}

// 3. Ejecución directa del caso de cabecera
byId('run').addEventListener('click', async () => {
  byId('run').disabled = true;
  document.querySelectorAll('[data-case]').forEach(b => (b.disabled = true));
  byId('result').hidden = true;
  byId('progress').textContent = 'Comprobando expediente y evidencia…';
  try {
    const response = await fetch(`/api/demo/${selectedCase}/audit`, {method: 'POST'});
    if (!response.ok) throw new Error('No fue posible ejecutar la auditoría. Intenta nuevamente.');
    const data = await response.json();
    renderAuditResult(data);
    byId('progress').textContent = `Auditoría de ${data.claim_id} completada con éxito.`;
  } catch (error) {
    byId('progress').textContent = error.message;
  } finally {
    byId('run').disabled = false;
    document.querySelectorAll('[data-case]').forEach(b => (b.disabled = false));
  }
});

// 4. Descarga del reporte JSON
byId('download').addEventListener('click', () => {
  if (!lastAuditResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastAuditResult, null, 2)], {type: 'application/json'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${lastAuditResult.claim_id}-audit.json`;
  a.click();
  URL.revokeObjectURL(url);
});

// ==========================================
// 5. GESTOR DOCUMENTAL INTERACTIVO
// ==========================================

// Refrescar tarjetas de documentos por rol
async function refreshClaimDocuments(claimId) {
  const roles = ['BILLING_DOCUMENT', 'INCIDENT_REPORT', 'WORKSHOP_REPORT', 'TARIFF'];
  try {
    const res = await fetch(`/api/claims/${claimId}/documents`);
    if (activeClaimId !== claimId) return;
    if (!res.ok) {
      roles.forEach(role => {
        const statusEl = byId(`status-${role}`);
        const fileInfoEl = byId(`fileinfo-${role}`);
        if (statusEl) {
          statusEl.textContent = 'Pendiente de archivo';
          statusEl.className = 'role-status badge-pending';
        }
        if (fileInfoEl) fileInfoEl.textContent = 'Sin documento cargado';
      });
      return;
    }
    const docs = await res.json();
    const classificationPanel = byId('wb-document-classifications');
    classificationPanel.replaceChildren();
    docs.filter(doc => doc.kind !== 'TARIFF').forEach(doc => {
      const label = document.createElement('label');
      label.textContent = `${doc.filename} · ${doc.active ? 'Activo' : 'Inactivo'} · Tipo (puedes corregirlo): `;
      const select = document.createElement('select');
      select.setAttribute('aria-label', `Tipo de ${doc.filename}`);
      Object.entries(roleNames).filter(([kind]) => kind !== 'TARIFF').forEach(([kind, name]) => {
        const option = document.createElement('option');
        option.value = kind; option.textContent = name; option.selected = kind === doc.kind;
        select.append(option);
      });
      select.addEventListener('change', async () => {
        const response = await fetch(`/api/claims/${claimId}/documents/${doc.id}`, {
          method: 'PATCH', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({kind: select.value})
        });
        if (!response.ok) { alert('No se pudo corregir el tipo documental.'); return; }
        currentSnapshot = null;
        byId('wb-confirm-audit-btn').disabled = true;
        byId('wb-extract-status').textContent = 'Tipo corregido. Extrae nuevamente para actualizar los datos.';
        await refreshClaimDocuments(claimId);
      });
      label.append(select); classificationPanel.append(label, document.createElement('br'));
    });
    roles.forEach(role => {
      const roleDocs = docs.filter(d => d.kind === role);
      const activeDoc = roleDocs.find(d => d.active);
      const statusEl = byId(`status-${role}`);
      const fileInfoEl = byId(`fileinfo-${role}`);

      if (activeDoc) {
        if (statusEl) {
          statusEl.textContent = 'Subido · Activo';
          statusEl.className = 'role-status badge-uploaded';
        }
        if (fileInfoEl) {
          const kb = (activeDoc.byte_count / 1024).toFixed(1);
          fileInfoEl.replaceChildren();
          const nameSpan = document.createElement('span');
          nameSpan.textContent = `${activeDoc.filename} (${kb} KB)`;
          const dlLink = document.createElement('a');
          dlLink.href = `/api/claims/${claimId}/documents/${activeDoc.id}`;
          dlLink.target = '_blank';
          dlLink.rel = 'noopener';
          dlLink.className = 'doc-dl-btn';
          dlLink.textContent = 'Descargar ↗';
          fileInfoEl.append(nameSpan, dlLink);
        }
      } else {
        if (statusEl) {
          if (role === 'TARIFF' && (claimId.endsWith('-D') || selectedCase === 'D')) {
            statusEl.textContent = 'Sin tarifario convenido (Caso D)';
            statusEl.className = 'role-status badge-pending';
            if (fileInfoEl) {
              fileInfoEl.textContent = 'Caso sin tarifario (diseñado para evaluar requerimiento de información)';
            }
          } else {
            statusEl.textContent = 'Pendiente de archivo';
            statusEl.className = 'role-status badge-pending';
            if (fileInfoEl) fileInfoEl.textContent = 'Sin documento cargado';
          }
        }
      }
    });
  } catch {
    // Modo desconectado / error silencioso
  }
}

// Renderizar snapshot de extracción
function renderSnapshot(snapshot) {
  currentSnapshot = snapshot;
  const hasOcr = (snapshot.evidence || []).some(e => e.location.includes(' · OCR'));
  byId('wb-ocr-review-label').hidden = !hasOcr;
  byId('wb-ocr-reviewed').checked = false;
  const updateConfirmation = () => {
    byId('wb-confirm-audit-btn').disabled = !(snapshot.items && snapshot.items.length)
      || (hasOcr && !byId('wb-ocr-reviewed').checked);
  };
  byId('wb-ocr-reviewed').onchange = updateConfirmation;
  updateConfirmation();
  byId('wb-billing-kind').value = snapshot.billing_kind || 'QUOTE';
  ['subtotal', 'taxes', 'total'].forEach(key => {
    byId(`wb-${key}`).value = snapshot[key] === null || snapshot[key] === undefined ? '' : snapshot[key];
  });
  byId('wb-review-notes').textContent = (snapshot.review_notes || []).join(' · ');
  const metaEl = byId('wb-snapshot-meta');
  if (metaEl) {
    const totalItems = snapshot.items ? snapshot.items.length : 0;
    const totalTariffs = snapshot.tariffs ? snapshot.tariffs.length : 0;
    metaEl.textContent = `${totalItems} ítems cotizados · ${totalTariffs} tarifas contractuales · Moneda: USD`;
  }

  // 1. Tabla de ítems
  const itemsTbody = byId('wb-items-table').querySelector('tbody');
  itemsTbody.replaceChildren();
  if (snapshot.items && snapshot.items.length) {
    snapshot.items.forEach(item => {
      const tr = document.createElement('tr');

      const tdId = document.createElement('td');
      tdId.textContent = item.id;

      const tdDesc = document.createElement('td');
      tdDesc.textContent = item.description;
      const codeSelect = document.createElement('select');
      codeSelect.setAttribute('aria-label', `Servicio de ${item.description}`);
      const unknown = document.createElement('option');
      unknown.value = ''; unknown.textContent = 'Servicio sin identificar'; codeSelect.append(unknown);
      [...new Set((snapshot.tariffs || []).map(t => t.service_code))].forEach(code => {
        const option = document.createElement('option');
        option.value = code; option.textContent = code; option.selected = code === item.service_code;
        codeSelect.append(option);
      });
      codeSelect.addEventListener('change', () => { item.service_code = codeSelect.value || null; });
      tdDesc.append(codeSelect);

      const tdQty = document.createElement('td');
      tdQty.textContent = `${item.quantity || 1} ${item.unit || 'UNIT'}`;

      const tdPrice = document.createElement('td');
      tdPrice.textContent = currency(item.unit_price);

      const tdTotal = document.createElement('td');
      tdTotal.textContent = currency(item.line_total);
      [[tdQty, 'quantity'], [tdPrice, 'unit_price'], [tdTotal, 'line_total']].forEach(([cell, key]) => {
        const input = document.createElement('input'); input.type = 'text'; input.inputMode = 'decimal';
        input.setAttribute('aria-label', `${key} de ${item.description}`);
        input.value = item[key] === null || item[key] === undefined ? '' : item[key];
        input.addEventListener('change', () => { item[key] = input.value.trim() || null; });
        cell.replaceChildren(input);
      });
      const unitSelect = document.createElement('select');
      unitSelect.setAttribute('aria-label', `Unidad de ${item.description}`);
      [['', 'Unidad pendiente'], ['HOUR', 'Horas'], ['UNIT', 'Unidades']].forEach(([value, name]) => {
        const option = document.createElement('option'); option.value = value; option.textContent = name;
        option.selected = value === (item.unit || ''); unitSelect.append(option);
      });
      unitSelect.addEventListener('change', () => { item.unit = unitSelect.value || null; });
      tdQty.append(unitSelect);

      const tdDamage = document.createElement('td');
      tdDamage.textContent = item.damage_code || 'No especificado';

      const tdEv = document.createElement('td');
      const ev = (snapshot.evidence || []).find(e => e.id === item.evidence_id);
      if (ev) {
        const tag = document.createElement('span');
        tag.className = 'ev-tag';
        tag.textContent = `${ev.document_id} · ${ev.location}`;
        const quote = document.createElement('span');
        quote.className = 'ev-quote';
        quote.textContent = `“${ev.text}”`;
        tdEv.append(tag, quote);
      } else {
        tdEv.textContent = item.evidence_id || 'Sin cita';
      }

      tr.append(tdId, tdDesc, tdQty, tdPrice, tdTotal, tdDamage, tdEv);
      itemsTbody.append(tr);
    });
  } else {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 7;
    td.textContent = 'No se extrajeron ítems de cotización en este expediente.';
    tr.append(td);
    itemsTbody.append(tr);
  }

  // 2. Tabla de tarifas
  const tariffsTbody = byId('wb-tariffs-table').querySelector('tbody');
  tariffsTbody.replaceChildren();
  if (snapshot.tariffs && snapshot.tariffs.length) {
    snapshot.tariffs.forEach(tf => {
      const tr = document.createElement('tr');

      const tdCode = document.createElement('td');
      tdCode.textContent = tf.service_code;

      const tdUnit = document.createElement('td');
      tdUnit.textContent = tf.unit;

      const tdRate = document.createElement('td');
      tdRate.textContent = currency(tf.allowed_rate);

      const tdEv = document.createElement('td');
      const ev = (snapshot.evidence || []).find(e => e.id === tf.evidence_id);
      if (ev) {
        const tag = document.createElement('span');
        tag.className = 'ev-tag';
        tag.textContent = `${ev.document_id} · ${ev.location}`;
        const quote = document.createElement('span');
        quote.className = 'ev-quote';
        quote.textContent = `“${ev.text}”`;
        tdEv.append(tag, quote);
      } else {
        tdEv.textContent = tf.evidence_id || 'Sin cita';
      }

      tr.append(tdCode, tdUnit, tdRate, tdEv);
      tariffsTbody.append(tr);
    });
  } else {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 4;
    td.textContent = 'No hay tarifas de convenio registradas para este expediente.';
    tr.append(td);
    tariffsTbody.append(tr);
  }

  // 3. Daños detectados
  const repList = byId('wb-reported-damages');
  repList.replaceChildren();
  if (snapshot.reported_damage_codes && snapshot.reported_damage_codes.length) {
    snapshot.reported_damage_codes.forEach(code => {
      const li = document.createElement('li');
      li.textContent = code;
      repList.append(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'Ninguno declarado';
    repList.append(li);
  }

  const inspList = byId('wb-inspected-damages');
  inspList.replaceChildren();
  if (snapshot.inspected_damage_codes && snapshot.inspected_damage_codes.length) {
    snapshot.inspected_damage_codes.forEach(code => {
      const li = document.createElement('li');
      li.textContent = code;
      inspList.append(li);
    });
  }
}

// Cargar preset sintético en el banco de trabajo
async function loadPresetIntoWorkbench(caseId) {
  selectedCase = caseId;
  const claimInput = byId('claim-id-input');
  activeClaimId = `CLM-2026-DEMO-${caseId}`;
  const presetClaimId = activeClaimId;
  if (claimInput) claimInput.value = activeClaimId;

  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.setAttribute('aria-pressed', String(btn.dataset.preset === caseId));
  });

  const extractStatus = byId('wb-extract-status');
  if (extractStatus) {
    extractStatus.textContent = `Cargando caso de prueba ${caseId}…`;
    extractStatus.style.color = '#14684f';
  }

  try {
    const res = await fetch(`/api/claims/${activeClaimId}/preset/${caseId}`, {method: 'POST'});
    if (activeClaimId !== presetClaimId) return;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al cargar caso predefinido');
    }
    const snapshot = await res.json();
    await refreshClaimDocuments(activeClaimId);
    if (activeClaimId !== presetClaimId) return;
    renderSnapshot(snapshot);
    if (extractStatus) {
      extractStatus.textContent = `✓ Caso ${caseId} cargado con documentos oficiales (PDF / XLSX), evidencias y tarifas.`;
    }
  } catch (err) {
    if (extractStatus) {
      extractStatus.textContent = `⚠ ${err.message}`;
      extractStatus.style.color = '#b26418';
    }
  }
}

// Botones de presets en el banco de trabajo
document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    loadPresetIntoWorkbench(btn.dataset.preset);
  });
});

// Botón para generar ID nuevo
const btnNewClaim = byId('btn-new-claim');
if (btnNewClaim) {
  btnNewClaim.addEventListener('click', async () => {
    const randomSuffix = Math.random().toString(36).substring(2, 7).toUpperCase();
    activeClaimId = `CLM-2026-${randomSuffix}`;
    selectedCase = null;
    renderSnapshot({items: [], tariffs: [], reported_damage_codes: [], inspected_damage_codes: []});
    currentSnapshot = null;
    lastAuditResult = null;
    document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed', 'false'));
    byId('claim-id-input').value = activeClaimId;
    byId('result').hidden = true;
    byId('wb-extraction-viewer').hidden = false;
    byId('wb-upload-panel').hidden = false;
    byId('toggle-upload-btn').textContent = '✕ Ocultar formulario';
    byId('toggle-data-btn').textContent = 'Ocultar datos extraídos ↑';
    byId('run').hidden = true;
    byId('input-link').hidden = true;
    byId('progress').textContent = '1. Sube cotización, siniestro e inspección. 2. Extrae con Gemini. 3. Revisa, corrige y audita. El tarifario ya está configurado.';
    byId('wb-upload-feedback').textContent = '';
    byId('wb-extract-status').textContent = `Nuevo expediente ${activeClaimId} iniciado. Sube tus documentos.`;
    const response = await fetch('/api/claims', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({claim_id: activeClaimId})
    });
    if (!response.ok) { byId('progress').textContent = 'No se pudo crear el expediente. Reintenta.'; return; }
    await refreshClaimDocuments(activeClaimId);
    byId('wb-doc-file').focus();
  });
}

// Actualizar claim ID si se edita manualmente
const claimInputEl = byId('claim-id-input');
if (claimInputEl) {
  claimInputEl.addEventListener('change', () => {
    const val = claimInputEl.value.trim();
    if (val) {
      activeClaimId = val;
      selectedCase = null;
      renderSnapshot({items: [], tariffs: []});
      currentSnapshot = null;
      lastAuditResult = null;
      byId('result').hidden = true;
      byId('run').hidden = true;
      byId('input-link').hidden = true;
      byId('wb-extraction-viewer').hidden = false;
      byId('wb-upload-panel').hidden = false;
      byId('progress').textContent = 'Expediente seleccionado. Revisa sus documentos y extrae los datos antes de auditar.';
      refreshClaimDocuments(activeClaimId);
    }
  });
}

// Subida interactiva de documentos PDF/XLSX
const wbUploadForm = byId('wb-upload-form');
if (wbUploadForm) {
  wbUploadForm.addEventListener('submit', async e => {
    e.preventDefault();
    const fileInput = byId('wb-doc-file');
    const roleSelect = byId('wb-doc-role');
    const feedback = byId('wb-upload-feedback');
    const submitBtn = byId('wb-upload-btn');

    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    const kind = roleSelect.value;

    feedback.textContent = kind ? `Subiendo ${file.name} como ${roleNames[kind]}…` : `Gemini está clasificando ${file.name}…`;
    feedback.style.color = '#14684f';
    if (submitBtn) submitBtn.disabled = true;

    try {
      // Asegurar existencia del expediente
      await fetch('/api/claims', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({claim_id: activeClaimId})
      }).catch(() => {});

      const formData = new FormData();
      formData.append('file', file);
      if (kind) formData.append('kind', kind);

      const res = await fetch(`/api/claims/${activeClaimId}/documents`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Error al subir el archivo');
      }

      const doc = await res.json();
      feedback.textContent = `✓ ${doc.filename}: ${roleNames[doc.kind]}. Puedes corregir el tipo en la lista de documentos.`;
      feedback.style.color = '#12664f';
      fileInput.value = '';
      await refreshClaimDocuments(activeClaimId);
    } catch (err) {
      feedback.textContent = `⚠ ${err.message}`;
      feedback.style.color = '#b26418';
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

// Botón de extracción documental
const wbExtractBtn = byId('wb-extract-btn');
if (wbExtractBtn) {
  wbExtractBtn.addEventListener('click', async () => {
    const statusEl = byId('wb-extract-status');
    statusEl.textContent = 'Gemini está extrayendo los datos y verificando las citas por página…';
    statusEl.style.color = '#14684f';
    wbExtractBtn.disabled = true;
    currentSnapshot = null;
    wbConfirmAuditBtn.disabled = true;

    try {
      const res = await fetch(`/api/claims/${activeClaimId}/extract`, {method: 'POST'});
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'No fue posible extraer datos de los documentos activos');
      }
      const snapshot = await res.json();
      renderSnapshot(snapshot);
      statusEl.textContent = `✓ Extracción completada: ${(snapshot.items || []).length} ítems y ${(snapshot.tariffs || []).length} tarifas detectadas.`;
    } catch (err) {
      statusEl.textContent = `⚠ ${err.message}`;
      statusEl.style.color = '#b26418';
    } finally {
      wbExtractBtn.disabled = false;
    }
  });
}

// Botón de confirmación de normalización y auditoría en vivo
const wbConfirmAuditBtn = byId('wb-confirm-audit-btn');
if (wbConfirmAuditBtn) {
  wbConfirmAuditBtn.addEventListener('click', async () => {
    if (!currentSnapshot) return;
    wbConfirmAuditBtn.disabled = true;
    wbConfirmAuditBtn.textContent = 'Consolidando normalización y auditando…';

    try {
      // 1. Mapear ítems normalizados a formato Item requerido por el contrato
      const itemsPayload = (currentSnapshot.items || []).map(it => ({
        id: it.id,
        description: it.description,
        service_code: it.service_code || it.id,
        damage_code: it.damage_code || 'UNKNOWN',
        unit: it.unit,
        quantity: it.quantity,
        unit_price: it.unit_price,
        line_total: it.line_total,
        evidence_id: it.evidence_id
      }));

      const tariffsPayload = (currentSnapshot.tariffs || []).map(tf => ({
        service_code: tf.service_code,
        unit: tf.unit,
        allowed_rate: tf.allowed_rate,
        evidence_id: tf.evidence_id
      }));

      // 2. Enviar confirmación determinista
      const normRes = await fetch(`/api/claims/${activeClaimId}/normalized`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-OCR-Reviewed': byId('wb-ocr-reviewed').checked ? 'true' : 'false'
        },
        body: JSON.stringify({
          billing_kind: byId('wb-billing-kind').value,
          reported_damage_codes: currentSnapshot.reported_damage_codes || [],
          inspected_damage_codes: currentSnapshot.inspected_damage_codes || [],
          items: itemsPayload,
          tariffs: tariffsPayload,
          subtotal: byId('wb-subtotal').value.trim() || null,
          taxes: byId('wb-taxes').value.trim() || null,
          total: byId('wb-total').value.trim() || null
        })
      });

      if (!normRes.ok) {
        const err = await normRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Error al confirmar los datos normalizados');
      }

      // 3. Ejecutar auditoría agéntica en vivo sobre el expediente
      const auditRes = await fetch(`/api/claims/${activeClaimId}/audits`, {method: 'POST'});
      if (!auditRes.ok) {
        const err = await auditRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Error al ejecutar la auditoría');
      }

      const auditData = await auditRes.json();
      renderAuditResult(auditData);
    } catch (err) {
      alert(`Error en la auditoría: ${err.message}`);
    } finally {
      wbConfirmAuditBtn.disabled = false;
      wbConfirmAuditBtn.textContent = 'Confirmar normalización y auditar expediente en vivo →';
    }
  });
}

// Inicializar vista al cargar la página precargando el caso de referencia B sin alterar scroll
window.addEventListener('DOMContentLoaded', () => {
  loadPresetIntoWorkbench('B');
  window.scrollTo(0, 0);
});

byId('standard-tariff-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(); form.append('file', byId('standard-tariff-file').files[0]);
  const response = await fetch('/api/claims/settings/standard-tariff', {method:'PUT', body:form});
  const result = await response.json();
  byId('standard-tariff-status').textContent = response.ok ? result.message : (result.detail || 'No se pudo guardar el tarifario.');
});
