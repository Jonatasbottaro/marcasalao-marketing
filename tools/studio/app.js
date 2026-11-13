'use strict';

let draft = null;
let catalog = [];
let pollTimer = null;

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c != null) node.append(c);
  return node;
};

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3500);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ ok: false, error: 'resposta ilegivel' }));
  if (!res.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function emptyDraft() {
  return {
    schemaVersion: 1, id: 'novo-pedido', project: '', title: 'Novo video', locale: 'pt-BR',
    profiles: [], visualStyle: { schemaVersion: 1, id: 'estilo-padrao', title: { textColor: '#FFFFFF', outlineColor: '#000000', fontSize: 42, marginTop: 160, marginHorizontal: 60 } },
    media: [], scenes: [],
  };
}

// ---- projetos e perfis ----
async function loadProjects() {
  const data = await api('/api/projects');
  const sel = $('#project-select');
  sel.innerHTML = '';
  sel.append(el('option', { value: '', text: '— selecione —' }));
  for (const p of data.projects) sel.append(el('option', { value: p.path, text: `${p.id} — ${p.name || ''}` }));
  if (draft && draft.project) sel.value = draft.project;
}

async function loadProfiles() {
  const project = $('#project-select').value;
  if (!project) { toast('Selecione um projeto.'); return; }
  draft.project = project;
  const data = await api('/api/profiles?project=' + encodeURIComponent(project));
  catalog = data.listing.profiles;
  renderProfiles();
  renderExportProfileOptions();
  toast(`${catalog.length} perfis carregados.`);
}

function renderProfiles() {
  const tbody = $('#profiles-table tbody');
  tbody.innerHTML = '';
  for (const p of catalog) {
    const checked = draft.profiles.includes(p.id);
    const usable = p.availability === 'allowed' && p.localExport;
    const cb = el('input', { type: 'checkbox', onchange: (e) => {
      if (e.target.checked) { if (!draft.profiles.includes(p.id)) draft.profiles.push(p.id); }
      else draft.profiles = draft.profiles.filter((x) => x !== p.id);
      renderExportProfileOptions();
    } });
    cb.checked = checked;
    cb.disabled = !usable;
    const avail = p.availability === 'allowed' ? el('span', { class: 'badge ok', text: 'permitido' })
      : p.availability === 'blocked' ? el('span', { class: 'badge err', text: p.blockCode || 'bloqueado' })
      : el('span', { class: 'badge muted', text: 'não consultado' });
    const local = p.localExport ? el('span', { class: 'badge ok', text: '9:16@30 sim' }) : el('span', { class: 'badge muted', text: 'fora do recorte' });
    tbody.append(el('tr', {}, [
      el('td', {}, cb), el('td', { text: p.id }), el('td', { text: `${p.network}/${p.publication}` }),
      el('td', { text: `${p.width}×${p.height} (${p.aspectRatio})` }), el('td', { text: p.fps == null ? '—' : String(p.fps) }),
      el('td', {}, avail), el('td', {}, local),
    ]));
  }
}

function renderExportProfileOptions() {
  const sel = $('#export-profile');
  const current = sel.value;
  sel.innerHTML = '';
  sel.append(el('option', { value: '', text: 'Todos os perfis do rascunho' }));
  for (const id of draft.profiles) sel.append(el('option', { value: id, text: id }));
  sel.value = current;
}

// ---- exemplos e rascunho ----
async function loadExamples() {
  const data = await api('/api/examples');
  const sel = $('#example-select');
  sel.innerHTML = '';
  for (const ex of data.examples) sel.append(el('option', { value: ex.path, text: ex.name }));
  sel._examples = data.examples;
}

function loadExample() {
  const sel = $('#example-select');
  const ex = (sel._examples || []).find((e) => e.path === sel.value);
  if (!ex) { toast('Selecione um exemplo.'); return; }
  draft = JSON.parse(JSON.stringify(ex.request));
  $('#draft-path').value = '.workspace/tmp/video-studio/drafts/' + draft.id + '.json';
  $('#output-dir').value = '.workspace/archives/video-studio/' + draft.id;
  $('#delivery-dir').value = '.workspace/archives/video-studio/' + draft.id;
  $('#project-select').value = draft.project;
  renderAll();
  loadProfiles();
  toast('Exemplo carregado: ' + draft.id);
}

async function saveDraft() {
  syncDraftFields();
  const path = $('#draft-path').value.trim();
  if (!path) { toast('Informe o caminho do rascunho.'); return; }
  const data = await post('/api/draft/save', { path, request: draft });
  toast('Rascunho salvo: ' + data.path);
}

async function openDraft() {
  const path = $('#draft-path').value.trim();
  if (!path) { toast('Informe o caminho do rascunho.'); return; }
  const data = await api('/api/draft/load?path=' + encodeURIComponent(path));
  draft = data.request;
  $('#project-select').value = draft.project || '';
  renderAll();
  if (draft.project) loadProfiles();
  toast('Rascunho reaberto.');
}

// ---- campos do rascunho ----
function syncDraftFields() {
  if (!draft) return;
  draft.id = $('#req-id').value.trim() || draft.id;
  draft.title = $('#req-title').value;
  draft.locale = $('#req-locale').value.trim() || 'pt-BR';
  draft.visualStyle = {
    schemaVersion: 1, id: $('#style-id').value.trim() || 'estilo-padrao',
    title: {
      textColor: $('#style-text').value.trim() || '#FFFFFF', outlineColor: $('#style-outline').value.trim() || '#000000',
      fontSize: Number($('#style-font').value) || 42, marginTop: Number($('#style-top').value) || 0,
      marginHorizontal: Number($('#style-horiz').value) || 0,
    },
  };
}

function renderDraftFields() {
  $('#req-id').value = draft.id || '';
  $('#req-title').value = draft.title || '';
  $('#req-locale').value = draft.locale || 'pt-BR';
  const vs = draft.visualStyle || { id: '', title: {} };
  $('#style-id').value = vs.id || '';
  $('#style-text').value = vs.title.textColor || '#FFFFFF';
  $('#style-outline').value = vs.title.outlineColor || '#000000';
  $('#style-font').value = vs.title.fontSize ?? 42;
  $('#style-top').value = vs.title.marginTop ?? 160;
  $('#style-horiz').value = vs.title.marginHorizontal ?? 60;
}

// ---- midias ----
function renderMedia() {
  const tbody = $('#media-table tbody');
  tbody.innerHTML = '';
  draft.media.forEach((m, i) => {
    const origin = el('input', { type: 'text', value: m.origin || '', oninput: (e) => { m.origin = e.target.value; } });
    const license = el('input', { type: 'text', value: m.license || 'pending', oninput: (e) => { m.license = e.target.value; } });
    tbody.append(el('tr', {}, [
      el('td', { text: m.id }), el('td', { text: m.type }), el('td', { text: m.path }),
      el('td', {}, origin), el('td', {}, license),
      el('td', {}, el('button', { class: 'secondary', text: 'Remover', onclick: () => { draft.media.splice(i, 1); renderMedia(); renderScenes(); } })),
    ]));
  });
}

async function scanMedia() {
  const folder = $('#media-folder').value.trim();
  if (!folder) { toast('Informe a pasta de trabalho.'); return; }
  const data = await post('/api/media/scan', { folder });
  let added = 0;
  for (const f of data.media) {
    if (draft.media.some((m) => m.path === f.path)) continue;
    const id = f.name.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'media';
    let unique = id; let n = 2;
    while (draft.media.some((m) => m.id === unique)) unique = `${id}-${n++}`;
    draft.media.push({ id: unique, path: f.path, type: f.type, origin: 'synthetic', license: 'pending' });
    added++;
  }
  renderMedia(); renderScenes();
  toast(`${added} mídia(s) cadastrada(s).`);
}

async function generateMedia() {
  syncDraftFields();
  if (!draft.media.length) { toast('Cadastre mídias no rascunho primeiro.'); return; }
  toast('Gerando mídia fictícia…');
  const data = await post('/api/media/generate', { request: draft });
  toast(`${data.written.length} arquivo(s) gerado(s).`);
}

// ---- cenas ----
const NARRATIVE = ['hook', 'context', 'problem', 'demonstration', 'explanation', 'proof', 'transition', 'cta', 'closing'];
const MOTION = ['none', 'slow-zoom'];

function renderScenes() {
  const list = $('#scenes-list');
  list.innerHTML = '';
  draft.scenes.forEach((s, i) => {
    const mediaSel = el('select', { onchange: (e) => { s.mediaId = e.target.value; } });
    mediaSel.append(el('option', { value: '', text: '— mídia —' }));
    for (const m of draft.media) mediaSel.append(el('option', { value: m.id, text: `${m.id} (${m.type})` }));
    mediaSel.value = s.mediaId || '';
    const nf = el('select', { onchange: (e) => { s.narrativeFunction = e.target.value; } });
    for (const v of NARRATIVE) nf.append(el('option', { value: v, text: v }));
    nf.value = s.narrativeFunction || 'demonstration';
    const mi = el('select', { onchange: (e) => { s.motionIntent = e.target.value; } });
    for (const v of MOTION) mi.append(el('option', { value: v, text: v }));
    mi.value = s.motionIntent || 'none';
    const card = el('div', { class: 'scene' }, [
      el('div', { class: 'row' }, [
        el('label', { text: `Cena ${i + 1} — id` }, el('input', { type: 'text', value: s.id, oninput: (e) => { s.id = e.target.value; } })),
        el('label', { text: 'Duração (ms)' }, el('input', { type: 'number', min: '1', value: s.durationMs, oninput: (e) => { s.durationMs = Number(e.target.value); } })),
        el('label', { text: 'Mídia' }, mediaSel),
        el('label', { text: 'Função' }, nf),
        el('label', { text: 'Movimento' }, mi),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Legenda (queimada)' }, el('input', { type: 'text', value: s.caption || '', oninput: (e) => { s.caption = e.target.value; } })),
        el('label', { text: 'Título sobreposto' }, el('input', { type: 'text', value: s.title || '', oninput: (e) => { s.title = e.target.value || undefined; } })),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Narração (TXT separado)' }, el('input', { type: 'text', value: s.narration || '', oninput: (e) => { s.narration = e.target.value; } })),
      ]),
      el('div', { class: 'row' }, [
        el('button', { class: 'secondary', text: '↑', onclick: () => { if (i > 0) { [draft.scenes[i - 1], draft.scenes[i]] = [draft.scenes[i], draft.scenes[i - 1]]; renderScenes(); } } }),
        el('button', { class: 'secondary', text: '↓', onclick: () => { if (i < draft.scenes.length - 1) { [draft.scenes[i + 1], draft.scenes[i]] = [draft.scenes[i], draft.scenes[i + 1]]; renderScenes(); } } }),
        el('button', { class: 'secondary', text: 'Remover', onclick: () => { draft.scenes.splice(i, 1); renderScenes(); } }),
      ]),
    ]);
    list.append(card);
  });
}

function addScene() {
  const n = draft.scenes.length + 1;
  draft.scenes.push({ id: `cena-${n}`, durationMs: 4000, mediaId: draft.media[0]?.id || '', caption: '', narration: '', narrativeFunction: 'demonstration', motionIntent: 'none' });
  renderScenes();
}

// ---- previa ----
async function preview() {
  syncDraftFields();
  const out = $('#preview-output');
  out.innerHTML = '<p class="muted">Calculando prévia…</p>';
  try {
    const data = await post('/api/preview', { request: draft });
    const r = data.result;
    out.innerHTML = '';
    if (r.status !== 'preview') { out.append(el('pre', { text: JSON.stringify(r, null, 2) })); return; }
    out.append(el('p', { text: `Pedido ${r.requestId} — ${r.profiles.length} perfil(is). Mídias: ${r.media.map((m) => m.id).join(', ') || '—'}` }));
    for (const p of r.profiles) {
      if (p.status !== 'compiled') {
        out.append(el('div', { class: 'profile-card' }, [
          el('strong', { text: p.profileId + ' ' }), el('span', { class: 'badge err', text: 'FALHOU: ' + (p.failureCode || '') }),
          el('pre', { text: (p.errors || []).map((e) => `${e.code} ${e.path}: ${e.message}`).join('\n') }),
        ]));
        continue;
      }
      const rows = p.beats.map((b) => el('tr', {}, [
        el('td', { text: b.beatId }), el('td', { text: `${b.startMs}→${b.endMs} ms` }), el('td', { text: `${b.durationMs} ms` }),
        el('td', { text: b.mediaId }), el('td', { text: b.title || '—' }),
      ]));
      const card = el('div', { class: 'profile-card' }, [
        el('strong', { text: p.profileId + ' ' }),
        el('span', { class: 'badge ok', text: `${p.geometry.width}×${p.geometry.height} @ ${p.fps}fps` }),
        el('span', { class: 'badge muted', text: `total ${p.durationSeconds}s` }),
        el('table', {}, [el('thead', {}, el('tr', {}, [el('th', { text: 'Beat' }), el('th', { text: 'Intervalo' }), el('th', { text: 'Duração' }), el('th', { text: 'Mídia' }), el('th', { text: 'Título' })])), el('tbody', {}, rows)]),
      ]);
      if (p.warnings && p.warnings.length) card.append(el('p', { class: 'timeline', text: 'Avisos: ' + p.warnings.map((w) => w.code).join(', ') }));
      out.append(card);
    }
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

// ---- exportacao ----
async function startExport(profileOverride) {
  syncDraftFields();
  const outputDir = $('#output-dir').value.trim();
  if (!outputDir) { toast('Informe a pasta de entrega.'); return; }
  const profile = profileOverride !== undefined ? profileOverride : $('#export-profile').value;
  const status = $('#export-status');
  status.innerHTML = '<p class="muted">Exportação iniciada…</p>';
  try {
    const data = await post('/api/export', { request: draft, outputDir, profile: profile || undefined });
    pollExport(data.jobId, outputDir);
  } catch (err) { status.innerHTML = ''; status.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function pollExport(jobId, outputDir) {
  if (pollTimer) clearTimeout(pollTimer);
  const tick = async () => {
    const data = await api('/api/export/status?job=' + jobId);
    const status = $('#export-status');
    if (data.status === 'running') {
      status.innerHTML = '<p class="muted">Exportando… (render em segundo plano)</p>';
      pollTimer = setTimeout(tick, 1500);
      return;
    }
    renderExportResult(data, outputDir);
  };
  tick();
}

function renderExportResult(data, outputDir) {
  const status = $('#export-status');
  status.innerHTML = '';
  const r = data.result || {};
  status.append(el('p', {}, [el('span', { class: data.status === 'completed' ? 'badge ok' : 'badge err', text: data.status })]));
  for (const p of (r.profiles || [])) {
    if (p.status === 'completed') {
      status.append(el('div', { text: `✓ ${p.profileId}: concluído (${p.deliveryManifest || ''})` }));
    } else {
      status.append(el('div', {}, [el('span', { class: 'badge err', text: `✗ ${p.profileId}: ${p.failureCode || p.error || 'falhou'}` })]));
    }
  }
  $('#delivery-dir').value = outputDir;
  loadDelivery();
}

// ---- entrega ----
async function loadDelivery() {
  const dir = $('#delivery-dir').value.trim();
  if (!dir) { toast('Informe a pasta de entrega.'); return; }
  const out = $('#delivery-output');
  out.innerHTML = '<p class="muted">Abrindo entrega…</p>';
  try {
    const data = await api('/api/delivery?dir=' + encodeURIComponent(dir));
    out.innerHTML = '';
    if (data.index) {
      out.append(el('p', { class: 'muted', text: `Índice: ${data.index.completedCount}/${data.index.profileCount} entrega(s) válida(s) — ${data.index.overallStatus}` }));
    }
    for (const prof of data.profiles) {
      const id = prof.profileId;
      const base = `/media?dir=${encodeURIComponent(dir)}&profile=${encodeURIComponent(id)}`;
      const valid = data.index ? (data.index.profiles.find((p) => p.profileId === id) || {}) : {};
      const card = el('div', { class: 'profile-card' }, [
        el('strong', { text: id + ' ' }),
        valid.lastValidDelivery ? el('span', { class: 'badge ok', text: 'entrega válida' }) : el('span', { class: 'badge muted', text: 'sem entrega válida' }),
        valid.lastAttempt && valid.lastAttempt.status === 'failed' ? el('span', { class: 'badge err', text: 'última tentativa falhou: ' + (valid.lastAttempt.failureCode || valid.lastAttempt.error || '') }) : null,
        el('video', { controls: '', preload: 'metadata', src: base + '&kind=video' }),
        el('div', {}, [
          el('a', { href: base + '&kind=video', download: '', text: 'Baixar MP4' }),
          el('a', { href: base + '&kind=srt', download: '', text: 'Baixar SRT' }),
          el('a', { href: base + '&kind=narration', download: '', text: 'Baixar narração TXT' }),
          el('button', { class: 'secondary', text: 'Reexportar este perfil', onclick: () => { $('#output-dir').value = dir; startExport(id); } }),
        ]),
      ]);
      out.append(card);
    }
    if (!data.profiles.length) out.append(el('p', { class: 'muted', text: 'Nenhuma entrega promovida nesta pasta.' }));
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function renderAll() {
  renderDraftFields();
  renderMedia();
  renderScenes();
  renderExportProfileOptions();
  if (catalog.length) renderProfiles();
}

async function init() {
  draft = emptyDraft();
  await loadProjects();
  await loadExamples();
  renderAll();
  $('#btn-load-profiles').addEventListener('click', () => loadProfiles().catch((e) => toast(e.message)));
  $('#btn-load-example').addEventListener('click', loadExample);
  $('#btn-save-draft').addEventListener('click', () => saveDraft().catch((e) => toast(e.message)));
  $('#btn-open-draft').addEventListener('click', () => openDraft().catch((e) => toast(e.message)));
  $('#btn-scan-media').addEventListener('click', () => scanMedia().catch((e) => toast(e.message)));
  $('#btn-generate-media').addEventListener('click', () => generateMedia().catch((e) => toast(e.message)));
  $('#btn-add-scene').addEventListener('click', addScene);
  $('#btn-preview').addEventListener('click', preview);
  $('#btn-export').addEventListener('click', () => startExport());
  $('#btn-load-delivery').addEventListener('click', () => loadDelivery().catch((e) => toast(e.message)));
}

init();