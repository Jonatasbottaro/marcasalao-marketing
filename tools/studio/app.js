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

// ================= Carrossel (R003) =================
let cdraft = null;
let cPollTimer = null;

function emptyCarousel() {
  return { schemaVersion: 1, id: 'novo-carrossel', project: '', profile: 'instagram-feed-image-square', title: 'Novo carrossel', media: [], cards: [] };
}

function setMode(mode) {
  $('#mode-video').hidden = mode !== 'video';
  $('#mode-carousel').hidden = mode !== 'carousel';
  $('#mode-motion').hidden = mode !== 'motion';
  $('#mode-video-btn').classList.toggle('active', mode === 'video');
  $('#mode-carousel-btn').classList.toggle('active', mode === 'carousel');
  $('#mode-motion-btn').classList.toggle('active', mode === 'motion');
  if (mode === 'motion') drawMotionCanvas();
}

async function loadCProjects() {
  const data = await api('/api/projects');
  const sel = $('#c-project-select');
  sel.innerHTML = '';
  sel.append(el('option', { value: '', text: '— selecione —' }));
  for (const p of data.projects) sel.append(el('option', { value: p.path, text: `${p.id} — ${p.name || ''}` }));
  if (cdraft && cdraft.project) sel.value = cdraft.project;
}

async function loadCProfiles() {
  const project = $('#c-project-select').value;
  if (!project) { toast('Selecione um projeto.'); return; }
  cdraft.project = project;
  const data = await api('/api/profiles?project=' + encodeURIComponent(project));
  const p = data.listing.profiles.find((x) => x.id === 'instagram-feed-image-square');
  $('#c-profile-info').textContent = p
    ? `instagram-feed-image-square: ${p.width}×${p.height} — ${p.availability === 'allowed' ? 'permitido' : 'bloqueado (' + p.blockCode + ')'}`
    : 'perfil instagram-feed-image-square ausente no catálogo';
}

async function loadCExamples() {
  const data = await api('/api/examples');
  const sel = $('#c-example-select');
  sel.innerHTML = '';
  const carousels = data.examples.filter((e) => e.kind === 'carousel');
  for (const ex of carousels) sel.append(el('option', { value: ex.path, text: ex.name }));
  sel._examples = carousels;
}

function loadCExample() {
  const sel = $('#c-example-select');
  const ex = (sel._examples || []).find((e) => e.path === sel.value);
  if (!ex) { toast('Selecione um exemplo.'); return; }
  cdraft = JSON.parse(JSON.stringify(ex.request));
  $('#c-draft-path').value = '.workspace/tmp/video-studio/drafts/' + cdraft.id + '.json';
  $('#c-output-dir').value = '.workspace/archives/video-studio/' + cdraft.id;
  $('#c-delivery-dir').value = '.workspace/archives/video-studio/' + cdraft.id;
  $('#c-project-select').value = cdraft.project;
  renderCAll();
  loadCProfiles();
  toast('Exemplo de carrossel carregado: ' + cdraft.id);
}

async function saveCDraft() {
  syncCFields();
  const path = $('#c-draft-path').value.trim();
  if (!path) { toast('Informe o caminho.'); return; }
  const d = await post('/api/draft/save', { path, request: cdraft });
  toast('Rascunho salvo: ' + d.path);
}

async function openCDraft() {
  const path = $('#c-draft-path').value.trim();
  if (!path) { toast('Informe o caminho.'); return; }
  const d = await api('/api/draft/load?path=' + encodeURIComponent(path));
  cdraft = d.request;
  $('#c-project-select').value = cdraft.project || '';
  renderCAll();
  if (cdraft.project) loadCProfiles();
  toast('Rascunho reaberto.');
}

function syncCFields() {
  if (!cdraft) return;
  cdraft.id = $('#c-req-id').value.trim() || cdraft.id;
  cdraft.title = $('#c-req-title').value;
}

function renderCFields() {
  $('#c-req-id').value = cdraft.id || '';
  $('#c-req-title').value = cdraft.title || '';
}

function renderCMedia() {
  const tbody = $('#c-media-table tbody');
  tbody.innerHTML = '';
  cdraft.media.forEach((m, i) => {
    tbody.append(el('tr', {}, [
      el('td', { text: m.id }), el('td', { text: m.type }), el('td', { text: m.path }),
      el('td', {}, el('input', { type: 'text', value: m.origin || '', oninput: (e) => { m.origin = e.target.value; } })),
      el('td', {}, el('input', { type: 'text', value: m.license || 'pending', oninput: (e) => { m.license = e.target.value; } })),
      el('td', {}, el('button', { class: 'secondary', text: 'Remover', onclick: () => { cdraft.media.splice(i, 1); renderCMedia(); renderCCards(); } })),
    ]));
  });
}

async function scanCMedia() {
  const folder = $('#c-media-folder').value.trim();
  if (!folder) { toast('Informe a pasta.'); return; }
  const d = await post('/api/media/scan', { folder });
  let added = 0;
  for (const f of d.media) {
    if (f.type !== 'image' || cdraft.media.some((m) => m.path === f.path)) continue;
    const id = f.name.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'media';
    let u = id; let n = 2;
    while (cdraft.media.some((m) => m.id === u)) u = `${id}-${n++}`;
    cdraft.media.push({ id: u, path: f.path, type: 'image', origin: 'synthetic', license: 'pending' });
    added++;
  }
  renderCMedia(); renderCCards();
  toast(`${added} mídia(s) cadastrada(s).`);
}

async function generateCMedia() {
  syncCFields();
  if (!cdraft.media.length) { toast('Cadastre mídias primeiro.'); return; }
  toast('Gerando mídia fictícia…');
  const d = await post('/api/media/generate', { request: cdraft });
  toast(`${d.written.length} arquivo(s) gerado(s).`);
}

function renderCCards() {
  const list = $('#c-cards-list');
  list.innerHTML = '';
  cdraft.cards.forEach((c, i) => {
    const mediaSel = el('select', { onchange: (e) => { c.mediaId = e.target.value || undefined; } });
    mediaSel.append(el('option', { value: '', text: '— sem mídia —' }));
    for (const m of cdraft.media) mediaSel.append(el('option', { value: m.id, text: m.id }));
    mediaSel.value = c.mediaId || '';
    list.append(el('div', { class: 'scene' }, [
      el('div', { class: 'row' }, [
        el('label', { text: `Card ${i + 1} — id` }, el('input', { type: 'text', value: c.id, oninput: (e) => { c.id = e.target.value; } })),
        el('label', { text: 'Mídia' }, mediaSel),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Título' }, el('input', { type: 'text', value: c.title || '', oninput: (e) => { c.title = e.target.value; } })),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Corpo (opcional)' }, el('input', { type: 'text', value: c.body || '', oninput: (e) => { c.body = e.target.value || undefined; } })),
      ]),
      el('div', { class: 'row' }, [
        el('button', { class: 'secondary', text: '↑', onclick: () => { if (i > 0) { [cdraft.cards[i - 1], cdraft.cards[i]] = [cdraft.cards[i], cdraft.cards[i - 1]]; renderCCards(); } } }),
        el('button', { class: 'secondary', text: '↓', onclick: () => { if (i < cdraft.cards.length - 1) { [cdraft.cards[i + 1], cdraft.cards[i]] = [cdraft.cards[i], cdraft.cards[i + 1]]; renderCCards(); } } }),
        el('button', { class: 'secondary', text: 'Remover', onclick: () => { cdraft.cards.splice(i, 1); renderCCards(); } }),
      ]),
    ]));
  });
}

function addCCard() {
  const n = cdraft.cards.length + 1;
  cdraft.cards.push({ id: `card-${n}`, title: '', body: '', mediaId: cdraft.media[0]?.id });
  renderCCards();
}

async function cPreview() {
  syncCFields();
  const out = $('#c-preview-output');
  out.innerHTML = '<p class="muted">Calculando prévia…</p>';
  try {
    const d = await post('/api/preview', { request: cdraft, kind: 'carousel' });
    const r = d.result;
    out.innerHTML = '';
    if (r.status !== 'preview') { out.append(el('pre', { text: JSON.stringify(r, null, 2) })); return; }
    out.append(el('p', { text: `Carrossel ${r.requestId} — ${r.profileId} ${r.geometry.width}×${r.geometry.height}` }));
    for (const c of r.cards) {
      out.append(el('div', { text: `${String(c.order).padStart(2, '0')} ${c.id}: ${c.title}` + (c.overflow ? '  [EXCEDE ÁREA — ajuste o texto]' : '') , class: c.overflow ? 'badge err' : '' }));
    }
    if (r.overflowCards && r.overflowCards.length) out.append(el('p', { class: 'badge err', text: 'Cards a ajustar: ' + r.overflowCards.join(', ') }));
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

async function cExport() {
  syncCFields();
  const outputDir = $('#c-output-dir').value.trim();
  if (!outputDir) { toast('Informe a pasta de entrega.'); return; }
  const status = $('#c-export-status');
  status.innerHTML = '<p class="muted">Exportando carrossel…</p>';
  try {
    const d = await post('/api/export', { request: cdraft, outputDir, kind: 'carousel' });
    cPoll(d.jobId, outputDir);
  } catch (err) { status.innerHTML = ''; status.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function cPoll(jobId, outputDir) {
  if (cPollTimer) clearTimeout(cPollTimer);
  const tick = async () => {
    const d = await api('/api/export/status?job=' + jobId);
    const status = $('#c-export-status');
    if (d.status === 'running') { status.innerHTML = '<p class="muted">Exportando… (segundo plano)</p>'; cPollTimer = setTimeout(tick, 1200); return; }
    status.innerHTML = '';
    status.append(el('p', {}, el('span', { class: d.status === 'completed' ? 'badge ok' : 'badge err', text: d.status })));
    const r = d.result || {};
    if (r.cards) for (const f of r.cards) status.append(el('div', { text: '✓ ' + f }));
    if (d.status !== 'completed') status.append(el('pre', { text: JSON.stringify(r, null, 2) }));
    $('#c-delivery-dir').value = outputDir;
    loadCDelivery();
  };
  tick();
}

async function loadCDelivery() {
  const dir = $('#c-delivery-dir').value.trim();
  if (!dir) { toast('Informe a pasta de entrega.'); return; }
  const out = $('#c-delivery-output');
  out.innerHTML = '<p class="muted">Abrindo entrega…</p>';
  try {
    const d = await api('/api/carousel-delivery?dir=' + encodeURIComponent(dir));
    out.innerHTML = '';
    if (d.index) {
      const lv = d.index.lastValidDelivery;
      const la = d.index.lastAttempt;
      out.append(el('p', {}, [
        lv ? el('span', { class: 'badge ok', text: 'entrega válida' }) : el('span', { class: 'badge muted', text: 'sem entrega válida' }),
        la && la.status === 'failed' ? el('span', { class: 'badge err', text: 'última tentativa falhou' }) : null,
      ]));
    }
    if (!d.manifest) { out.append(el('p', { class: 'muted', text: 'Nenhum manifesto de carrossel nesta pasta.' })); return; }
    const base = `/media?dir=${encodeURIComponent(dir)}`;
    out.append(el('p', {}, el('a', { href: base + '&kind=zip', download: '', text: 'Baixar ZIP (carousel.zip)' })));
    d.manifest.cards.forEach((c, i) => {
      out.append(el('div', { class: 'profile-card' }, [
        el('strong', { text: `${String(c.order).padStart(2, '0')} ${c.id} ` }),
        el('img', { class: 'card-thumb', src: `${base}&kind=card&index=${i}`, alt: c.id }),
        el('div', {}, el('a', { href: `${base}&kind=card&index=${i}`, download: c.file, text: 'Baixar ' + c.file })),
      ]));
    });
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function renderCAll() { renderCFields(); renderCMedia(); renderCCards(); }

async function initCarousel() {
  cdraft = emptyCarousel();
  await loadCProjects();
  await loadCExamples();
  renderCAll();
  $('#c-btn-load-profiles').addEventListener('click', () => loadCProfiles().catch((e) => toast(e.message)));
  $('#c-btn-load-example').addEventListener('click', loadCExample);
  $('#c-btn-save-draft').addEventListener('click', () => saveCDraft().catch((e) => toast(e.message)));
  $('#c-btn-open-draft').addEventListener('click', () => openCDraft().catch((e) => toast(e.message)));
  $('#c-btn-scan-media').addEventListener('click', () => scanCMedia().catch((e) => toast(e.message)));
  $('#c-btn-generate-media').addEventListener('click', () => generateCMedia().catch((e) => toast(e.message)));
  $('#c-btn-add-card').addEventListener('click', addCCard);
  $('#c-btn-preview').addEventListener('click', cPreview);
  $('#c-btn-export').addEventListener('click', cExport);
  $('#c-btn-load-delivery').addEventListener('click', () => loadCDelivery().catch((e) => toast(e.message)));
}

// ================= Motion (contorno animado) =================
let mreq = null, mplan = null, mImg = null, mDrag = null, mPollTimer = null;
const mEffect = () => (mplan && mplan.effects[0]) || null;

async function loadMExamples() {
  const d = await api('/api/examples');
  const sel = $('#m-example-select');
  sel.innerHTML = '';
  const vids = d.examples.filter((e) => e.kind === 'video' && e.name.includes('motion'));
  for (const e of vids) sel.append(el('option', { value: e.path, text: e.name }));
  sel._examples = vids;
}

function loadMExample() {
  const sel = $('#m-example-select');
  const ex = (sel._examples || []).find((e) => e.path === sel.value);
  if (!ex) { toast('Selecione um exemplo.'); return; }
  mreq = JSON.parse(JSON.stringify(ex.request));
  $('#m-plan-path').value = '.workspace/tmp/video-studio/drafts/' + mreq.id + '.motion.json';
  $('#m-output-dir').value = '.workspace/archives/video-studio/' + mreq.id;
  const planPath = ex.path.replace('.video-request.json', '.motion-plan.json');
  api('/api/draft/load?path=' + encodeURIComponent(planPath))
    .then((d) => { mplan = d.request; afterMPlan(); })
    .catch(() => {
      mplan = { schemaVersion: 1, requestId: mreq.id, effects: [{ sceneId: mreq.scenes[0].id, region: { x: 0.1, y: 0.3, w: 0.8, h: 0.15 }, color: '#FFD700', thickness: 6, startMs: 500, endMs: 3000 }] };
      afterMPlan();
    });
  populateMProfiles();
}

function afterMPlan() {
  const e = mEffect();
  $('#m-start').value = e.startMs; $('#m-end').value = e.endMs;
  $('#m-color').value = e.color; $('#m-thickness').value = e.thickness;
  populateMScenes(); drawMotionCanvas(); updateMRegionInfo();
}

function populateMScenes() {
  const sel = $('#m-scene-select');
  sel.innerHTML = '';
  for (const s of mreq.scenes) sel.append(el('option', { value: s.id, text: s.id }));
  sel.value = mEffect().sceneId;
  sel.onchange = () => { mEffect().sceneId = sel.value; mImg = null; drawMotionCanvas(); };
}

function populateMProfiles() {
  const sel = $('#m-profile-select');
  sel.innerHTML = '';
  for (const p of mreq.profiles) sel.append(el('option', { value: p, text: p }));
}

function currentMedia() {
  const s = mreq.scenes.find((x) => x.id === mEffect().sceneId);
  return mreq.media.find((m) => m.id === s.mediaId);
}

function drawMotionCanvas() {
  const cv = $('#m-canvas'); const ctx = cv.getContext('2d');
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, cv.width, cv.height);
  if (!mreq || !mplan) return;
  const media = currentMedia(); if (!media) return;
  if (!mImg || mImg._src !== media.path) {
    mImg = new Image(); mImg._src = media.path;
    mImg.onload = () => drawMotionCanvas();
    mImg.src = '/source-media?path=' + encodeURIComponent(media.path);
    return;
  }
  const scale = Math.min(cv.width / mImg.width, cv.height / mImg.height);
  const dw = mImg.width * scale, dh = mImg.height * scale;
  ctx.drawImage(mImg, (cv.width - dw) / 2, (cv.height - dh) / 2, dw, dh);
  const r = mEffect().region;
  ctx.strokeStyle = mEffect().color; ctx.lineWidth = 3;
  ctx.strokeRect(r.x * cv.width, r.y * cv.height, r.w * cv.width, r.h * cv.height);
}

function updateMRegionInfo() {
  const e = mEffect(); if (!e) return;
  const r = e.region;
  $('#m-region-info').textContent = `Região x=${r.x.toFixed(2)} y=${r.y.toFixed(2)} w=${r.w.toFixed(2)} h=${r.h.toFixed(2)} — contorno de ${e.startMs}ms a ${e.endMs}ms (relativo à cena ${e.sceneId}).`;
}

function canvasFraction(ev) {
  const cv = $('#m-canvas'); const rect = cv.getBoundingClientRect();
  return { x: (ev.clientX - rect.left) / rect.width, y: (ev.clientY - rect.top) / rect.height };
}

function initMotionCanvas() {
  const cv = $('#m-canvas');
  cv.addEventListener('pointerdown', (ev) => { mDrag = canvasFraction(ev); cv.setPointerCapture(ev.pointerId); });
  cv.addEventListener('pointermove', (ev) => {
    if (!mDrag || !mEffect()) return;
    const p = canvasFraction(ev);
    const x = Math.min(mDrag.x, p.x), y = Math.min(mDrag.y, p.y);
    const w = Math.abs(p.x - mDrag.x), h = Math.abs(p.y - mDrag.y);
    mEffect().region = { x: Math.max(0, x), y: Math.max(0, y), w: Math.min(1, w), h: Math.min(1, h) };
    drawMotionCanvas(); updateMRegionInfo();
  });
  cv.addEventListener('pointerup', () => { mDrag = null; });
  for (const [id, key] of [['m-start', 'startMs'], ['m-end', 'endMs'], ['m-thickness', 'thickness']]) {
    $('#' + id).addEventListener('input', (e) => { if (mEffect()) { mEffect()[key] = Number(e.target.value); updateMRegionInfo(); } });
  }
  $('#m-color').addEventListener('input', (e) => { if (mEffect()) { mEffect().color = e.target.value; drawMotionCanvas(); } });
}

async function saveMPlan() {
  const path = $('#m-plan-path').value.trim();
  if (!path || !mplan) { toast('Informe o caminho do plano.'); return; }
  const d = await post('/api/draft/save', { path, request: mplan });
  toast('Plano salvo: ' + d.path);
}

async function openMPlan() {
  const path = $('#m-plan-path').value.trim();
  if (!path) { toast('Informe o caminho do plano.'); return; }
  const d = await api('/api/draft/load?path=' + encodeURIComponent(path));
  mplan = d.request; afterMPlan(); toast('Plano reaberto.');
}

async function mPreview() {
  const out = $('#m-preview-output');
  out.innerHTML = '<p class="muted">Calculando prévia…</p>';
  try {
    const d = await post('/api/preview', { request: mreq, motionPlan: mplan, kind: 'video' });
    const r = d.result;
    out.innerHTML = '';
    if (r.status !== 'preview') { out.append(el('pre', { text: JSON.stringify(r, null, 2) })); return; }
    for (const p of r.profiles) {
      if (p.status !== 'compiled') { out.append(el('p', { class: 'badge err', text: `${p.profileId}: ${p.failureCode}` })); continue; }
      const mo = p.motion;
      if (!mo) { out.append(el('p', { text: `${p.profileId}: sem motion` })); continue; }
      for (const e of mo.effects) {
        out.append(el('p', { text: `${p.profileId} / ${e.sceneId}: contorno ${e.absoluteStartMs}ms→${e.absoluteEndMs}ms (absoluto), região x=${e.region.x.toFixed(2)} y=${e.region.y.toFixed(2)} w=${e.region.w.toFixed(2)} h=${e.region.h.toFixed(2)}, cor ${e.color}` }));
      }
    }
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

async function mExport() {
  const outputDir = $('#m-output-dir').value.trim();
  if (!outputDir) { toast('Informe a pasta de entrega.'); return; }
  const status = $('#m-export-status');
  status.innerHTML = '<p class="muted">Exportando com Motion…</p>';
  try {
    const d = await post('/api/export', { request: mreq, outputDir, profile: $('#m-profile-select').value, kind: 'video', motionPlan: mplan });
    mPoll(d.jobId, outputDir);
  } catch (err) { status.innerHTML = ''; status.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function mPoll(jobId, outputDir) {
  if (mPollTimer) clearTimeout(mPollTimer);
  const tick = async () => {
    const d = await api('/api/export/status?job=' + jobId);
    const status = $('#m-export-status');
    if (d.status === 'running') { status.innerHTML = '<p class="muted">Exportando… (segundo plano)</p>'; mPollTimer = setTimeout(tick, 1200); return; }
    status.innerHTML = '';
    status.append(el('p', {}, el('span', { class: d.status === 'completed' ? 'badge ok' : 'badge err', text: d.status })));
    const out = $('#m-delivery-output');
    out.innerHTML = '';
    if (d.status === 'completed') {
      const profile = $('#m-profile-select').value;
      const base = `/media?dir=${encodeURIComponent(outputDir)}&profile=${encodeURIComponent(profile)}`;
      out.append(el('video', { controls: '', preload: 'metadata', src: base + '&kind=video' }));
      out.append(el('div', {}, [
        el('a', { href: base + '&kind=video', download: '', text: 'Baixar MP4' }),
        el('a', { href: base + '&kind=srt', download: '', text: 'SRT' }),
        el('a', { href: base + '&kind=narration', download: '', text: 'Narração' }),
      ]));
    } else {
      out.append(el('pre', { text: JSON.stringify(d.result, null, 2) }));
    }
  };
  tick();
}

async function initMotion() {
  await loadMExamples();
  initMotionCanvas();
  $('#m-btn-load-example').addEventListener('click', loadMExample);
  $('#m-btn-save-plan').addEventListener('click', () => saveMPlan().catch((e) => toast(e.message)));
  $('#m-btn-open-plan').addEventListener('click', () => openMPlan().catch((e) => toast(e.message)));
  $('#m-btn-preview').addEventListener('click', mPreview);
  $('#m-btn-export').addEventListener('click', mExport);
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
  $('#mode-video-btn').addEventListener('click', () => setMode('video'));
  $('#mode-carousel-btn').addEventListener('click', () => setMode('carousel'));
  $('#mode-motion-btn').addEventListener('click', () => setMode('motion'));
  await initCarousel();
  await initMotion();
  setMode('video');
}

init();