let selected = 'B';
let result = null;
const byId = id => document.getElementById(id);
const currency = value => value === null ? 'No disponible' : new Intl.NumberFormat('es-PA', {style: 'currency', currency: 'USD'}).format(Number(value));
const labels = {CANDIDATE_FOR_APPROVAL: 'Candidato para aprobación · requiere decisión humana', REVIEW_REQUIRED: 'Revisión requerida', INFORMATION_REQUIRED: 'Información requerida'};

document.querySelectorAll('[data-case]').forEach(button => button.addEventListener('click', () => {
  selected = button.dataset.case;
  document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
  byId('run').textContent = `Auditar expediente ${selected} →`;
  byId('input-link').href = `/api/demo/${selected}`;
  byId('result').hidden = true;
  byId('progress').textContent = '';
}));

byId('run').addEventListener('click', async () => {
  byId('run').disabled = true;
  document.querySelectorAll('[data-case]').forEach(b => b.disabled = true);
  byId('result').hidden = true;
  byId('progress').textContent = 'Comprobando expediente y evidencia…';
  try {
    const response = await fetch(`/api/demo/${selected}/audit`, {method: 'POST'});
    if (!response.ok) throw new Error('No fue posible ejecutar la auditoría. Intenta nuevamente.');
    result = await response.json();
    byId('status').textContent = labels[result.status];
    byId('status').dataset.status = result.status;
    byId('billed').textContent = currency(result.billed_amount);
    byId('difference').textContent = result.trace.includes('tariff_check') ? currency(result.flagged_difference) : 'No evaluado';
    byId('reference').textContent = currency(result.reference_subtotal);
    byId('findings').replaceChildren();
    if (!result.findings.length) {
      const p = document.createElement('p'); p.textContent = 'No se detectaron discrepancias en las comprobaciones ejecutadas.'; byId('findings').append(p);
    }
    result.findings.forEach(finding => {
      const card = document.createElement('details');
      const summary = document.createElement('summary'); summary.textContent = `${finding.code}${finding.item_id ? ` · ${finding.item_id}` : ''}`;
      const p = document.createElement('p'); p.textContent = finding.description;
      card.append(summary, p);
      if (finding.calculation) { const calc = document.createElement('pre'); calc.textContent = finding.calculation; card.append(calc); }
      finding.evidence_ids.forEach(id => {
        const evidence = result.evidence.find(e => e.id === id);
        if (!evidence) return;
        const quote = document.createElement('blockquote');
        const cite = document.createElement('cite'); cite.textContent = `${evidence.document_id} / ${evidence.location}`;
        const text = document.createElement('p'); text.textContent = evidence.text;
        quote.append(cite, text); card.append(quote);
      });
      byId('findings').append(card);
    });
    byId('trace').replaceChildren();
    result.trace.forEach(step => { const li = document.createElement('li'); li.textContent = step; byId('trace').append(li); });
    byId('versions').textContent = `${result.rule_version} · ${result.prompt_version} · ${result.mode} · ${result.duration_ms} ms. Modelo: ${result.model || 'simulado'}. Tokens: ${result.input_tokens} entrada / ${result.output_tokens} salida.`;
    byId('result').hidden = false;
    byId('progress').textContent = `Auditoría de ${result.claim_id} completada.`;
  } catch (error) { byId('progress').textContent = error.message; }
  finally {
    byId('run').disabled = false;
    document.querySelectorAll('[data-case]').forEach(b => b.disabled = false);
  }
});

byId('download').addEventListener('click', () => {
  if (!result) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = `${result.claim_id}-audit.json`; a.click(); URL.revokeObjectURL(url);
});
