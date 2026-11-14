'use strict';

let currentWork = null;
let allProjects = [];
let draft = null;
let catalog = [];
let pollTimer = null;

let cdraft = null;
let cCatalog = [];
let cPollTimer = null;

let mreq = null;
let mplan = null;
let mImg = null;
let mDrag = null;
let mPollTimer = null;
let mCurrentSceneId = null;
let mStandaloneOverride = false;

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
  setTimeout(() => t.classList.remove('show'), 3800);
}

function slugifyKebab(text) {
  return String(text || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ ok: false, error: 'resposta ilegível' }));
  if (!res.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}
const post = (path, body) => api(path, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

function emptyDraft() {
  return {
    schemaVersion: 1,
    id: 'novo-pedido',
    project: '',
    title: 'Novo vídeo',
    locale: 'pt-BR',
    profiles: [],
    visualStyle: {
      schemaVersion: 1,
      id: 'estilo-padrao',
      title: {
        textColor: '#FFFFFF',
        outlineColor: '#000000',
        fontSize: 42,
        marginTop: 160,
        marginHorizontal: 60,
      },
    },
    media: [],
    scenes: [],
  };
}

function emptyCarousel() {
  return {
    schemaVersion: 1,
    id: 'novo-carrossel',
    project: '',
    profile: 'instagram-feed-image-square',
    title: 'Novo carrossel',
    media: [],
    cards: [],
  };
}

// ---- Prontidão do ambiente ----
async function loadReadiness() {
  const pill = $('#readiness-banner');
  const box = $('#readiness-details');
  try {
    const data = await api('/api/readiness');
    const r = data.readiness;
    pill.textContent = r.ready ? 'Ambiente pronto ✓' : 'Ambiente incompleto !';
    pill.className = 'readiness-pill ' + (r.ready ? 'ok' : 'err');
    box.innerHTML = '';
    box.append(el('p', { text: r.summary }));
    const list = el('ul', {});
    for (const item of r.items) {
      const li = el('li', {}, [
        el('span', { class: item.ok ? 'badge ok' : 'badge err', text: item.ok ? 'OK' : 'FALTA' }),
        el('strong', { text: ' ' + item.label + ': ' }),
        document.createTextNode(item.detail),
      ]);
      if (item.instruction) li.append(el('div', { class: 'muted', text: 'Ação: ' + item.instruction }));
      list.append(li);
    }
    box.append(list);
    box.hidden = r.ready;
  } catch (err) {
    pill.textContent = 'Erro ao verificar ambiente';
    pill.className = 'readiness-pill err';
    box.hidden = false;
    box.textContent = err.message;
  }
}

// ---- Navegação entre abas ----
function setMode(mode) {
  $('#mode-home').hidden = mode !== 'home';
  $('#mode-video').hidden = mode !== 'video';
  $('#mode-carousel').hidden = mode !== 'carousel';
  $('#mode-motion').hidden = mode !== 'motion';
  $('#mode-home-btn').classList.toggle('active', mode === 'home');
  $('#mode-video-btn').classList.toggle('active', mode === 'video');
  $('#mode-carousel-btn').classList.toggle('active', mode === 'carousel');
  $('#mode-motion-btn').classList.toggle('active', mode === 'motion');
  if (mode === 'motion') {
    if (currentWork && !mStandaloneOverride) {
      syncDraftFields();
      syncMotionFromDraft();
    }
    drawMotionCanvas();
  }
  if (mode === 'home') {
    loadWorks().catch(() => {});
  }
}

// ---- Projetos e Cadastro ----
async function loadProjects() {
  const data = await api('/api/projects');
  allProjects = data.projects || [];

  const fillSelect = (sel, currentVal) => {
    sel.innerHTML = '';
    sel.append(el('option', { value: '', text: '— selecione —' }));
    for (const p of allProjects) {
      const tag = p.source === 'registered' ? '[Cadastrado]' : '[Exemplo]';
      sel.append(el('option', { value: p.path, text: `${tag} ${p.id} — ${p.name || ''}` }));
    }
    if (currentVal) sel.value = currentVal;
  };

  fillSelect($('#work-project'), $('#work-project').value || (allProjects[0]?.path || ''));
  fillSelect($('#project-select'), draft?.project);
  fillSelect($('#c-project-select'), cdraft?.project);

  const tbody = $('#projects-table tbody');
  tbody.innerHTML = '';
  for (const p of allProjects) {
    const badge = el('span', {
      class: p.source === 'registered' ? 'badge ok' : 'badge muted',
      text: p.sourceLabel || p.source || 'exemplo',
    });
    tbody.append(el('tr', {}, [
      el('td', { text: p.id || '' }),
      el('td', { text: p.name || '' }),
      el('td', {}, badge),
      el('td', { text: p.locale || '' }),
      el('td', { text: (p.outputProfiles || []).join(', ') }),
    ]));
  }
}

async function createProject() {
  const id = $('#proj-id').value.trim();
  const name = $('#proj-name').value.trim();
  const locale = $('#proj-locale').value.trim() || 'pt-BR';
  const timezone = $('#proj-tz').value.trim() || 'America/Sao_Paulo';
  const brandTheme = $('#proj-theme').value.trim() || id;
  const assetRoot = $('#proj-asset-root').value.trim() || `.workspace/studio/projects/${id}/assets`;
  const outputProfiles = Array.from(document.querySelectorAll('#proj-profiles-boxes input[type="checkbox"]:checked'))
    .map((cb) => cb.value);

  const feedback = $('#proj-create-feedback');
  feedback.innerHTML = '';
  try {
    const data = await post('/api/projects/create', {
      schemaVersion: 1,
      id,
      name,
      locale,
      timezone,
      brandTheme,
      assetRoot,
      contentPolicies: {
        requireApprovedBriefing: $('#proj-pol-briefing').checked,
        requireApprovedScript: $('#proj-pol-script').checked,
        prohibitPersonalData: $('#proj-pol-pii').checked,
        requireFunctionalEvidence: $('#proj-pol-evidence').checked,
      },
      outputProfiles,
    });
    await loadProjects();
    $('#work-project').value = data.path;
    feedback.append(el('div', {
      class: 'alert-box ok',
      text: `Projeto cadastrado e validado pelo núcleo: ${data.project.id} (${data.path})`,
    }));
    toast('Projeto cadastrado: ' + data.project.id);
  } catch (err) {
    feedback.append(el('div', { class: 'alert-box err', text: 'Erro ao validar/cadastrar projeto: ' + err.message }));
    toast(err.message);
  }
}

// ---- Trabalhos (Home, Criar, Reabrir, Salvar, Demo) ----
function renderActiveWorkBar() {
  const bar = $('#active-work-bar');
  if (!currentWork) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  $('#active-work-title').textContent = `Trabalho ativo: ${currentWork.name} (${currentWork.id})`;
  $('#active-work-meta').textContent = ` — Projeto: ${currentWork.projectId || currentWork.project} · Pasta: ${currentWork.paths.workDir}`;
}

function updateWorkPathsPreview() {
  const id = $('#work-id').value.trim() || '<id-do-trabalho>';
  $('#work-paths-preview').textContent =
    `Caminhos automáticos em .workspace/studio/works/${id}/ (rascunhos/, media/ compartilhada e deliveries/).`;
}

async function loadWorks() {
  const data = await api('/api/works');
  const tbody = $('#works-table tbody');
  tbody.innerHTML = '';
  const works = data.works || [];
  if (!works.length) {
    tbody.append(el('tr', {}, el('td', { colspan: '8', class: 'muted', text: 'Nenhum trabalho criado ainda. Use a demonstração guiada ou crie um trabalho abaixo.' })));
    return;
  }
  for (const w of works) {
    const s = w.summary || {};
    const mk = (ok, st) => {
      if (st === 'failed' && !ok) return el('span', { class: 'badge err', text: 'falhou' });
      if (st === 'failed' && ok) return [el('span', { class: 'badge ok', text: 'válido' }), el('span', { class: 'badge err', text: 'tentativa falhou' })];
      if (st === 'interrupted') return [ok ? el('span', { class: 'badge ok', text: 'válido' }) : null, el('span', { class: 'badge warn', text: 'interrompida' })];
      if (ok) return el('span', { class: 'badge ok', text: typeof ok === 'number' ? `${ok} perfil(is)` : 'pronto' });
      return el('span', { class: 'badge muted', text: 'sem entrega' });
    };
    tbody.append(el('tr', {}, [
      el('td', { text: w.id }),
      el('td', { text: w.name }),
      el('td', { text: w.projectId || w.project }),
      el('td', {}, mk(s.videoValidCount, s.videoLastStatus)),
      el('td', {}, mk(s.carouselValid, s.carouselLastStatus)),
      el('td', {}, mk(s.motionValidCount, s.motionLastStatus)),
      el('td', { text: (w.updatedAt || '').replace('T', ' ').replace('Z', '') }),
      el('td', {}, el('button', {
        text: 'Reabrir',
        onclick: () => openWork(w.id).then(() => setMode('video')).catch((e) => toast(e.message)),
      })),
    ]));
  }
}

function applyOpenedWork(data) {
  currentWork = data.work;
  mStandaloneOverride = false;
  const p = currentWork.paths;

  draft = JSON.parse(JSON.stringify(data.videoRequest));
  cdraft = JSON.parse(JSON.stringify(data.carouselRequest));
  mreq = JSON.parse(JSON.stringify(data.videoRequest));
  mplan = JSON.parse(JSON.stringify(data.motionPlan));

  $('#project-select').value = draft.project || currentWork.project || '';
  $('#c-project-select').value = cdraft.project || currentWork.project || '';
  $('#draft-path').value = p.videoDraft;
  $('#media-folder').value = p.mediaDir;
  $('#output-dir').value = p.videoDeliveryDir;
  $('#delivery-dir').value = p.videoDeliveryDir;

  $('#c-draft-path').value = p.carouselDraft;
  $('#c-media-folder').value = p.mediaDir;
  $('#c-output-dir').value = p.carouselDeliveryDir;
  $('#c-delivery-dir').value = p.carouselDeliveryDir;

  $('#m-plan-path').value = p.motionPlan;
  $('#m-output-dir').value = p.motionDeliveryDir;

  catalog = (data.listing && data.listing.profiles) || [];
  cCatalog = catalog;

  for (const sel of ['#preview-output', '#c-preview-output', '#m-preview-output', '#export-status', '#c-export-status', '#m-export-status']) {
    $(sel).innerHTML = '';
  }

  renderActiveWorkBar();
  renderAll();
  renderCAll();
  renderCProfileOptions();
  populateMProfiles();
  mCurrentSceneId = (mplan.effects && mplan.effects[0]?.sceneId) || (mreq.scenes && mreq.scenes[0]?.id) || null;
  afterMPlan();

  if (data.deliveries) {
    renderVideoDeliveryPayload('#delivery-output', data.deliveries.video, p.videoDeliveryDir, 'video');
    renderCarouselDeliveryPayload(data.deliveries.carousel, p.carouselDeliveryDir);
    renderVideoDeliveryPayload('#m-delivery-output', data.deliveries.motion, p.motionDeliveryDir, 'motion');
  }
  loadWorks().catch(() => {});
}

async function createWork() {
  const name = $('#work-name').value.trim();
  const id = $('#work-id').value.trim();
  const project = $('#work-project').value;
  const template = $('#work-template').value;
  const feedback = $('#work-create-feedback');
  feedback.innerHTML = '';
  try {
    const data = await post('/api/works/create', { id, name: name || id, project, template });
    applyOpenedWork(data);
    setMode('video');
    toast('Trabalho criado e aberto: ' + data.work.id);
  } catch (err) {
    feedback.append(el('div', { class: 'alert-box err', text: err.message }));
    toast(err.message);
  }
}

async function openWork(workId) {
  const data = await api('/api/works/open?id=' + encodeURIComponent(workId));
  applyOpenedWork(data);
  toast('Trabalho retomado: ' + data.work.id);
  return data;
}

async function saveWork(silent = false) {
  if (!currentWork) {
    if (!silent) toast('Crie ou abra um trabalho na aba Trabalhos & Projetos.');
    return null;
  }
  syncDraftFields();
  syncCFields();
  const payload = {
    workId: currentWork.id,
    videoRequest: draft,
    carouselRequest: cdraft,
    motionPlan: mplan,
  };
  const data = await post('/api/works/save', payload);
  currentWork = data.work;
  renderActiveWorkBar();
  if (!silent) toast('Trabalho salvo em disco com segurança.');
  loadWorks().catch(() => {});
  return data;
}

async function startGuidedDemo(brand) {
  const box = $('#demo-feedback');
  box.innerHTML = '<p class="muted">Preparando trabalho de demonstração…</p>';
  try {
    const data = await post('/api/works/demo', { brand });
    box.innerHTML = '';
    applyOpenedWork(data);
    setMode('video');
    toast('Demonstração guiada pronta: ' + data.work.id);
  } catch (err) {
    box.innerHTML = '';
    box.append(el('div', { class: 'alert-box err', text: err.message }));
    toast(err.message);
  }
}

// ---- Perfis e Vídeos ----
async function loadProfiles() {
  const project = $('#project-select').value;
  if (!project) { toast('Selecione um projeto.'); return; }
  draft.project = project;
  const data = await api('/api/profiles?project=' + encodeURIComponent(project) + '&module=video');
  catalog = data.listing.profiles;
  // Remove perfis selecionados que deixaram de ser compatíveis com o projeto atual
  const allowedIds = new Set(catalog.filter((p) => p.localExportVideo).map((p) => p.id));
  draft.profiles = (draft.profiles || []).filter((id) => allowedIds.has(id));
  renderProfiles();
  renderExportProfileOptions();
  populateMProfiles();
  toast(`${data.listing.compatibleProfiles.length} destino(s) compatível(is) com Vídeo.`);
}

function renderProfiles() {
  const tbody = $('#profiles-table tbody');
  tbody.innerHTML = '';
  const showAll = $('#video-show-all-profiles').checked;
  const list = showAll ? catalog : catalog.filter((p) => p.localExportVideo);
  if (!list.length) {
    tbody.append(el('tr', {}, el('td', {
      colspan: '7',
      class: 'muted',
      text: 'Nenhum destino compatível com Vídeo 9:16@30 neste projeto. Marque perfis compatíveis ou "Mostrar perfis fora do recorte".',
    })));
    return;
  }
  for (const p of list) {
    const checked = draft.profiles.includes(p.id);
    const usable = p.availability === 'allowed' && p.localExportVideo;
    const cb = el('input', {
      type: 'checkbox',
      onchange: (e) => {
        if (e.target.checked) { if (!draft.profiles.includes(p.id)) draft.profiles.push(p.id); }
        else draft.profiles = draft.profiles.filter((x) => x !== p.id);
        renderExportProfileOptions();
        populateMProfiles();
      },
    });
    cb.checked = checked;
    cb.disabled = !usable;
    const avail = p.availability === 'allowed'
      ? el('span', { class: 'badge ok', text: 'permitido' })
      : p.availability === 'blocked'
        ? el('span', { class: 'badge err', text: p.blockCode || 'bloqueado' })
        : el('span', { class: 'badge muted', text: 'não consultado' });
    const local = p.localExportVideo
      ? el('span', { class: 'badge ok', text: '9:16@30 compatível' })
      : el('span', { class: 'badge muted', text: 'fora do recorte Vídeo' });
    tbody.append(el('tr', {}, [
      el('td', {}, cb),
      el('td', { text: p.id }),
      el('td', { text: `${p.network}/${p.publication}` }),
      el('td', { text: `${p.width}×${p.height} (${p.aspectRatio})` }),
      el('td', { text: p.fps == null ? '—' : String(p.fps) }),
      el('td', {}, avail),
      el('td', {}, local),
    ]));
  }
}

function renderExportProfileOptions() {
  const sel = $('#export-profile');
  const current = sel.value;
  sel.innerHTML = '';
  sel.append(el('option', { value: '', text: 'Todos os perfis selecionados' }));
  for (const id of draft.profiles) sel.append(el('option', { value: id, text: id }));
  if (draft.profiles.includes(current)) sel.value = current;
}

// ---- Exemplos e Rascunho Vídeo ----
async function loadExamples() {
  const data = await api('/api/examples');
  const sel = $('#example-select');
  sel.innerHTML = '';
  const vids = data.examples.filter((e) => e.kind === 'video');
  for (const ex of vids) sel.append(el('option', { value: ex.path, text: ex.name }));
  sel._examples = vids;
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

function syncDraftFields() {
  if (!draft) return;
  draft.id = $('#req-id').value.trim() || draft.id;
  draft.title = $('#req-title').value;
  draft.locale = $('#req-locale').value.trim() || 'pt-BR';
  draft.visualStyle = {
    schemaVersion: 1,
    id: $('#style-id').value.trim() || 'estilo-padrao',
    title: {
      textColor: $('#style-text').value.trim() || '#FFFFFF',
      outlineColor: $('#style-outline').value.trim() || '#000000',
      fontSize: Number($('#style-font').value) || 42,
      marginTop: Number($('#style-top').value) || 0,
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

// ---- Mídias Vídeo ----
function renderMedia() {
  const tbody = $('#media-table tbody');
  tbody.innerHTML = '';
  draft.media.forEach((m, i) => {
    const origin = el('input', { type: 'text', value: m.origin || '', oninput: (e) => { m.origin = e.target.value; } });
    const license = el('input', { type: 'text', value: m.license || 'pending', oninput: (e) => { m.license = e.target.value; } });
    tbody.append(el('tr', {}, [
      el('td', { text: m.id }),
      el('td', { text: m.type }),
      el('td', { text: m.path }),
      el('td', {}, origin),
      el('td', {}, license),
      el('td', {}, el('button', {
        class: 'secondary',
        text: 'Remover',
        onclick: () => { draft.media.splice(i, 1); renderMedia(); renderScenes(); },
      })),
    ]));
  });
}

async function scanMediaInto(targetDraft, folder, allowedTypes, afterRender) {
  if (!folder) { toast('Informe ou abra um trabalho com pasta de mídia.'); return; }
  const data = await post('/api/media/scan', { folder });
  let added = 0;
  for (const f of data.media) {
    if (allowedTypes && !allowedTypes.includes(f.type)) continue;
    if (targetDraft.media.some((m) => m.path === f.path)) continue;
    const base = slugifyKebab(f.name.replace(/\.[^.]+$/, '')) || 'media';
    let unique = base;
    let n = 2;
    while (targetDraft.media.some((m) => m.id === unique)) unique = `${base}-${n++}`;
    targetDraft.media.push({ id: unique, path: f.path, type: f.type, origin: 'studio-work', license: 'pending' });
    added++;
  }
  afterRender();
  toast(`${added} mídia(s) importada(s) para reutilização.`);
}

async function generateMedia() {
  syncDraftFields();
  if (!draft.media.length) { toast('Cadastre mídias no rascunho primeiro.'); return; }
  toast('Gerando mídia fictícia…');
  const data = await post('/api/media/generate', { request: draft });
  toast(`${data.written.length} arquivo(s) gerado(s).`);
}

// ---- Cenas Vídeo ----
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
  draft.scenes.push({
    id: `cena-${n}`,
    durationMs: 4000,
    mediaId: draft.media[0]?.id || '',
    caption: 'Nova cena',
    narration: 'Narração da nova cena.',
    narrativeFunction: 'demonstration',
    motionIntent: 'none',
  });
  renderScenes();
}

// ---- Prévia Vídeo ----
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
        el('table', {}, [
          el('thead', {}, el('tr', {}, [el('th', { text: 'Beat' }), el('th', { text: 'Intervalo' }), el('th', { text: 'Duração' }), el('th', { text: 'Mídia' }), el('th', { text: 'Título' })])),
          el('tbody', {}, rows),
        ]),
      ]);
      if (p.warnings && p.warnings.length) card.append(el('p', { class: 'timeline', text: 'Avisos: ' + p.warnings.map((w) => w.code).join(', ') }));
      out.append(card);
    }
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

// ---- Exportação e Entrega Vídeo/Motion ----
async function startExport(profileOverride) {
  syncDraftFields();
  const outputDir = $('#output-dir').value.trim();
  if (!outputDir) { toast('Crie um trabalho ou informe a pasta de entrega.'); return; }
  const profile = profileOverride !== undefined ? profileOverride : $('#export-profile').value;
  const status = $('#export-status');
  status.innerHTML = '<p class="muted">Exportação iniciada…</p>';
  try {
    const data = await post('/api/export', {
      request: draft,
      outputDir,
      profile: profile || undefined,
      workId: currentWork ? currentWork.id : undefined,
    });
    pollExport(data.jobId, outputDir);
  } catch (err) {
    status.innerHTML = '';
    status.append(el('div', { class: 'alert-box err', text: 'Erro: ' + err.message }));
  }
}

function pollExport(jobId, outputDir) {
  if (pollTimer) clearTimeout(pollTimer);
  const tick = async () => {
    const data = await api('/api/export/status?job=' + jobId);
    const status = $('#export-status');
    if (data.status === 'running') {
      status.innerHTML = '<p class="muted">Exportando… (render em segundo plano)</p>';
      pollTimer = setTimeout(tick, 1200);
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
  if (data.status !== 'completed' && (!r.profiles || !r.profiles.length)) {
    status.append(el('div', { class: 'alert-box err', text: r.error || JSON.stringify(r) }));
  }
  $('#delivery-dir').value = outputDir;
  loadDelivery();
  loadWorks().catch(() => {});
}

function renderLastAttemptBanner(out, lastExportStatus, kind) {
  if (!lastExportStatus) return;
  if (lastExportStatus.status === 'failed') {
    out.append(el('div', {
      class: 'alert-box err',
      text: `Última tentativa (${lastExportStatus.profile || 'todos'}) falhou: ${lastExportStatus.error || 'erro na exportação'}. Entregas válidas anteriores permanecem preservadas.`,
    }));
  } else if (lastExportStatus.status === 'interrupted') {
    out.append(el('div', {
      class: 'alert-box warn',
      text: lastExportStatus.error || 'Última tentativa foi interrompida ao fechar o painel. Entregas válidas anteriores foram preservadas; tente exportar novamente.',
    }));
  } else if (lastExportStatus.status === 'running') {
    out.append(el('div', {
      class: 'alert-box warn',
      text: `Exportação (${lastExportStatus.profile || 'todos'}) em andamento em segundo plano.`,
    }));
  }
}

function renderVideoDeliveryPayload(containerSel, data, dir, mode) {
  const out = $(containerSel);
  out.innerHTML = '';
  renderLastAttemptBanner(out, data.lastExportStatus, mode);

  if (data.index) {
    out.append(el('p', {
      class: 'muted',
      text: `Índice: ${data.index.completedCount}/${data.index.profileCount} entrega(s) válida(s) — ${data.index.overallStatus}`,
    }));
  }
  const cacheBust = data.lastExportStatus?.finishedAt ? `&v=${encodeURIComponent(data.lastExportStatus.finishedAt)}` : '';
  for (const prof of (data.profiles || [])) {
    const id = prof.profileId;
    const base = `/media?dir=${encodeURIComponent(dir)}&profile=${encodeURIComponent(id)}`;
    const valid = data.index ? (data.index.profiles.find((p) => p.profileId === id) || {}) : {};
    const actions = [
      el('a', { href: base + '&kind=video', download: '', text: 'Baixar MP4' }),
      el('a', { href: base + '&kind=srt', download: '', text: 'Baixar SRT' }),
      el('a', { href: base + '&kind=narration', download: '', text: 'Baixar narração TXT' }),
    ];
    if (mode === 'video') {
      actions.push(el('button', {
        class: 'secondary',
        text: 'Reexportar este perfil',
        onclick: () => { $('#output-dir').value = dir; startExport(id); },
      }));
    } else {
      actions.push(el('button', {
        class: 'secondary',
        text: 'Reexportar Motion neste perfil',
        onclick: () => { $('#m-output-dir').value = dir; $('#m-profile-select').value = id; mExport(); },
      }));
    }
    const card = el('div', { class: 'profile-card' }, [
      el('strong', { text: id + ' ' }),
      el('span', { class: 'badge ok', text: 'entrega válida' }),
      valid.lastAttempt && valid.lastAttempt.status === 'failed'
        ? el('span', { class: 'badge err', text: 'última tentativa falhou: ' + (valid.lastAttempt.failureCode || valid.lastAttempt.error || '') })
        : null,
      el('video', { controls: '', preload: 'metadata', src: base + '&kind=video' + cacheBust }),
      el('div', {}, actions),
    ]);
    out.append(card);
  }
  if (!(data.profiles || []).length && !data.lastExportStatus) {
    out.append(el('p', { class: 'muted', text: 'Nenhuma entrega promovida nesta pasta ainda.' }));
  }
}

async function loadDelivery() {
  const dir = $('#delivery-dir').value.trim();
  if (!dir) { toast('Informe a pasta de entrega.'); return; }
  const out = $('#delivery-output');
  out.innerHTML = '<p class="muted">Abrindo entrega…</p>';
  try {
    const data = await api('/api/delivery?dir=' + encodeURIComponent(dir));
    renderVideoDeliveryPayload('#delivery-output', data, dir, 'video');
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
async function loadCProfiles() {
  const project = $('#c-project-select').value;
  if (!project) { toast('Selecione um projeto.'); return; }
  cdraft.project = project;
  const data = await api('/api/profiles?project=' + encodeURIComponent(project) + '&module=carousel');
  cCatalog = data.listing.profiles || [];
  renderCProfileOptions();
  toast(`${data.listing.compatibleProfiles.length} destino(s) compatível(is) com Carrossel.`);
}

function renderCProfileOptions() {
  const sel = $('#c-profile-select');
  const compat = cCatalog.filter((x) => x.localExportCarousel);
  sel.innerHTML = '';
  if (!compat.length) {
    sel.append(el('option', { value: cdraft?.profile || '', text: 'Nenhum perfil 1:1 permitido neste projeto' }));
    $('#c-profile-info').textContent = 'Nenhum perfil de imagem 1:1 permitido pela allowlist deste projeto.';
    return;
  }
  for (const p of compat) {
    sel.append(el('option', { value: p.id, text: `${p.id} — ${p.width}×${p.height} (${p.network})` }));
  }
  if (compat.some((p) => p.id === cdraft.profile)) {
    sel.value = cdraft.profile;
  } else {
    cdraft.profile = compat[0].id;
    sel.value = cdraft.profile;
  }
  const active = compat.find((p) => p.id === sel.value);
  $('#c-profile-info').textContent = active
    ? `${active.id}: ${active.width}×${active.height} — permitido pela allowlist`
    : '';
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
  if ($('#c-profile-select').value) cdraft.profile = $('#c-profile-select').value;
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
      el('td', { text: m.id }),
      el('td', { text: m.type }),
      el('td', { text: m.path }),
      el('td', {}, el('input', { type: 'text', value: m.origin || '', oninput: (e) => { m.origin = e.target.value; } })),
      el('td', {}, el('input', { type: 'text', value: m.license || 'pending', oninput: (e) => { m.license = e.target.value; } })),
      el('td', {}, el('button', {
        class: 'secondary',
        text: 'Remover',
        onclick: () => { cdraft.media.splice(i, 1); renderCMedia(); renderCCards(); },
      })),
    ]));
  });
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
  cdraft.cards.push({ id: `card-${n}`, title: 'Novo card', body: '', mediaId: cdraft.media[0]?.id });
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
      out.append(el('div', {
        text: `${String(c.order).padStart(2, '0')} ${c.id}: ${c.title}` + (c.overflow ? '  [EXCEDE ÁREA — ajuste o texto]' : ''),
        class: c.overflow ? 'badge err' : '',
      }));
    }
    if (r.overflowCards && r.overflowCards.length) {
      out.append(el('p', { class: 'badge err', text: 'Cards a ajustar: ' + r.overflowCards.join(', ') }));
    }
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

async function cExport() {
  syncCFields();
  const outputDir = $('#c-output-dir').value.trim();
  if (!outputDir) { toast('Crie um trabalho ou informe a pasta de entrega.'); return; }
  const status = $('#c-export-status');
  status.innerHTML = '<p class="muted">Exportando carrossel…</p>';
  try {
    const d = await post('/api/export', {
      request: cdraft,
      outputDir,
      kind: 'carousel',
      profile: cdraft.profile,
      workId: currentWork ? currentWork.id : undefined,
    });
    cPoll(d.jobId, outputDir);
  } catch (err) {
    status.innerHTML = '';
    status.append(el('div', { class: 'alert-box err', text: 'Erro: ' + err.message }));
  }
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
    if (d.status !== 'completed') status.append(el('div', { class: 'alert-box err', text: r.error || JSON.stringify(r) }));
    $('#c-delivery-dir').value = outputDir;
    loadCDelivery();
    loadWorks().catch(() => {});
  };
  tick();
}

function renderCarouselDeliveryPayload(d, dir) {
  const out = $('#c-delivery-output');
  out.innerHTML = '';
  renderLastAttemptBanner(out, d.lastExportStatus, 'carousel');

  if (d.index) {
    const lv = d.index.lastValidDelivery;
    const la = d.index.lastAttempt;
    out.append(el('p', {}, [
      lv ? el('span', { class: 'badge ok', text: 'entrega válida preservada' }) : el('span', { class: 'badge muted', text: 'sem entrega válida' }),
      la && la.status === 'failed'
        ? el('span', { class: 'badge err', text: 'última tentativa falhou' })
        : la && la.status === 'interrupted'
          ? el('span', { class: 'badge warn', text: 'última tentativa interrompida' })
          : null,
    ]));
  }
  if (!d.manifest) {
    if (!d.lastExportStatus) out.append(el('p', { class: 'muted', text: 'Nenhum manifesto de carrossel nesta pasta ainda.' }));
    return;
  }
  const cacheBust = d.lastExportStatus?.finishedAt ? `&v=${encodeURIComponent(d.lastExportStatus.finishedAt)}` : '';
  const base = `/media?dir=${encodeURIComponent(dir)}`;
  out.append(el('p', {}, el('a', { href: base + '&kind=zip', download: 'carousel.zip', text: 'Baixar ZIP (carousel.zip)' })));
  d.manifest.cards.forEach((c, i) => {
    out.append(el('div', { class: 'profile-card' }, [
      el('strong', { text: `${String(c.order).padStart(2, '0')} ${c.id} ` }),
      el('img', { class: 'card-thumb', src: `${base}&kind=card&index=${i}${cacheBust}`, alt: c.id }),
      el('div', {}, el('a', { href: `${base}&kind=card&index=${i}`, download: c.file, text: 'Baixar ' + c.file })),
    ]));
  });
}

async function loadCDelivery() {
  const dir = $('#c-delivery-dir').value.trim();
  if (!dir) { toast('Informe a pasta de entrega.'); return; }
  const out = $('#c-delivery-output');
  out.innerHTML = '<p class="muted">Abrindo entrega…</p>';
  try {
    const d = await api('/api/carousel-delivery?dir=' + encodeURIComponent(dir));
    renderCarouselDeliveryPayload(d, dir);
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

function renderCAll() { renderCFields(); renderCMedia(); renderCCards(); }

// ================= Motion (contorno animado multi-cena) =================
function currentMScene() {
  if (!mreq || !mreq.scenes || !mreq.scenes.length) return null;
  return mreq.scenes.find((s) => s.id === mCurrentSceneId) || mreq.scenes[0];
}

function mEffectFor(sceneId) {
  if (!mplan || !Array.isArray(mplan.effects) || !sceneId) return null;
  return mplan.effects.find((e) => e.sceneId === sceneId) || null;
}

function ensureCurrentMEffect() {
  const scene = currentMScene();
  if (!scene || !mplan) return null;
  if (scene.motionIntent === 'slow-zoom') {
    toast(`Cena "${scene.id}" usa slow-zoom (incompatível com contorno animado). Altere para "none" na aba Vídeos.`);
    return null;
  }
  let eff = mEffectFor(scene.id);
  if (!eff) {
    eff = {
      sceneId: scene.id,
      region: { x: 0.1, y: 0.3, w: 0.8, h: 0.15 },
      color: '#FFD700',
      thickness: 6,
      startMs: Math.min(500, Math.max(0, scene.durationMs - 500)),
      endMs: Math.min(3000, scene.durationMs),
      fadeInMs: 200,
      fadeOutMs: 200,
    };
    mplan.effects.push(eff);
    populateMScenes();
    renderMotionEffectsSummary();
  }
  return eff;
}

function removeCurrentMEffect() {
  if (!mplan || !mCurrentSceneId) return;
  const idx = mplan.effects.findIndex((e) => e.sceneId === mCurrentSceneId);
  if (idx < 0) return;
  if (mplan.effects.length <= 1) {
    toast('O MotionPlan exige ao menos 1 cena com contorno.');
    return;
  }
  mplan.effects.splice(idx, 1);
  afterMPlan();
  toast(`Contorno removido da cena "${mCurrentSceneId}". Demais cenas preservadas.`);
}

function syncMotionFromDraft() {
  if (!draft) return;
  mreq = JSON.parse(JSON.stringify(draft));
  if (!mplan) {
    const first = (mreq.scenes || []).find((s) => s.motionIntent !== 'slow-zoom') || mreq.scenes[0];
    mplan = {
      schemaVersion: 1,
      requestId: mreq.id,
      effects: first ? [{
        sceneId: first.id,
        region: { x: 0.1, y: 0.3, w: 0.8, h: 0.15 },
        color: '#FFD700',
        thickness: 6,
        startMs: 500,
        endMs: Math.min(3000, first.durationMs || 4000),
        fadeInMs: 200,
        fadeOutMs: 200,
      }] : [],
    };
  }
  mplan.requestId = mreq.id;
  if (!mCurrentSceneId || !(mreq.scenes || []).some((s) => s.id === mCurrentSceneId)) {
    mCurrentSceneId = (mplan.effects[0]?.sceneId) || (mreq.scenes[0]?.id) || null;
  }
  mImg = null;
  populateMProfiles();
  afterMPlan();
}

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
  mStandaloneOverride = true;
  mreq = JSON.parse(JSON.stringify(ex.request));
  mCurrentSceneId = mreq.scenes[0]?.id || null;
  $('#m-plan-path').value = '.workspace/tmp/video-studio/drafts/' + mreq.id + '.motion.json';
  $('#m-output-dir').value = '.workspace/archives/video-studio/' + mreq.id;
  const planPath = ex.path.replace('.video-request.json', '.motion-plan.json');
  api('/api/draft/load?path=' + encodeURIComponent(planPath))
    .then((d) => { mplan = d.request; mCurrentSceneId = mplan.effects[0]?.sceneId || mreq.scenes[0]?.id; afterMPlan(); })
    .catch(() => {
      mplan = {
        schemaVersion: 1,
        requestId: mreq.id,
        effects: [{ sceneId: mreq.scenes[0].id, region: { x: 0.1, y: 0.3, w: 0.8, h: 0.15 }, color: '#FFD700', thickness: 6, startMs: 500, endMs: 3000 }],
      };
      afterMPlan();
    });
  populateMProfiles();
}

function renderMotionEffectsSummary() {
  const box = $('#m-effects-summary');
  box.innerHTML = '';
  if (!mplan || !mplan.effects.length) {
    box.append(el('span', { class: 'muted', text: 'Nenhum contorno configurado.' }));
    return;
  }
  box.append(el('span', { class: 'muted', text: `Cenas com contorno (${mplan.effects.length}): ` }));
  for (const eff of mplan.effects) {
    const active = eff.sceneId === mCurrentSceneId;
    box.append(el('button', {
      type: 'button',
      class: 'effect-pill' + (active ? ' active' : ''),
      text: `${eff.sceneId} (${eff.startMs}–${eff.endMs}ms ${eff.color})`,
      onclick: () => {
        mCurrentSceneId = eff.sceneId;
        mImg = null;
        afterMPlan();
      },
    }));
  }
}

function afterMPlan() {
  populateMScenes();
  const e = mEffectFor(mCurrentSceneId);
  if (e) {
    $('#m-start').value = e.startMs;
    $('#m-end').value = e.endMs;
    $('#m-color').value = e.color;
    $('#m-thickness').value = e.thickness;
  }
  renderMotionEffectsSummary();
  drawMotionCanvas();
  updateMRegionInfo();
}

function populateMScenes() {
  const sel = $('#m-scene-select');
  sel.innerHTML = '';
  if (!mreq || !mreq.scenes) return;
  for (const s of mreq.scenes) {
    const hasEff = Boolean(mEffectFor(s.id));
    const zoomNote = s.motionIntent === 'slow-zoom' ? ' [zoom — altere para none]' : '';
    const effNote = hasEff ? ' [com contorno]' : '';
    sel.append(el('option', { value: s.id, text: `${s.id} (${s.durationMs}ms)${effNote}${zoomNote}` }));
  }
  if (!mCurrentSceneId || !mreq.scenes.some((s) => s.id === mCurrentSceneId)) {
    mCurrentSceneId = mreq.scenes[0]?.id || null;
  }
  if (mCurrentSceneId) sel.value = mCurrentSceneId;
  sel.onchange = () => {
    mCurrentSceneId = sel.value;
    mImg = null;
    afterMPlan();
  };
}

function populateMProfiles() {
  const sel = $('#m-profile-select');
  const prev = sel.value;
  sel.innerHTML = '';
  const list = (mreq && mreq.profiles && mreq.profiles.length)
    ? mreq.profiles
    : catalog.filter((p) => p.localExportMotion).map((p) => p.id);
  for (const p of list) sel.append(el('option', { value: p, text: p }));
  if (list.includes(prev)) sel.value = prev;
}

function currentMedia() {
  const s = currentMScene();
  if (!s || !mreq) return null;
  return mreq.media.find((m) => m.id === s.mediaId) || null;
}

function drawMotionCanvas() {
  const cv = $('#m-canvas');
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, cv.width, cv.height);
  if (!mreq || !mplan) return;
  const media = currentMedia();
  if (!media) return;
  if (!mImg || mImg._src !== media.path) {
    mImg = new Image();
    mImg._src = media.path;
    mImg.onload = () => drawMotionCanvas();
    mImg.src = '/source-media?path=' + encodeURIComponent(media.path);
    return;
  }
  const scale = Math.min(cv.width / mImg.width, cv.height / mImg.height);
  const dw = mImg.width * scale;
  const dh = mImg.height * scale;
  ctx.drawImage(mImg, (cv.width - dw) / 2, (cv.height - dh) / 2, dw, dh);
  const eff = mEffectFor(mCurrentSceneId);
  if (eff && eff.region) {
    const r = eff.region;
    ctx.strokeStyle = eff.color || '#FFD700';
    ctx.lineWidth = 3;
    ctx.strokeRect(r.x * cv.width, r.y * cv.height, r.w * cv.width, r.h * cv.height);
  }
}

function updateMRegionInfo() {
  const scene = currentMScene();
  const e = mEffectFor(mCurrentSceneId);
  if (!scene) { $('#m-region-info').textContent = 'Nenhuma cena selecionada.'; return; }
  if (scene.motionIntent === 'slow-zoom') {
    $('#m-region-info').textContent = `Cena "${scene.id}" está com slow-zoom; altere o movimento para "none" na aba Vídeos para aplicar contorno.`;
    return;
  }
  if (!e) {
    $('#m-region-info').textContent = `Cena "${scene.id}" (${scene.durationMs}ms) ainda sem contorno. Arraste na imagem ou clique em "Ativar contorno nesta cena".`;
    return;
  }
  const r = e.region;
  $('#m-region-info').textContent = `Região (${e.sceneId}): x=${r.x.toFixed(2)} y=${r.y.toFixed(2)} w=${r.w.toFixed(2)} h=${r.h.toFixed(2)} — contorno de ${e.startMs}ms a ${e.endMs}ms (${e.color}, ${e.thickness}px).`;
}

function canvasFraction(ev) {
  const cv = $('#m-canvas');
  const rect = cv.getBoundingClientRect();
  return { x: (ev.clientX - rect.left) / rect.width, y: (ev.clientY - rect.top) / rect.height };
}

function initMotionCanvas() {
  const cv = $('#m-canvas');
  cv.addEventListener('pointerdown', (ev) => {
    if (!ensureCurrentMEffect()) return;
    mDrag = canvasFraction(ev);
    cv.setPointerCapture(ev.pointerId);
  });
  cv.addEventListener('pointermove', (ev) => {
    if (!mDrag) return;
    const eff = mEffectFor(mCurrentSceneId);
    if (!eff) return;
    const p = canvasFraction(ev);
    const x = Math.max(0, Math.min(mDrag.x, p.x));
    const y = Math.max(0, Math.min(mDrag.y, p.y));
    const w = Math.max(0.02, Math.min(1 - x, Math.abs(p.x - mDrag.x)));
    const h = Math.max(0.02, Math.min(1 - y, Math.abs(p.y - mDrag.y)));
    eff.region = { x, y, w, h };
    drawMotionCanvas();
    updateMRegionInfo();
  });
  cv.addEventListener('pointerup', () => { mDrag = null; renderMotionEffectsSummary(); });
  for (const [id, key] of [['m-start', 'startMs'], ['m-end', 'endMs'], ['m-thickness', 'thickness']]) {
    $('#' + id).addEventListener('input', (e) => {
      const eff = ensureCurrentMEffect();
      if (!eff) return;
      eff[key] = Number(e.target.value);
      updateMRegionInfo();
      renderMotionEffectsSummary();
    });
  }
  $('#m-color').addEventListener('input', (e) => {
    const eff = ensureCurrentMEffect();
    if (!eff) return;
    eff.color = e.target.value;
    drawMotionCanvas();
    updateMRegionInfo();
    renderMotionEffectsSummary();
  });
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
  mplan = d.request;
  mCurrentSceneId = mplan.effects[0]?.sceneId || mCurrentSceneId;
  afterMPlan();
  toast('Plano reaberto.');
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
      if (p.status !== 'compiled') {
        out.append(el('div', { class: 'alert-box err', text: `${p.profileId}: ${p.failureCode} ${(p.errors || []).map((e) => e.message).join('; ')}` }));
        continue;
      }
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
  if (!outputDir) { toast('Crie um trabalho ou informe a pasta de entrega.'); return; }
  const status = $('#m-export-status');
  status.innerHTML = '<p class="muted">Exportando com Motion…</p>';
  try {
    const profile = $('#m-profile-select').value;
    const d = await post('/api/export', {
      request: mreq,
      outputDir,
      profile: profile || undefined,
      kind: 'video',
      motionPlan: mplan,
      workId: (!mStandaloneOverride && currentWork) ? currentWork.id : undefined,
    });
    mPoll(d.jobId, outputDir);
  } catch (err) {
    status.innerHTML = '';
    status.append(el('div', { class: 'alert-box err', text: 'Erro: ' + err.message }));
  }
}

function mPoll(jobId, outputDir) {
  if (mPollTimer) clearTimeout(mPollTimer);
  const tick = async () => {
    const d = await api('/api/export/status?job=' + jobId);
    const status = $('#m-export-status');
    if (d.status === 'running') { status.innerHTML = '<p class="muted">Exportando… (segundo plano)</p>'; mPollTimer = setTimeout(tick, 1200); return; }
    status.innerHTML = '';
    status.append(el('p', {}, el('span', { class: d.status === 'completed' ? 'badge ok' : 'badge err', text: d.status })));
    await loadMDelivery(outputDir);
    loadWorks().catch(() => {});
  };
  tick();
}

async function loadMDelivery(dirOverride) {
  const dir = dirOverride || $('#m-output-dir').value.trim();
  if (!dir) { toast('Informe a pasta de entrega Motion.'); return; }
  const data = await api('/api/delivery?dir=' + encodeURIComponent(dir));
  renderVideoDeliveryPayload('#m-delivery-output', data, dir, 'motion');
}

async function initCarousel() {
  cdraft = emptyCarousel();
  await loadCExamples();
  renderCAll();
  $('#c-btn-load-profiles').addEventListener('click', () => loadCProfiles().catch((e) => toast(e.message)));
  $('#c-project-select').addEventListener('change', () => {
    if ($('#c-project-select').value) loadCProfiles().catch((e) => toast(e.message));
  });
  $('#c-profile-select').addEventListener('change', syncCFields);
  $('#c-btn-load-example').addEventListener('click', loadCExample);
  $('#c-btn-save-draft').addEventListener('click', () => saveCDraft().catch((e) => toast(e.message)));
  $('#c-btn-open-draft').addEventListener('click', () => openCDraft().catch((e) => toast(e.message)));
  $('#c-btn-save-work').addEventListener('click', () => saveWork().catch((e) => toast(e.message)));
  $('#c-btn-scan-work-media').addEventListener('click', () => {
    const dir = currentWork ? currentWork.paths.mediaDir : $('#c-media-folder').value.trim();
    scanMediaInto(cdraft, dir, ['image'], () => { renderCMedia(); renderCCards(); }).catch((e) => toast(e.message));
  });
  $('#c-btn-scan-media').addEventListener('click', () => {
    scanMediaInto(cdraft, $('#c-media-folder').value.trim(), ['image'], () => { renderCMedia(); renderCCards(); }).catch((e) => toast(e.message));
  });
  $('#c-btn-generate-media').addEventListener('click', () => generateCMedia().catch((e) => toast(e.message)));
  $('#c-btn-add-card').addEventListener('click', addCCard);
  $('#c-btn-preview').addEventListener('click', cPreview);
  $('#c-btn-export').addEventListener('click', cExport);
  $('#c-btn-load-delivery').addEventListener('click', () => loadCDelivery().catch((e) => toast(e.message)));
}

async function initMotion() {
  await loadMExamples();
  initMotionCanvas();
  $('#m-btn-load-example').addEventListener('click', loadMExample);
  $('#m-btn-sync-work').addEventListener('click', () => {
    mStandaloneOverride = false;
    syncDraftFields();
    syncMotionFromDraft();
    toast('Cenas do trabalho sincronizadas no Motion.');
  });
  $('#m-btn-save-work').addEventListener('click', () => saveWork().catch((e) => toast(e.message)));
  $('#m-btn-save-plan').addEventListener('click', () => saveMPlan().catch((e) => toast(e.message)));
  $('#m-btn-open-plan').addEventListener('click', () => openMPlan().catch((e) => toast(e.message)));
  $('#m-btn-enable-scene').addEventListener('click', () => { if (ensureCurrentMEffect()) afterMPlan(); });
  $('#m-btn-remove-scene').addEventListener('click', removeCurrentMEffect);
  $('#m-btn-preview').addEventListener('click', mPreview);
  $('#m-btn-export').addEventListener('click', mExport);
  $('#m-btn-load-delivery').addEventListener('click', () => loadMDelivery().catch((e) => toast(e.message)));
}

async function init() {
  draft = emptyDraft();
  await loadReadiness();
  await loadProjects();
  await loadWorks();
  await loadExamples();
  renderAll();

  $('#readiness-banner').addEventListener('click', () => {
    const details = $('#readiness-details');
    details.hidden = !details.hidden;
  });
  $('#btn-refresh-readiness').addEventListener('click', () => loadReadiness());

  // Sugestão automática de IDs em kebab-case nos formulários
  let workIdTouched = false;
  $('#work-id').addEventListener('input', () => { workIdTouched = true; updateWorkPathsPreview(); });
  $('#work-name').addEventListener('input', (e) => {
    if (!workIdTouched) {
      $('#work-id').value = slugifyKebab(e.target.value);
      updateWorkPathsPreview();
    }
  });
  updateWorkPathsPreview();

  let projIdTouched = false;
  $('#proj-id').addEventListener('input', () => {
    projIdTouched = true;
    const v = $('#proj-id').value.trim();
    if (v) {
      $('#proj-theme').value = v;
      $('#proj-asset-root').value = `.workspace/studio/projects/${v}/assets`;
    }
  });
  $('#proj-name').addEventListener('input', (e) => {
    if (!projIdTouched) {
      const slug = slugifyKebab(e.target.value);
      $('#proj-id').value = slug;
      if (slug) {
        $('#proj-theme').value = slug;
        $('#proj-asset-root').value = `.workspace/studio/projects/${slug}/assets`;
      }
    }
  });

  $('#btn-create-project').addEventListener('click', createProject);
  $('#btn-create-work').addEventListener('click', createWork);
  $('#btn-demo-marca-salao').addEventListener('click', () => startGuidedDemo('marca-salao'));
  $('#btn-demo-multitrack').addEventListener('click', () => startGuidedDemo('multitrack-hub'));
  $('#btn-save-work').addEventListener('click', () => saveWork().catch((e) => toast(e.message)));
  $('#btn-work-home').addEventListener('click', () => setMode('home'));

  $('#btn-load-profiles').addEventListener('click', () => loadProfiles().catch((e) => toast(e.message)));
  $('#project-select').addEventListener('change', () => {
    if ($('#project-select').value) loadProfiles().catch((e) => toast(e.message));
  });
  $('#video-show-all-profiles').addEventListener('change', renderProfiles);
  $('#btn-load-example').addEventListener('click', loadExample);
  $('#btn-save-draft').addEventListener('click', () => saveDraft().catch((e) => toast(e.message)));
  $('#btn-open-draft').addEventListener('click', () => openDraft().catch((e) => toast(e.message)));
  $('#btn-save-video-work').addEventListener('click', () => saveWork().catch((e) => toast(e.message)));
  $('#btn-scan-work-media').addEventListener('click', () => {
    const dir = currentWork ? currentWork.paths.mediaDir : $('#media-folder').value.trim();
    scanMediaInto(draft, dir, ['image', 'video'], () => { renderMedia(); renderScenes(); }).catch((e) => toast(e.message));
  });
  $('#btn-scan-media').addEventListener('click', () => {
    scanMediaInto(draft, $('#media-folder').value.trim(), ['image', 'video'], () => { renderMedia(); renderScenes(); }).catch((e) => toast(e.message));
  });
  $('#btn-generate-media').addEventListener('click', () => generateMedia().catch((e) => toast(e.message)));
  $('#btn-add-scene').addEventListener('click', addScene);
  $('#btn-preview').addEventListener('click', preview);
  $('#btn-export').addEventListener('click', () => startExport());
  $('#btn-load-delivery').addEventListener('click', () => loadDelivery().catch((e) => toast(e.message)));

  $('#mode-home-btn').addEventListener('click', () => setMode('home'));
  $('#mode-video-btn').addEventListener('click', () => setMode('video'));
  $('#mode-carousel-btn').addEventListener('click', () => setMode('carousel'));
  $('#mode-motion-btn').addEventListener('click', () => setMode('motion'));

  await initCarousel();
  await initMotion();
  setMode('home');
}

init();
