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
  BILLING_DOCUMENT: 'Factura de cobro',
  INCIDENT_REPORT: 'Declaración de siniestro',
  WORKSHOP_REPORT: 'Informe pericial',
  TARIFF: 'Tarifario de convenio'
};

// 1. Selector rápido de casos superiores (A, B, C, D)
document.querySelectorAll('[data-case]').forEach(button => {
  button.addEventListener('click', () => {
    selectedCase = button.dataset.case;
    document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    byId('run').textContent = `Auditar expediente ${selectedCase} inmediatamente →`;
    byId('load-to-wb').textContent = `Inspeccionar caso ${selectedCase} en Banco de Trabajo T06 ↓`;
    byId('input-link').href = `/api/demo/${selectedCase}`;
    byId('result').hidden = true;
    byId('progress').textContent = '';
  });
});

// Cargar caso rápido directamente en el banco de trabajo T06
const loadToWbBtn = byId('load-to-wb');
if (loadToWbBtn) {
  loadToWbBtn.addEventListener('click', () => {
    loadPresetIntoWorkbench(selectedCase);
    byId('workbench').scrollIntoView({behavior: 'smooth'});
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
      const summary = document.createElement('summary');
      summary.textContent = `${finding.code}${finding.item_id ? ` · ${finding.item_id}` : ''}`;
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
    auditResult.trace.forEach(step => {
      const li = document.createElement('li');
      li.textContent = step;
      traceContainer.append(li);
    });
  }

  byId('versions').textContent = `${auditResult.rule_version} · ${auditResult.prompt_version} · ${auditResult.mode} · ${auditResult.duration_ms} ms. Modelo: ${auditResult.model || 'simulado'}. Tokens: ${auditResult.input_tokens || 0} entrada / ${auditResult.output_tokens || 0} salida.`;
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
// 5. BANCO DE TRABAJO T06 (WORKBENCH)
// ==========================================

// Refrescar tarjetas de documentos por rol
async function refreshClaimDocuments(claimId) {
  const roles = ['BILLING_DOCUMENT', 'INCIDENT_REPORT', 'WORKSHOP_REPORT', 'TARIFF'];
  try {
    const res = await fetch(`/api/claims/${claimId}/documents`);
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
    roles.forEach(role => {
      const roleDocs = docs.filter(d => d.kind === role);
      const activeDoc = roleDocs.find(d => d.active) || roleDocs[0];
      const statusEl = byId(`status-${role}`);
      const fileInfoEl = byId(`fileinfo-${role}`);

      if (activeDoc) {
        if (statusEl) {
          statusEl.textContent = 'Subido · Activo';
          statusEl.className = 'role-status badge-uploaded';
        }
        if (fileInfoEl) {
          const kb = (activeDoc.byte_count / 1024).toFixed(1);
          fileInfoEl.textContent = `${activeDoc.filename} (${kb} KB, v${activeDoc.version})`;
          fileInfoEl.title = activeDoc.filename;
        }
      } else {
        if (statusEl) {
          statusEl.textContent = 'Pendiente de archivo';
          statusEl.className = 'role-status badge-pending';
        }
        if (fileInfoEl) fileInfoEl.textContent = 'Sin documento cargado';
      }
    });
  } catch {
    // Modo desconectado / error silencioso
  }
}

// Renderizar snapshot de extracción
function renderSnapshot(snapshot) {
  currentSnapshot = snapshot;
  const metaEl = byId('wb-snapshot-meta');
  if (metaEl) {
    const totalItems = snapshot.items ? snapshot.items.length : 0;
    const totalTariffs = snapshot.tariffs ? snapshot.tariffs.length : 0;
    metaEl.textContent = `${totalItems} ítems facturados · ${totalTariffs} tarifas contractuales · Moneda: USD`;
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

      const tdQty = document.createElement('td');
      tdQty.textContent = `${item.quantity || 1} ${item.unit || 'UNIT'}`;

      const tdPrice = document.createElement('td');
      tdPrice.textContent = currency(item.unit_price);

      const tdTotal = document.createElement('td');
      tdTotal.textContent = currency(item.line_total);

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
    td.textContent = 'No se extrajeron ítems de facturación en este expediente.';
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
  } else {
    const li = document.createElement('li');
    li.textContent = 'Ninguno peritado';
    inspList.append(li);
  }

  byId('wb-extraction-viewer').hidden = false;
  byId('wb-extraction-viewer').scrollIntoView({behavior: 'smooth'});
}

// Cargar preset sintético en el banco de trabajo
async function loadPresetIntoWorkbench(caseId) {
  const claimInput = byId('claim-id-input');
  activeClaimId = `CLM-2026-DEMO-${caseId}`;
  if (claimInput) claimInput.value = activeClaimId;

  const extractStatus = byId('wb-extract-status');
  if (extractStatus) {
    extractStatus.textContent = `Cargando caso de prueba ${caseId}…`;
    extractStatus.style.color = '#14684f';
  }

  try {
    const res = await fetch(`/api/claims/${activeClaimId}/preset/${caseId}`, {method: 'POST'});
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al cargar caso predefinido');
    }
    const snapshot = await res.json();
    await refreshClaimDocuments(activeClaimId);
    renderSnapshot(snapshot);
    if (extractStatus) {
      extractStatus.textContent = `✓ Caso ${caseId} cargado con documentos, evidencias y tarifas.`;
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
  btnNewClaim.addEventListener('click', () => {
    const randomSuffix = Math.random().toString(36).substring(2, 7).toUpperCase();
    activeClaimId = `CLM-2026-${randomSuffix}`;
    byId('claim-id-input').value = activeClaimId;
    byId('wb-extraction-viewer').hidden = true;
    byId('wb-upload-feedback').textContent = '';
    byId('wb-extract-status').textContent = `Nuevo expediente ${activeClaimId} iniciado. Sube tus documentos.`;
    refreshClaimDocuments(activeClaimId);
  });
}

// Actualizar claim ID si se edita manualmente
const claimInputEl = byId('claim-id-input');
if (claimInputEl) {
  claimInputEl.addEventListener('change', () => {
    const val = claimInputEl.value.trim();
    if (val) {
      activeClaimId = val;
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

    feedback.textContent = `Subiendo ${file.name} como ${roleNames[kind]}…`;
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
      formData.append('kind', kind);

      const res = await fetch(`/api/claims/${activeClaimId}/documents`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Error al subir el archivo');
      }

      const doc = await res.json();
      feedback.textContent = `✓ Archivo "${doc.filename}" almacenado correctamente (v${doc.version}).`;
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
    statusEl.textContent = 'Extrayendo texto página por página y analizando tarifas…';
    statusEl.style.color = '#14684f';
    wbExtractBtn.disabled = true;

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
        unit: it.unit || 'UNIT',
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
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          billing_kind: currentSnapshot.billing_kind || 'INVOICE',
          reported_damage_codes: currentSnapshot.reported_damage_codes || [],
          inspected_damage_codes: currentSnapshot.inspected_damage_codes || [],
          items: itemsPayload,
          tariffs: tariffsPayload,
          subtotal: currentSnapshot.subtotal,
          taxes: currentSnapshot.taxes || '0.00',
          total: currentSnapshot.total
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

// Inicializar vista al cargar la página
window.addEventListener('DOMContentLoaded', () => {
  refreshClaimDocuments(activeClaimId);
});
