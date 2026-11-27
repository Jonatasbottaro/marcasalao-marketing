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
let reviewState = null;
let reviewSyncSeq = 0;

let activeVideoProfileId = null;
let selectedSceneIndex = 0;
let vFrameMedia = { key: null, element: null, width: 0, height: 0, ready: false, error: false, type: null };
let vFrameDrag = false;
let vFrameInfoSeq = 0;
let vFrameInfoTimer = null;
let vLastFrameInfo = null;
let vPreviewPollTimer = null;
let vPreviewStatusTimer = null;
let vPreviewStatusSeq = 0;
let vLastPreviewData = null;
let vLoadedPreviewUrl = null;
let pendingPreviewSeekSec = null;

function isAstryxHomeActive() {
  return Boolean(window.__studioAstryxHomeActive) || document.getElementById('home-astryx-root')?.dataset?.astryxReady === '1';
}

function homeLegacyRoot() {
  return document.getElementById('home-legacy-root');
}

function homeEl(sel) {
  const root = homeLegacyRoot();
  if (!root || isAstryxHomeActive()) return null;
  return root.querySelector(sel);
}

function isAstryxQueueActive() {
  return Boolean(window.__studioAstryxQueueActive) || document.getElementById('queue-astryx-root')?.dataset?.astryxReady === '1';
}

function queueLegacyRoot() {
  return document.getElementById('queue-legacy-root');
}

function queueEl(sel) {
  const root = queueLegacyRoot();
  if (!root || isAstryxQueueActive()) return null;
  return root.querySelector(sel);
}
let mVideoMedia = { key: null, canvas: null, ready: false, error: false };

async function apiDetailed(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ ok: false, error: 'resposta ilegível' }));
  return { status: res.status, ok: res.ok && data.ok !== false, data };
}

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
    return { ok: true, readiness: r };
  } catch (err) {
    pill.textContent = 'Erro ao verificar ambiente';
    pill.className = 'readiness-pill err';
    box.hidden = false;
    box.textContent = err.message;
    return { ok: false, error: err.message };
  }
}

// ---- Navegação entre abas ----
function setMode(mode) {
  $('#mode-home').hidden = mode !== 'home';
  $('#mode-video').hidden = mode !== 'video';
  $('#mode-carousel').hidden = mode !== 'carousel';
  $('#mode-motion').hidden = mode !== 'motion';
  $('#mode-review').hidden = mode !== 'review';
  $('#mode-queue').hidden = mode !== 'queue';
  $('#mode-connections').hidden = mode !== 'connections';
  $('#mode-home-btn').classList.toggle('active', mode === 'home');
  $('#mode-video-btn').classList.toggle('active', mode === 'video');
  $('#mode-carousel-btn').classList.toggle('active', mode === 'carousel');
  $('#mode-motion-btn').classList.toggle('active', mode === 'motion');
  $('#mode-review-btn').classList.toggle('active', mode === 'review');
  $('#mode-queue-btn').classList.toggle('active', mode === 'queue');
  $('#mode-connections-btn').classList.toggle('active', mode === 'connections');
  if (mode === 'motion') {
    if (currentWork && !mStandaloneOverride) {
      syncDraftFields();
      syncMotionFromDraft();
    }
    drawMotionCanvas();
  }
  if (mode === 'review' && currentWork) {
    loadReviewOverview().catch((e) => toast(e.message));
  }
  if (mode === 'home') {
    loadWorks().catch(() => {});
  }
  if (mode === 'queue') {
    loadQueue().catch((e) => toast(e.message));
  }
  if (mode === 'connections') {
    loadConnections().catch((e) => toast(e.message));
  }
}

// ---- Projetos e Cadastro ----
async function renderProjectProfileBoxes() {
  if (isAstryxHomeActive()) return;
  const box = homeEl('#proj-profiles-boxes');
  if (!box || box.childElementCount) return;
  const data = await api('/api/profiles');
  const defaults = new Set(['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts', 'instagram-feed-image-square']);
  for (const p of data.listing.profiles) {
    const mods = (p.compatibleModules || []).join('/') || 'sem render local';
    const label = `${p.id} (${p.aspectRatio} ${p.width}×${p.height} — ${mods})`;
    const chk = el('input', { type: 'checkbox', value: p.id });
    if (defaults.has(p.id)) chk.checked = true;
    box.append(el('label', { class: 'inline-check' }, chk, ` ${label}`));
  }
}

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

  const workProj = homeEl('#work-project');
  if (workProj) fillSelect(workProj, workProj.value || (allProjects[0]?.path || ''));
  fillSelect($('#project-select'), draft?.project);
  fillSelect($('#c-project-select'), cdraft?.project);

  const tbody = homeEl('#projects-table tbody');
  if (!tbody) return;
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
  if (isAstryxHomeActive()) return;
  const id = (homeEl('#proj-id')?.value || '').trim();
  const name = (homeEl('#proj-name')?.value || '').trim();
  const locale = (homeEl('#proj-locale')?.value || '').trim() || 'pt-BR';
  const timezone = (homeEl('#proj-tz')?.value || '').trim() || 'America/Sao_Paulo';
  const brandTheme = (homeEl('#proj-theme')?.value || '').trim() || id;
  const assetRoot = (homeEl('#proj-asset-root')?.value || '').trim() || `.workspace/studio/projects/${id}/assets`;
  const root = homeLegacyRoot();
  const outputProfiles = root
    ? Array.from(root.querySelectorAll('#proj-profiles-boxes input[type="checkbox"]:checked')).map((cb) => cb.value)
    : [];

  const feedback = homeEl('#proj-create-feedback');
  if (!feedback) return;
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
        requireApprovedBriefing: Boolean(homeEl('#proj-pol-briefing')?.checked),
        requireApprovedScript: Boolean(homeEl('#proj-pol-script')?.checked),
        prohibitPersonalData: Boolean(homeEl('#proj-pol-pii')?.checked),
        requireFunctionalEvidence: Boolean(homeEl('#proj-pol-evidence')?.checked),
      },
      outputProfiles,
    });
    await loadProjects();
    const workProj = homeEl('#work-project');
    if (workProj) workProj.value = data.path;
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
  const cleanEl = $('#work-captions-clean');
  if (cleanEl) cleanEl.checked = currentWork.captionsMode === 'clean';
}

function updateWorkPathsPreview() {
  const input = homeEl('#work-id');
  const previewEl = homeEl('#work-paths-preview');
  if (!input || !previewEl) return;
  const id = input.value.trim() || '<id-do-trabalho>';
  previewEl.textContent =
    `Caminhos automáticos em .workspace/studio/works/${id}/ (rascunhos/, media/ compartilhada e deliveries/).`;
}

const selectedBatchWorks = new Set();
let lastSavedWorkSnapshot = null;

function updateBatchSelectionCount() {
  const span = homeEl('#works-batch-count');
  if (span) span.textContent = `${selectedBatchWorks.size} selecionado(s)`;
}

function hasUnsavedWorkChanges() {
  if (!currentWork || !lastSavedWorkSnapshot) return false;
  syncDraftFields();
  syncCFields();
  const currentSnap = JSON.stringify({
    videoRequest: draft,
    carouselRequest: cdraft,
    motionPlan: mplan,
    captionsMode: ($('#work-captions-clean')?.checked) ? 'clean' : 'burned',
  });
  return currentSnap !== lastSavedWorkSnapshot;
}

async function loadWorks() {
  if (isAstryxHomeActive()) {
    window.__studioAstryxRefresh?.();
    return;
  }
  const data = await api('/api/works');
  const tbody = homeEl('#works-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const works = data.works || [];
  if (!works.length) {
    tbody.append(el('tr', {}, el('td', { colspan: '9', class: 'muted', text: 'Nenhum trabalho criado ainda. Use a demonstração guiada ou crie um trabalho abaixo.' })));
    updateBatchSelectionCount();
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
    const chk = el('input', {
      type: 'checkbox',
      class: 'work-select-cb',
      'data-work-id': w.id,
      onchange: () => {
        if (chk.checked) selectedBatchWorks.add(w.id);
        else selectedBatchWorks.delete(w.id);
        updateBatchSelectionCount();
      },
    });
    chk.checked = selectedBatchWorks.has(w.id);
    tbody.append(el('tr', {}, [
      el('td', {}, chk),
      el('td', { text: w.id }),
      el('td', { text: w.name }),
      el('td', { text: w.projectId || w.project }),
      el('td', {}, mk(s.videoValidCount, s.videoLastStatus)),
      el('td', {}, mk(s.carouselValid, s.carouselLastStatus)),
      el('td', {}, mk(s.motionValidCount, s.motionLastStatus)),
      el('td', { text: (w.updatedAt || '').replace('T', ' ').replace('Z', '') }),
      el('td', {}, [
        el('button', {
          text: 'Reabrir',
          onclick: () => openWork(w.id).then(() => setMode('video')).catch((e) => toast(e.message)),
        }),
        el('button', {
          class: 'secondary',
          text: 'Salvar como modelo',
          onclick: () => saveWorkAsModel(w.id).catch((e) => toast(e.message)),
        }),
        el('button', {
          class: 'secondary',
          text: 'Duplicar como rascunho',
          onclick: () => duplicateWorkDialog(w.id).catch((e) => toast(e.message)),
        }),
      ]),
    ]));
  }
  updateBatchSelectionCount();
}

function applyOpenedWork(data) {
  currentWork = data.work;
  mStandaloneOverride = false;
  const p = currentWork.paths;

  draft = JSON.parse(JSON.stringify(data.videoRequest));
  cdraft = JSON.parse(JSON.stringify(data.carouselRequest));
  mreq = JSON.parse(JSON.stringify(data.videoRequest));
  mplan = JSON.parse(JSON.stringify(data.motionPlan));
  lastSavedWorkSnapshot = JSON.stringify({
    videoRequest: data.videoRequest,
    carouselRequest: data.carouselRequest,
    motionPlan: data.motionPlan,
  });

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

  const feedbackSelectors = ['#preview-output', '#c-preview-output', '#m-preview-output', '#export-status', '#c-export-status', '#m-export-status', '#r-editorial-feedback'];
  if (!isAstryxReviewPackageActive()) feedbackSelectors.push('#r-package-status');
  for (const sel of feedbackSelectors) {
    const node = $(sel);
    if (node) node.innerHTML = '';
  }

  renderActiveWorkBar();
  selectedSceneIndex = 0;
  activeVideoProfileId = (draft.profiles && draft.profiles[0]) || null;
  vLoadedPreviewUrl = null;
  vLastPreviewData = null;
  vLastFrameInfo = null;
  vFrameMedia = { key: null, element: null, width: 0, height: 0, ready: false, error: false, type: null };
  mVideoMedia = { key: null, canvas: null, ready: false, error: false };
  renderAll();
  refreshVideoPreviewStatus().catch(() => {});
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
  renderReviewPanel(data.review || null, data.packageDelivery || null);
  loadWorks().catch(() => {});
}

async function createWork() {
  if (isAstryxHomeActive()) return;
  const name = (homeEl('#work-name')?.value || '').trim();
  const id = (homeEl('#work-id')?.value || '').trim();
  const project = homeEl('#work-project')?.value || '';
  const template = homeEl('#work-template')?.value || 'marca-salao';
  const feedback = homeEl('#work-create-feedback');
  if (!feedback) return;
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

let openWorkSeq = 0;
async function openWork(workId) {
  const seq = ++openWorkSeq;
  const data = await api('/api/works/open?id=' + encodeURIComponent(workId));
  if (seq !== openWorkSeq) return null;
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
  const captionsMode = ($('#work-captions-clean')?.checked) ? 'clean' : 'burned';
  const payload = {
    workId: currentWork.id,
    videoRequest: draft,
    carouselRequest: cdraft,
    motionPlan: mplan,
    captionsMode,
  };
  const data = await post('/api/works/save', payload);
  currentWork = data.work;
  lastSavedWorkSnapshot = JSON.stringify({
    videoRequest: draft,
    carouselRequest: cdraft,
    motionPlan: mplan,
    captionsMode,
  });
  if (!mStandaloneOverride) mreq = JSON.parse(JSON.stringify(draft));
  renderActiveWorkBar();
  if (!silent) toast('Trabalho salvo em disco com segurança.');
  schedulePreviewStatusRefresh();
  if (!$('#mode-review').hidden) loadReviewOverview().catch(() => {});
  loadWorks().catch(() => {});
  return data;
}

async function startGuidedDemo(brand) {
  if (isAstryxHomeActive()) return;
  const box = homeEl('#demo-feedback');
  if (!box) return;
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
      text: 'Nenhum destino compatível com Vídeo local (9:16 ou 16:9 @30) neste projeto. Marque perfis compatíveis ou "Mostrar perfis fora do recorte".',
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
        renderActiveVideoProfileSelect();
        renderAssemblyTimeline();
        renderFramingEditor();
        schedulePreviewStatusRefresh();
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
      ? el('span', { class: 'badge ok', text: `${p.aspectRatio}@${p.fps} compatível` })
      : el('span', {
          class: 'badge muted',
          text: (p.localExport && p.localExport.video && p.localExport.video.reason)
            ? `sem render local (${p.localExport.video.reason})`
            : 'fora do recorte Vídeo',
        });
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
  for (const id of draft.profiles) {
    const p = catalog.find((x) => x.id === id);
    const label = p ? `${id} — ${p.width}×${p.height} (${p.aspectRatio})` : id;
    sel.append(el('option', { value: id, text: label }));
  }
  if (draft.profiles.includes(current)) sel.value = current;
  renderActiveVideoProfileSelect();
}

function loadDraftStateReset() {
  selectedSceneIndex = 0;
  activeVideoProfileId = (draft && draft.profiles && draft.profiles[0]) || null;
  vLoadedPreviewUrl = null;
  vLastPreviewData = null;
  vLastFrameInfo = null;
  vFrameMedia = { key: null, element: null, width: 0, height: 0, ready: false, error: false, type: null };
  mVideoMedia = { key: null, canvas: null, ready: false, error: false };
}

// ---- Exemplos e Rascunho Vídeo ----
async function loadExamples() {
  const data = await api('/api/examples');
  const sel = $('#example-select');
  sel.innerHTML = '';
  const vids = data.examples.filter((e) => e.kind === 'video');
  for (const ex of vids) sel.append(el('option', { value: ex.path, text: ex.name }));
  sel._examples = vids;

  const tmplSel = homeEl('#work-template');
  if (tmplSel && !isAstryxHomeActive()) {
    Array.from(tmplSel.querySelectorAll('option[data-dynamic-example="1"]')).forEach((opt) => opt.remove());
    for (const ex of vids) {
      const exId = ex.request?.id || ex.name;
      tmplSel.append(el('option', {
        value: `example:${exId}`,
        'data-dynamic-example': '1',
        text: `Pedido exemplo: ${exId} — ${ex.request?.title || ex.name}`,
      }));
    }
  }
}

function loadExample() {
  const sel = $('#example-select');
  const ex = (sel._examples || []).find((e) => e.path === sel.value);
  if (!ex) { toast('Selecione um exemplo.'); return; }
  if (currentWork) {
    currentWork = null;
    renderActiveWorkBar();
  }
  draft = JSON.parse(JSON.stringify(ex.request));
  $('#draft-path').value = '.workspace/tmp/video-studio/drafts/' + draft.id + '.json';
  $('#output-dir').value = '.workspace/archives/video-studio/' + draft.id;
  $('#delivery-dir').value = '.workspace/archives/video-studio/' + draft.id;
  $('#project-select').value = draft.project;
  loadDraftStateReset();
  renderAll();
  loadProfiles();
  refreshVideoPreviewStatus().catch(() => {});
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
  if (currentWork) {
    currentWork = null;
    renderActiveWorkBar();
  }
  draft = data.request;
  $('#project-select').value = draft.project || '';
  loadDraftStateReset();
  renderAll();
  if (draft.project) loadProfiles();
  refreshVideoPreviewStatus().catch(() => {});
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

// ---- Importação de gravação MP4 em blocos (biblioteca do trabalho) ----
function bufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = '';
  const STEP = 0x8000;
  for (let i = 0; i < bytes.length; i += STEP) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + STEP));
  }
  return btoa(bin);
}

async function importRecordingFile(file) {
  if (!currentWork) { toast('Abra um trabalho antes de importar a gravação.'); return; }
  if (!file.name.toLowerCase().endsWith('.mp4')) { toast('A gravação deve ser um arquivo .mp4 (H.264).'); return; }
  const note = $('#recording-import-note');
  const original = note.textContent;
  try {
    note.textContent = `Enviando ${file.name} (${file.size} bytes) em blocos…`;
    const start = await post('/api/works/media/import-video/start', {
      workId: currentWork.id, fileName: file.name, totalBytes: file.size,
      origin: 'imported-manual', license: 'pending',
    });
    const chunkBytes = start.chunkBytes;
    let offset = 0;
    while (offset < file.size) {
      const slice = file.slice(offset, offset + chunkBytes);
      const dataBase64 = bufferToBase64(await slice.arrayBuffer());
      await post('/api/works/media/import-video/chunk', { uploadId: start.uploadId, offset, dataBase64 });
      offset += slice.size;
      note.textContent = `Enviando ${file.name}: ${offset}/${file.size} bytes…`;
    }
    note.textContent = 'Validando conteúdo com FFprobe e promovendo…';
    const finish = await post('/api/works/media/import-video/finish', {
      uploadId: start.uploadId, workId: currentWork.id,
    });
    const v = finish.version;
    if (!draft.media.some((m) => m.id === finish.assetId)) {
      draft.media.push({ id: finish.assetId, path: v.path, type: 'video', origin: v.origin, license: v.license });
    }
    renderMedia();
    renderScenes();
    if (window.StudioMedia && typeof window.StudioMedia.refresh === 'function') {
      window.StudioMedia.refresh().catch(() => {});
    }
    toast(`Gravação importada: ${finish.assetId} (${v.width}×${v.height}, ${v.durationSeconds}s). Selecione-a nas cenas para recortar.`);
  } catch (e) {
    toast('Falha na importação: ' + e.message);
  } finally {
    note.textContent = original;
  }
}

// ---- Cenas Vídeo ----
const NARRATIVE = ['hook', 'context', 'problem', 'demonstration', 'explanation', 'proof', 'transition', 'cta', 'closing'];
const MOTION = ['none', 'slow-zoom'];

function sceneMediaEntry(s) {
  return (draft.media || []).find((m) => m.id === s.mediaId) || null;
}

function assemblyStartMs(index) {
  let acc = 0;
  for (let i = 0; i < index; i++) acc += Number(draft.scenes[i].durationMs) || 0;
  return acc;
}

function fmtMs(ms) {
  const s = (Number(ms) || 0) / 1000;
  return `${s.toFixed(2)}s`;
}

// ---- Editor de cortes por cena (fonte de video) ----
function buildCutEditor(s, i) {
  const media = sceneMediaEntry(s);
  const video = el('video', {
    class: 'cut-player', muted: '', controls: '', preload: 'metadata',
    src: `/source-media?path=${encodeURIComponent(media.path)}`,
    style: 'max-width: 270px; max-height: 240px; background: #000; border-radius: 6px;',
  });
  const info = el('p', { class: 'timeline cut-info' });
  const err = el('p', { class: 'badge err cut-error', hidden: '' });
  const startInput = el('input', {
    type: 'number', min: '0', step: '1', value: s.sourceStartMs ?? 0,
    oninput: (e) => {
      const v = Math.max(0, Math.round(Number(e.target.value) || 0));
      if (v > 0) s.sourceStartMs = v; else delete s.sourceStartMs;
      refresh();
      renderAssemblyTimeline();
      schedulePreviewStatusRefresh();
      if (selectedSceneIndex === i) renderFramingEditor(true);
    },
  });
  const durInput = el('input', {
    type: 'number', min: '1', step: '1', value: s.durationMs,
    oninput: (e) => {
      s.durationMs = Math.max(1, Math.round(Number(e.target.value) || 1));
      refresh();
      renderAssemblyTimeline();
      schedulePreviewStatusRefresh();
    },
  });

  function sourceDurationMs() {
    return Number.isFinite(video.duration) && video.duration > 0 ? Math.round(video.duration * 1000) : null;
  }
  function refresh() {
    const start = s.sourceStartMs || 0;
    const dur = Number(s.durationMs) || 0;
    const avail = sourceDurationMs();
    const a0 = assemblyStartMs(i);
    info.textContent = `Fonte: ${avail != null ? fmtMs(avail) + ' disponíveis' : 'duração desconhecida'} · `
      + `Trecho: ${fmtMs(start)} → ${fmtMs(start + dur)} · Cena: ${fmtMs(dur)} · `
      + `Montagem: ${fmtMs(a0)} → ${fmtMs(a0 + dur)}`;
    let problem = null;
    if (avail != null && start + dur > avail) {
      problem = `Trecho ultrapassa a fonte: fim pedido ${fmtMs(start + dur)} > disponível ${fmtMs(avail)}. Ajuste o início ou a duração.`;
    }
    if (problem) { err.textContent = problem; err.removeAttribute('hidden'); }
    else { err.textContent = ''; err.setAttribute('hidden', ''); }
    // Sincroniza o campo de duração principal da cena.
    const mainDur = document.querySelector(`#scenes-list .scene:nth-child(${i + 1}) .scene-duration`);
    if (mainDur && Number(mainDur.value) !== dur) mainDur.value = dur;
  }

  video.addEventListener('loadedmetadata', refresh);
  video.addEventListener('error', () => {
    err.textContent = 'Não foi possível carregar a fonte registrada. Verifique o arquivo na biblioteca.';
    err.removeAttribute('hidden');
  });
  video.addEventListener('timeupdate', () => {
    const until = Number(video.dataset.playUntil || 0);
    if (until > 0 && video.currentTime * 1000 >= until) {
      video.pause();
      video.dataset.playUntil = '0';
    }
  });

  const markIn = el('button', {
    class: 'secondary', type: 'button', text: 'Marcar entrada',
    onclick: () => {
      const v = Math.round(video.currentTime * 1000);
      if (v > 0) s.sourceStartMs = v; else delete s.sourceStartMs;
      startInput.value = v;
      refresh();
      renderAssemblyTimeline();
      schedulePreviewStatusRefresh();
      if (selectedSceneIndex === i) renderFramingEditor(true);
    },
  });
  const markOut = el('button', {
    class: 'secondary', type: 'button', text: 'Marcar saída',
    onclick: () => {
      const end = Math.round(video.currentTime * 1000);
      s.durationMs = Math.max(1, end - (s.sourceStartMs || 0));
      durInput.value = s.durationMs;
      refresh();
      renderAssemblyTimeline();
      schedulePreviewStatusRefresh();
    },
  });
  const playRange = el('button', {
    class: 'secondary', type: 'button', text: 'Reproduzir trecho',
    onclick: () => {
      video.currentTime = (s.sourceStartMs || 0) / 1000;
      video.dataset.playUntil = String((s.sourceStartMs || 0) + (Number(s.durationMs) || 0));
      video.play().catch(() => {});
    },
  });

  refresh();
  return el('div', { class: 'cut-editor', style: 'margin-top: 6px; padding: 8px; border: 1px dashed var(--line); border-radius: 6px;' }, [
    el('div', { class: 'row', style: 'align-items: flex-start; gap: 10px;' }, [
      video,
      el('div', {}, [
        info,
        err,
        el('div', { class: 'row' }, [markIn, markOut, playRange]),
        el('div', { class: 'row' }, [
          el('label', { text: 'Início na fonte (ms)' }, startInput),
          el('label', { text: 'Duração do trecho (ms)' }, durInput),
        ]),
        el('p', { class: 'muted', text: 'A saída da fonte é derivada: início + duração. A posição na montagem vem da ordem das cenas.' }),
      ]),
    ]),
  ]);
}

function clamp01(v) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0.5;
}

function clampZoom(v) {
  const n = Math.round(Number(v));
  return Number.isFinite(n) ? Math.max(100, Math.min(300, n)) : 100;
}

function getVideoProfileMeta(profileId) {
  if (!profileId) return null;
  const found = (catalog || []).find((p) => p.id === profileId);
  if (found && found.width && found.height) return found;
  const isHoriz = profileId.includes('horizontal');
  return {
    id: profileId,
    width: isHoriz ? 1920 : 1080,
    height: isHoriz ? 1080 : 1920,
    aspectRatio: isHoriz ? '16:9' : '9:16',
    fps: 30,
  };
}

function getSceneFraming(scene, profileId) {
  if (!scene || !scene.framingByProfile || !profileId) return null;
  const f = scene.framingByProfile[profileId];
  if (!f || typeof f !== 'object') return null;
  if (f.centerX == null || f.centerY == null || f.zoomPercent == null) return null;
  return f;
}

function setSceneFraming(scene, profileId, val) {
  if (!scene || !profileId) return;
  if (!val) {
    if (scene.framingByProfile && Object.prototype.hasOwnProperty.call(scene.framingByProfile, profileId)) {
      delete scene.framingByProfile[profileId];
      if (!Object.keys(scene.framingByProfile).length) delete scene.framingByProfile;
    }
    return;
  }
  if (!scene.framingByProfile) scene.framingByProfile = {};
  scene.framingByProfile[profileId] = {
    centerX: Number(clamp01(val.centerX).toFixed(4)),
    centerY: Number(clamp01(val.centerY).toFixed(4)),
    zoomPercent: clampZoom(val.zoomPercent),
  };
}

function computeLocalCropPreview(srcW, srcH, outW, outH, framing) {
  if (!srcW || !srcH || !outW || !outH || !framing) {
    return {
      mode: 'fit', centerX: 0.5, centerY: 0.5, zoomPercent: 100,
      cropX: 0, cropY: 0, cropWidth: srcW || 0, cropHeight: srcH || 0,
    };
  }
  let baseW, baseH;
  if (srcW * outH >= outW * srcH) {
    baseH = srcH;
    baseW = srcH * (outW / outH);
  } else {
    baseW = srcW;
    baseH = srcW * (outH / outW);
  }
  const zoom = clampZoom(framing.zoomPercent) / 100;
  const rawW = baseW / zoom;
  const rawH = baseH / zoom;
  const maxEvenW = Math.max(2, srcW - (srcW % 2));
  const maxEvenH = Math.max(2, srcH - (srcH % 2));
  const cropW = Math.max(2, Math.min(maxEvenW, Math.round(rawW / 2) * 2));
  const cropH = Math.max(2, Math.min(maxEvenH, Math.round(rawH / 2) * 2));
  const cx = clamp01(framing.centerX);
  const cy = clamp01(framing.centerY);
  const maxLeft = Math.max(0, srcW - cropW);
  const maxTop = Math.max(0, srcH - cropH);
  let left = Math.round((cx * srcW - cropW / 2) / 2) * 2;
  let top = Math.round((cy * srcH - cropH / 2) / 2) * 2;
  left = Math.max(0, Math.min(maxLeft - (maxLeft % 2), left));
  top = Math.max(0, Math.min(maxTop - (maxTop % 2), top));
  return {
    mode: 'fill', centerX: cx, centerY: cy, zoomPercent: clampZoom(framing.zoomPercent),
    cropX: left, cropY: top, cropWidth: cropW, cropHeight: cropH,
  };
}

function syncActiveVideoProfile() {
  const selected = (draft && Array.isArray(draft.profiles)) ? draft.profiles : [];
  if (selected.length) {
    if (!activeVideoProfileId || !selected.includes(activeVideoProfileId)) {
      activeVideoProfileId = selected[0];
    }
    return activeVideoProfileId;
  }
  activeVideoProfileId = null;
  return null;
}

function renderActiveVideoProfileSelect() {
  const sel = $('#v-active-profile');
  const badge = $('#v-active-profile-info');
  const targetBadge = $('#v-preview-target-label');
  if (!sel) return;
  const prev = activeVideoProfileId;
  syncActiveVideoProfile();
  sel.innerHTML = '';
  const selected = (draft && Array.isArray(draft.profiles)) ? draft.profiles : [];
  for (const id of selected) {
    const p = getVideoProfileMeta(id);
    sel.append(el('option', { value: id, text: p ? `${id} — ${p.width}×${p.height} (${p.aspectRatio})` : id }));
  }
  if (!selected.length) {
    sel.append(el('option', { value: '', text: '— selecione um perfil na seção 1 —' }));
    if (badge) { badge.textContent = 'Nenhum destino selecionado'; badge.className = 'badge muted'; }
    if (targetBadge) targetBadge.textContent = 'Destino: —';
  } else {
    sel.value = activeVideoProfileId;
    const p = getVideoProfileMeta(activeVideoProfileId);
    if (badge) {
      badge.textContent = p ? `${p.width}×${p.height} (${p.aspectRatio})` : activeVideoProfileId;
      badge.className = 'badge ok';
    }
    if (targetBadge) targetBadge.textContent = `Destino: ${activeVideoProfileId}`;
  }
  if (prev !== activeVideoProfileId) {
    vLastFrameInfo = null;
  }
}

function seekPreviewPlayerTo(ms) {
  const box = $('#v-preview-player-box');
  const player = $('#v-preview-player');
  if (!box || box.hidden || !player || !player.getAttribute('src')) return;
  const sec = Math.max(0, (Number(ms) || 0) / 1000);
  if (player.readyState >= 1) {
    try { player.currentTime = sec; } catch {}
    pendingPreviewSeekSec = null;
  } else {
    pendingPreviewSeekSec = sec;
  }
}

function renderAssemblyTimeline() {
  const bar = $('#v-assembly-timeline');
  if (!bar) return;
  bar.innerHTML = '';
  const scenes = (draft && draft.scenes) || [];
  if (!scenes.length) {
    bar.append(el('span', { class: 'muted', text: 'Adicione cenas para visualizar a linha do tempo da montagem.' }));
    return;
  }
  syncActiveVideoProfile();
  let acc = 0;
  scenes.forEach((s, i) => {
    const dur = Math.max(0, Number(s.durationMs) || 0);
    const start = acc;
    const end = acc + dur;
    acc = end;
    const f = getSceneFraming(s, activeVideoProfileId);
    const frameTxt = activeVideoProfileId
      ? (f ? `Preencher ${f.zoomPercent}% (${Number(f.centerX).toFixed(2)}, ${Number(f.centerY).toFixed(2)})` : 'Ajustar')
      : 'Sem destino';
    const media = sceneMediaEntry(s);
    const cutTxt = media?.type === 'video'
      ? `corte ${fmtMs(s.sourceStartMs || 0)}→${fmtMs((s.sourceStartMs || 0) + dur)}`
      : 'imagem';
    const chip = el('button', {
      type: 'button',
      class: 'timeline-chip' + (i === selectedSceneIndex ? ' active' : ''),
      'data-scene-index': String(i),
      'data-start-ms': String(start),
      onclick: () => {
        selectedSceneIndex = i;
        vLastFrameInfo = null;
        renderScenes();
        seekPreviewPlayerTo(start);
      },
    }, [
      el('strong', { text: `${i + 1}. ${s.id || `cena-${i + 1}`}` }),
      el('small', { text: `${fmtMs(start)} → ${fmtMs(end)} (${cutTxt})` }),
      el('small', { text: frameTxt }),
    ]);
    bar.append(chip);
  });
}

function renderScenes() {
  const list = $('#scenes-list');
  list.innerHTML = '';
  const scenes = draft.scenes || [];
  if (selectedSceneIndex >= scenes.length) selectedSceneIndex = Math.max(0, scenes.length - 1);
  syncActiveVideoProfile();
  scenes.forEach((s, i) => {
    const f = getSceneFraming(s, activeVideoProfileId);
    const framingBadge = el('span', {
      class: 'badge ' + (f ? 'ok' : 'muted'),
      text: activeVideoProfileId
        ? (f ? `${activeVideoProfileId}: Preencher ${f.zoomPercent}%` : `${activeVideoProfileId}: Ajustar`)
        : 'Ajustar',
    });
    const mediaSel = el('select', {
      onchange: (e) => {
        s.mediaId = e.target.value;
        selectedSceneIndex = i;
        vLastFrameInfo = null;
        renderScenes();
        schedulePreviewStatusRefresh();
      },
    });
    mediaSel.append(el('option', { value: '', text: '— mídia —' }));
    for (const m of draft.media) mediaSel.append(el('option', { value: m.id, text: `${m.id} (${m.type})` }));
    mediaSel.value = s.mediaId || '';
    const nf = el('select', { onchange: (e) => { s.narrativeFunction = e.target.value; schedulePreviewStatusRefresh(); } });
    for (const v of NARRATIVE) nf.append(el('option', { value: v, text: v }));
    nf.value = s.narrativeFunction || 'demonstration';
    const mi = el('select', { onchange: (e) => { s.motionIntent = e.target.value; schedulePreviewStatusRefresh(); } });
    for (const v of MOTION) mi.append(el('option', { value: v, text: v }));
    mi.value = s.motionIntent || 'none';
    const card = el('div', { class: 'scene' + (i === selectedSceneIndex ? ' active-scene' : ''), 'data-scene-index': String(i) }, [
      el('div', { class: 'row', style: 'justify-content: space-between; align-items: center;' }, [
        el('div', {}, [framingBadge]),
        el('button', {
          type: 'button',
          class: i === selectedSceneIndex ? 'framing-active-btn' : 'secondary',
          text: i === selectedSceneIndex ? 'Enquadrando esta cena' : 'Enquadrar cena',
          onclick: () => {
            selectedSceneIndex = i;
            vLastFrameInfo = null;
            renderScenes();
          },
        }),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: `Cena ${i + 1} — id` }, el('input', { type: 'text', value: s.id, oninput: (e) => { s.id = e.target.value; renderAssemblyTimeline(); schedulePreviewStatusRefresh(); } })),
        el('label', { text: 'Duração (ms)' }, el('input', { type: 'number', class: 'scene-duration', min: '1', value: s.durationMs, oninput: (e) => { s.durationMs = Number(e.target.value); renderAssemblyTimeline(); schedulePreviewStatusRefresh(); } })),
        el('label', { text: 'Mídia' }, mediaSel),
        el('label', { text: 'Função' }, nf),
        el('label', { text: 'Movimento' }, mi),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Legenda (queimada)' }, el('input', { type: 'text', value: s.caption || '', oninput: (e) => { s.caption = e.target.value; schedulePreviewStatusRefresh(); } })),
        el('label', { text: 'Título sobreposto' }, el('input', { type: 'text', value: s.title || '', oninput: (e) => { s.title = e.target.value || undefined; schedulePreviewStatusRefresh(); } })),
      ]),
      el('div', { class: 'row' }, [
        el('label', { text: 'Narração (TXT separado)' }, el('input', { type: 'text', value: s.narration || '', oninput: (e) => { s.narration = e.target.value; } })),
      ]),
      sceneMediaEntry(s)?.type === 'video' ? buildCutEditor(s, i) : null,
      el('div', { class: 'row' }, [
        el('button', { class: 'secondary', text: '↑', onclick: () => {
          if (i > 0) {
            [draft.scenes[i - 1], draft.scenes[i]] = [draft.scenes[i], draft.scenes[i - 1]];
            if (selectedSceneIndex === i) selectedSceneIndex = i - 1;
            else if (selectedSceneIndex === i - 1) selectedSceneIndex = i;
            renderScenes();
            schedulePreviewStatusRefresh();
          }
        } }),
        el('button', { class: 'secondary', text: '↓', onclick: () => {
          if (i < draft.scenes.length - 1) {
            [draft.scenes[i + 1], draft.scenes[i]] = [draft.scenes[i], draft.scenes[i + 1]];
            if (selectedSceneIndex === i) selectedSceneIndex = i + 1;
            else if (selectedSceneIndex === i + 1) selectedSceneIndex = i;
            renderScenes();
            schedulePreviewStatusRefresh();
          }
        } }),
        el('button', { class: 'secondary', text: 'Duplicar cena', onclick: () => { duplicateScene(i); } }),
        el('button', { class: 'secondary', text: 'Remover', onclick: () => {
          draft.scenes.splice(i, 1);
          if (selectedSceneIndex >= draft.scenes.length) selectedSceneIndex = Math.max(0, draft.scenes.length - 1);
          vLastFrameInfo = null;
          renderScenes();
          schedulePreviewStatusRefresh();
        } }),
      ]),
    ]);
    list.append(card);
  });
  renderAssemblyTimeline();
  renderFramingEditor(true);
}

function duplicateScene(i) {
  const src = draft.scenes[i];
  const used = new Set(draft.scenes.map((s) => s.id));
  let n = 2;
  let id = `${src.id}-copia`;
  while (used.has(id)) id = `${src.id}-copia-${n++}`;
  const copy = JSON.parse(JSON.stringify(src));
  copy.id = id;
  draft.scenes.splice(i + 1, 0, copy);
  selectedSceneIndex = i + 1;
  renderScenes();
  schedulePreviewStatusRefresh();
  toast(`Cena duplicada (${id}) — a mesma fonte pode ser recortada em outro trecho.`);
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
  selectedSceneIndex = draft.scenes.length - 1;
  vLastFrameInfo = null;
  renderScenes();
  schedulePreviewStatusRefresh();
}

// ---- Enquadramento visual da cena selecionada e previa da montagem ----
function drawFramingCanvases() {
  const srcCv = $('#v-frame-source-canvas');
  const dstCv = $('#v-frame-dest-canvas');
  if (!srcCv || !dstCv) return;
  const sCtx = srcCv.getContext('2d');
  const dCtx = dstCv.getContext('2d');
  const s = (draft.scenes || [])[selectedSceneIndex] || null;
  const profile = getVideoProfileMeta(activeVideoProfileId);
  const outW = profile ? Number(profile.width) : 1080;
  const outH = profile ? Number(profile.height) : 1920;

  // Ajusta dimensoes do canvas de destino preservando proporcao do perfil
  const maxDstH = 360;
  const maxDstW = 360;
  const dstScale = Math.min(maxDstW / outW, maxDstH / outH);
  dstCv.width = Math.max(80, Math.round(outW * dstScale));
  dstCv.height = Math.max(80, Math.round(outH * dstScale));

  sCtx.fillStyle = '#000';
  sCtx.fillRect(0, 0, srcCv.width, srcCv.height);
  dCtx.fillStyle = '#000';
  dCtx.fillRect(0, 0, dstCv.width, dstCv.height);

  if (!s || !vFrameMedia.ready || !vFrameMedia.element || !vFrameMedia.width || !vFrameMedia.height) {
    srcCv._drawRect = null;
    if (!vFrameMedia.error) {
      sCtx.fillStyle = '#9aa0a6';
      sCtx.font = '13px system-ui, sans-serif';
      sCtx.fillText('Carregando quadro da mídia…', 16, 28);
    }
    return;
  }

  const natW = vFrameMedia.width;
  const natH = vFrameMedia.height;
  const fitSrc = Math.min(srcCv.width / natW, srcCv.height / natH);
  const drawW = natW * fitSrc;
  const drawH = natH * fitSrc;
  const drawX = (srcCv.width - drawW) / 2;
  const drawY = (srcCv.height - drawH) / 2;
  srcCv._drawRect = { x: drawX, y: drawY, w: drawW, h: drawH, natW, natH };
  sCtx.drawImage(vFrameMedia.element, drawX, drawY, drawW, drawH);

  const framing = getSceneFraming(s, activeVideoProfileId);
  const resolved = (vLastFrameInfo && vLastFrameInfo.resolvedFraming)
    ? vLastFrameInfo.resolvedFraming
    : computeLocalCropPreview(natW, natH, outW, outH, framing);

  if (framing && resolved.mode === 'fill') {
    const rx = drawX + (resolved.cropX / natW) * drawW;
    const ry = drawY + (resolved.cropY / natH) * drawH;
    const rw = (resolved.cropWidth / natW) * drawW;
    const rh = (resolved.cropHeight / natH) * drawH;
    // Escurece fora da janela de recorte
    sCtx.save();
    sCtx.fillStyle = 'rgba(0, 0, 0, 0.52)';
    sCtx.fillRect(drawX, drawY, drawW, Math.max(0, ry - drawY));
    sCtx.fillRect(drawX, ry + rh, drawW, Math.max(0, drawY + drawH - (ry + rh)));
    sCtx.fillRect(drawX, ry, Math.max(0, rx - drawX), rh);
    sCtx.fillRect(rx + rw, ry, Math.max(0, drawX + drawW - (rx + rw)), rh);
    sCtx.strokeStyle = '#4f8cff';
    sCtx.lineWidth = 2;
    sCtx.strokeRect(rx, ry, rw, rh);
    // Ponto do centro escolhido
    const px = drawX + clamp01(framing.centerX) * drawW;
    const py = drawY + clamp01(framing.centerY) * drawH;
    sCtx.fillStyle = '#FFD700';
    sCtx.beginPath();
    sCtx.arc(px, py, 5, 0, Math.PI * 2);
    sCtx.fill();
    sCtx.strokeStyle = '#000';
    sCtx.lineWidth = 1.5;
    sCtx.stroke();
    sCtx.restore();

    dCtx.drawImage(
      vFrameMedia.element,
      resolved.cropX, resolved.cropY, resolved.cropWidth, resolved.cropHeight,
      0, 0, dstCv.width, dstCv.height,
    );
  } else {
    sCtx.strokeStyle = 'rgba(63, 185, 80, 0.85)';
    sCtx.lineWidth = 2;
    sCtx.strokeRect(drawX + 1, drawY + 1, Math.max(1, drawW - 2), Math.max(1, drawH - 2));

    const fitOut = Math.min(dstCv.width / natW, dstCv.height / natH);
    const dw = natW * fitOut;
    const dh = natH * fitOut;
    dCtx.drawImage(vFrameMedia.element, (dstCv.width - dw) / 2, (dstCv.height - dh) / 2, dw, dh);
  }
}

function loadFramingSourceMedia(scene, forceSeek = false) {
  const metaP = $('#v-frame-source-meta');
  if (!scene || !scene.mediaId) {
    vFrameMedia = { key: null, element: null, width: 0, height: 0, ready: false, error: false, type: null };
    if (metaP) metaP.textContent = 'Selecione uma mídia nesta cena.';
    drawFramingCanvases();
    return;
  }
  const media = sceneMediaEntry(scene);
  if (!media || !media.path) {
    vFrameMedia = { key: null, element: null, width: 0, height: 0, ready: false, error: true, type: null };
    if (metaP) metaP.textContent = `Mídia ${scene.mediaId} não encontrada no pedido.`;
    drawFramingCanvases();
    return;
  }
  const cutStart = scene.sourceStartMs || 0;
  const key = `${media.type}|${media.path}|${cutStart}`;
  if (vFrameMedia.key === key && vFrameMedia.ready && !forceSeek) {
    drawFramingCanvases();
    return;
  }
  const srcUrl = `/source-media?path=${encodeURIComponent(media.path)}`;
  if (media.type === 'video') {
    const targetSec = Math.max(0, cutStart / 1000);
    const canReuseVideo = vFrameMedia.type === 'video' && vFrameMedia.mediaPath === media.path && vFrameMedia.videoEl;
    const videoEl = canReuseVideo ? vFrameMedia.videoEl : el('video', { muted: '', preload: 'auto', src: srcUrl });
    const frameCanvas = document.createElement('canvas');
    vFrameMedia = {
      key,
      mediaPath: media.path,
      type: 'video',
      videoEl,
      element: frameCanvas,
      width: vFrameMedia.width || 0,
      height: vFrameMedia.height || 0,
      ready: false,
      error: false,
    };
    const capture = () => {
      if (vFrameMedia.key !== key) return;
      const vw = videoEl.videoWidth || 0;
      const vh = videoEl.videoHeight || 0;
      if (vw <= 0 || vh <= 0) return;
      frameCanvas.width = vw;
      frameCanvas.height = vh;
      frameCanvas.getContext('2d').drawImage(videoEl, 0, 0, vw, vh);
      vFrameMedia.width = vw;
      vFrameMedia.height = vh;
      vFrameMedia.ready = true;
      vFrameMedia.error = false;
      if (metaP) metaP.textContent = `Quadro da gravação em ${fmtMs(cutStart)} (${vw}×${vh})`;
      drawFramingCanvases();
    };
    videoEl.onloadeddata = () => {
      if (vFrameMedia.key !== key) return;
      if (Math.abs((videoEl.currentTime || 0) - targetSec) < 0.02) capture();
      else {
        try { videoEl.currentTime = targetSec; } catch { capture(); }
      }
    };
    videoEl.onseeked = capture;
    videoEl.onerror = () => {
      if (vFrameMedia.key !== key) return;
      vFrameMedia.error = true;
      if (metaP) metaP.textContent = 'Não foi possível carregar o quadro da gravação.';
      drawFramingCanvases();
    };
    if (canReuseVideo && videoEl.readyState >= 2) {
      if (Math.abs((videoEl.currentTime || 0) - targetSec) < 0.02) capture();
      else {
        try { videoEl.currentTime = targetSec; } catch { capture(); }
      }
    }
  } else {
    const img = new Image();
    vFrameMedia = {
      key,
      mediaPath: media.path,
      type: 'image',
      element: img,
      width: 0,
      height: 0,
      ready: false,
      error: false,
    };
    img.onload = () => {
      if (vFrameMedia.key !== key) return;
      vFrameMedia.width = img.naturalWidth;
      vFrameMedia.height = img.naturalHeight;
      vFrameMedia.ready = true;
      vFrameMedia.error = false;
      if (metaP) metaP.textContent = `Imagem estática (${img.naturalWidth}×${img.naturalHeight})`;
      drawFramingCanvases();
    };
    img.onerror = () => {
      if (vFrameMedia.key !== key) return;
      vFrameMedia.error = true;
      if (metaP) metaP.textContent = 'Não foi possível carregar a imagem.';
      drawFramingCanvases();
    };
    img.src = srcUrl;
  }
}

function scheduleServerFrameInfo(immediate = false) {
  if (vFrameInfoTimer) clearTimeout(vFrameInfoTimer);
  const run = async () => {
    const s = (draft.scenes || [])[selectedSceneIndex];
    const errBox = $('#v-frame-error-banner');
    const errText = $('#v-frame-error-text');
    const infoP = $('#v-frame-resolved-info');
    if (!s || !activeVideoProfileId) {
      if (errBox) errBox.hidden = true;
      if (infoP) infoP.textContent = '';
      return;
    }
    const media = sceneMediaEntry(s);
    if (!media || !media.path) {
      if (errBox) errBox.hidden = true;
      if (infoP) infoP.textContent = 'Cena sem mídia selecionada.';
      return;
    }
    const seq = ++vFrameInfoSeq;
    const framing = getSceneFraming(s, activeVideoProfileId);
    try {
      const data = await post('/api/video/frame-info', {
        workId: currentWork ? currentWork.id : undefined,
        project: (draft && draft.project) || $('#project-select').value || undefined,
        profileId: activeVideoProfileId,
        mediaPath: media.path,
        beatId: s.id,
        framing: framing || { mode: 'fit' },
      });
      if (seq !== vFrameInfoSeq) return;
      vLastFrameInfo = data;
      const r = data.resolvedFraming || {};
      if (!data.ok && data.errorCode === 'FRAMING_MEDIA_METADATA_UNSUPPORTED') {
        if (errText) errText.textContent = data.message || 'Metadados de mídia impedem recorte confiável; volte para Ajustar.';
        if (errBox) errBox.hidden = false;
        if (infoP) infoP.textContent = `Fallback disponível: Ajustar (${r.sourceWidth}×${r.sourceHeight} → ${r.outputWidth}×${r.outputHeight})`;
      } else {
        if (errBox) errBox.hidden = true;
        if (infoP) {
          infoP.textContent = r.mode === 'fill'
            ? `Adaptador: recorte ${r.cropWidth}×${r.cropHeight} em (${r.cropX}, ${r.cropY}) → saída ${r.outputWidth}×${r.outputHeight} (zoom ${r.zoomPercent}%, centro ${Number(r.centerX).toFixed(2)}, ${Number(r.centerY).toFixed(2)})`
            : `Adaptador: Ajustar (mídia inteira ${r.sourceWidth}×${r.sourceHeight} centralizada em ${r.outputWidth}×${r.outputHeight})`;
        }
      }
      drawFramingCanvases();
    } catch (err) {
      if (seq !== vFrameInfoSeq) return;
      if (infoP) infoP.textContent = `Aviso ao consultar adaptador: ${err.message}`;
    }
  };
  if (immediate) run();
  else vFrameInfoTimer = setTimeout(run, 100);
}

function renderFramingEditor(reloadMedia = false, queryImmediate = true) {
  const panel = $('#v-framing-editor');
  if (!panel) return;
  const scenes = (draft && draft.scenes) || [];
  syncActiveVideoProfile();
  if (!scenes.length || !activeVideoProfileId) {
    panel.hidden = true;
    return;
  }
  if (selectedSceneIndex < 0 || selectedSceneIndex >= scenes.length) selectedSceneIndex = 0;
  const s = scenes[selectedSceneIndex];
  panel.hidden = false;
  const f = getSceneFraming(s, activeVideoProfileId);
  const title = $('#v-framing-scene-title');
  const summary = $('#v-framing-scene-summary');
  if (title) title.textContent = `Cena ${selectedSceneIndex + 1} (${s.id}) — ${activeVideoProfileId}`;
  if (summary) {
    summary.textContent = f
      ? `Preencher (${f.zoomPercent}% em ${Number(f.centerX).toFixed(2)}, ${Number(f.centerY).toFixed(2)})`
      : 'Ajustar (mídia inteira centralizada)';
    summary.className = 'badge ' + (f ? 'ok' : 'muted');
  }
  const fitBtn = $('#v-frame-mode-fit');
  const fillBtn = $('#v-frame-mode-fill');
  if (fitBtn) fitBtn.classList.toggle('framing-active-btn', !f);
  if (fillBtn) fillBtn.classList.toggle('framing-active-btn', Boolean(f));

  const cx = f ? clamp01(f.centerX) : 0.5;
  const cy = f ? clamp01(f.centerY) : 0.5;
  const zoom = f ? clampZoom(f.zoomPercent) : 100;
  $('#v-frame-center-x').value = cx.toFixed(2);
  $('#v-frame-center-y').value = cy.toFixed(2);
  $('#v-frame-zoom-range').value = String(zoom);
  $('#v-frame-zoom').value = String(zoom);

  if (reloadMedia) loadFramingSourceMedia(s, false);
  else drawFramingCanvases();
  scheduleServerFrameInfo(queryImmediate);
}

function applyFramingChange(nextFraming, queryImmediate = false) {
  const s = (draft.scenes || [])[selectedSceneIndex];
  syncActiveVideoProfile();
  if (!s || !activeVideoProfileId) return;
  vLastFrameInfo = null;
  setSceneFraming(s, activeVideoProfileId, nextFraming);
  renderFramingEditor(false, queryImmediate);
  renderAssemblyTimeline();
  // Atualiza somente o badge da cena ativa na lista para nao recriar inputs durante digitacao/arraste
  const badge = document.querySelector(`#scenes-list .scene[data-scene-index="${selectedSceneIndex}"] .badge`);
  if (badge) {
    const cur = getSceneFraming(s, activeVideoProfileId);
    badge.className = 'badge ' + (cur ? 'ok' : 'muted');
    badge.textContent = cur ? `${activeVideoProfileId}: Preencher ${cur.zoomPercent}%` : `${activeVideoProfileId}: Ajustar`;
  }
  schedulePreviewStatusRefresh();
}

function renderVideoPreviewState(data) {
  vLastPreviewData = data || null;
  const badge = $('#v-preview-render-badge');
  const statusBox = $('#v-preview-render-status');
  const playerBox = $('#v-preview-player-box');
  const player = $('#v-preview-player');
  const metaP = $('#v-preview-player-meta');
  const targetBadge = $('#v-preview-target-label');
  if (!badge || !statusBox || !playerBox || !player) return;

  const pid = data?.profileId || activeVideoProfileId;
  if (targetBadge) targetBadge.textContent = pid ? `Destino: ${pid}` : 'Destino: —';
  if (!data || !pid) {
    badge.className = 'badge muted';
    badge.textContent = 'Sem destino';
    statusBox.textContent = '';
    playerBox.hidden = true;
    return;
  }

  const job = data.job;
  const lastReady = data.lastReady;
  if (lastReady && lastReady.url) {
    playerBox.hidden = false;
    const desiredUrl = `${lastReady.url}&v=${encodeURIComponent(lastReady.previewFingerprint || '')}`;
    if (vLoadedPreviewUrl !== desiredUrl) {
      vLoadedPreviewUrl = desiredUrl;
      player.src = desiredUrl;
    }
    if (metaP) {
      metaP.textContent = `${lastReady.width}×${lastReady.height} · ${fmtMs(lastReady.durationMs)} · ${lastReady.bytes} bytes · sem áudio (SHA ${(lastReady.sha256 || '').slice(0, 10)})`;
    }
  } else {
    playerBox.hidden = true;
    vLoadedPreviewUrl = null;
    player.removeAttribute('src');
  }

  if (job && job.status === 'running') {
    badge.className = 'badge warn';
    badge.textContent = lastReady
      ? 'Gerando prévia (exibindo prévia da versão anterior)'
      : 'Gerando prévia da montagem…';
    statusBox.textContent = 'Renderizando prévia com o mesmo grafo de composição e legendas…';
    return;
  }

  if (job && job.status === 'failed') {
    badge.className = 'badge err';
    badge.textContent = 'Falha na geração da prévia';
    statusBox.innerHTML = '';
    statusBox.append(el('div', { class: 'alert-box err', text: job.error || 'Falha desconhecida ao gerar prévia.' }));
    return;
  }

  if (lastReady) {
    if (lastReady.matchesCurrentDraft) {
      badge.className = 'badge ok';
      badge.textContent = 'Prévia atualizada';
      statusBox.textContent = 'Prévia pronta e sincronizada com a edição atual deste destino.';
    } else {
      badge.className = 'badge warn';
      badge.textContent = 'Prévia da versão anterior';
      statusBox.textContent = 'O pedido, recorte, enquadramento ou mídia deste destino mudou desde a última prévia. Gere novamente para atualizar.';
    }
    return;
  }

  badge.className = 'badge muted';
  badge.textContent = 'Sem prévia gerada';
  statusBox.textContent = 'Clique em "Gerar prévia da montagem" para renderizar e assistir à montagem deste destino.';
}

async function refreshVideoPreviewStatus(profileOverride) {
  syncActiveVideoProfile();
  const profileId = profileOverride || activeVideoProfileId;
  if (!profileId) {
    renderVideoPreviewState(null);
    return null;
  }
  syncDraftFields();
  const seq = ++vPreviewStatusSeq;
  const data = await post('/api/video/preview-status', {
    workId: currentWork ? currentWork.id : undefined,
    profileId,
    request: draft,
    motionPlan: (!mStandaloneOverride && mplan && (mplan.effects || []).length) ? mplan : undefined,
  });
  if (seq !== vPreviewStatusSeq) return data;
  if (profileId === activeVideoProfileId) renderVideoPreviewState(data);
  if (data.job && data.job.status === 'running') {
    pollVideoPreview(data.job.jobId, profileId);
  }
  return data;
}

function schedulePreviewStatusRefresh() {
  if (vPreviewStatusTimer) clearTimeout(vPreviewStatusTimer);
  vPreviewStatusTimer = setTimeout(() => {
    refreshVideoPreviewStatus().catch(() => {});
  }, 150);
}

function pollVideoPreview(jobId, profileId) {
  if (vPreviewPollTimer) clearTimeout(vPreviewPollTimer);
  const tick = async () => {
    try {
      syncDraftFields();
      const data = await post('/api/video/preview-status', {
        workId: currentWork ? currentWork.id : undefined,
        profileId,
        jobId,
        request: draft,
        motionPlan: (!mStandaloneOverride && mplan && (mplan.effects || []).length) ? mplan : undefined,
      });
      if (profileId === activeVideoProfileId) renderVideoPreviewState(data);
      if (data.job && data.job.status === 'running') {
        vPreviewPollTimer = setTimeout(tick, 700);
      }
    } catch (err) {
      toast('Erro ao consultar prévia: ' + err.message);
    }
  };
  vPreviewPollTimer = setTimeout(tick, 600);
}

async function startVideoPreviewRender() {
  syncDraftFields();
  syncActiveVideoProfile();
  if (!activeVideoProfileId) {
    toast('Selecione pelo menos um perfil de vídeo antes de gerar a prévia.');
    return;
  }
  const badge = $('#v-preview-render-badge');
  if (badge) { badge.className = 'badge warn'; badge.textContent = 'Iniciando prévia…'; }
  try {
    const started = await post('/api/video/preview-render', {
      workId: currentWork ? currentWork.id : undefined,
      profileId: activeVideoProfileId,
      request: draft,
      motionPlan: (!mStandaloneOverride && mplan && (mplan.effects || []).length) ? mplan : undefined,
    });
    await refreshVideoPreviewStatus(activeVideoProfileId);
    pollVideoPreview(started.jobId, activeVideoProfileId);
  } catch (err) {
    if (badge) { badge.className = 'badge err'; badge.textContent = 'Erro ao iniciar prévia'; }
    toast('Prévia falhou: ' + err.message);
  }
}

function initFramingAndPreviewControls() {
  const activeSel = $('#v-active-profile');
  if (activeSel) {
    activeSel.addEventListener('change', () => {
      activeVideoProfileId = activeSel.value || null;
      vLastFrameInfo = null;
      vLoadedPreviewUrl = null;
      renderActiveVideoProfileSelect();
      renderScenes();
      refreshVideoPreviewStatus().catch(() => {});
    });
  }
  $('#v-frame-mode-fit')?.addEventListener('click', () => applyFramingChange(null, true));
  $('#v-frame-fallback-fit-btn')?.addEventListener('click', () => {
    applyFramingChange(null, true);
    toast('Enquadramento revertido para Ajustar.');
  });
  $('#v-frame-mode-fill')?.addEventListener('click', () => {
    const s = (draft.scenes || [])[selectedSceneIndex];
    const cur = getSceneFraming(s, activeVideoProfileId);
    applyFramingChange(cur || { centerX: 0.5, centerY: 0.5, zoomPercent: 100 }, true);
  });
  $('#v-frame-reset-btn')?.addEventListener('click', () => {
    applyFramingChange(null, true);
    toast(`Ajuste da cena desfeito para ${activeVideoProfileId || 'o destino'} (voltou para Ajustar).`);
  });

  const cxInput = $('#v-frame-center-x');
  const cyInput = $('#v-frame-center-y');
  const zoomRange = $('#v-frame-zoom-range');
  const zoomInput = $('#v-frame-zoom');

  function applyNumericInputs() {
    applyFramingChange({
      centerX: clamp01(cxInput.value),
      centerY: clamp01(cyInput.value),
      zoomPercent: clampZoom(zoomInput.value),
    }, false);
  }
  cxInput?.addEventListener('input', applyNumericInputs);
  cyInput?.addEventListener('input', applyNumericInputs);
  zoomRange?.addEventListener('input', () => {
    zoomInput.value = zoomRange.value;
    applyFramingChange({
      centerX: clamp01(cxInput.value),
      centerY: clamp01(cyInput.value),
      zoomPercent: clampZoom(zoomRange.value),
    }, false);
  });
  zoomInput?.addEventListener('input', () => {
    zoomRange.value = String(clampZoom(zoomInput.value));
    applyNumericInputs();
  });

  const srcCv = $('#v-frame-source-canvas');
  function updateCenterFromPointer(ev) {
    const rect = srcCv.getBoundingClientRect();
    const px = ((ev.clientX - rect.left) / rect.width) * srcCv.width;
    const py = ((ev.clientY - rect.top) / rect.height) * srcCv.height;
    const dr = srcCv._drawRect || { x: 0, y: 0, w: srcCv.width, h: srcCv.height };
    const cx = clamp01((px - dr.x) / dr.w);
    const cy = clamp01((py - dr.y) / dr.h);
    const s = (draft.scenes || [])[selectedSceneIndex];
    const cur = getSceneFraming(s, activeVideoProfileId);
    applyFramingChange({ centerX: cx, centerY: cy, zoomPercent: cur ? cur.zoomPercent : 100 }, false);
  }
  srcCv?.addEventListener('pointerdown', (ev) => {
    if (!srcCv._drawRect) return;
    vFrameDrag = true;
    try { srcCv.setPointerCapture(ev.pointerId); } catch {}
    updateCenterFromPointer(ev);
  });
  srcCv?.addEventListener('pointermove', (ev) => {
    if (!vFrameDrag) return;
    updateCenterFromPointer(ev);
  });
  srcCv?.addEventListener('pointerup', () => {
    if (!vFrameDrag) return;
    vFrameDrag = false;
    scheduleServerFrameInfo(true);
  });

  $('#v-btn-preview-render')?.addEventListener('click', () => startVideoPreviewRender().catch((e) => toast(e.message)));
  const player = $('#v-preview-player');
  player?.addEventListener('loadedmetadata', () => {
    if (pendingPreviewSeekSec != null) {
      try { player.currentTime = pendingPreviewSeekSec; } catch {}
      pendingPreviewSeekSec = null;
    }
  });
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
    const chosen = $('#export-profile').value;
    const frameProfile = r.profiles.find((p) => p.status === 'compiled' && p.profileId === chosen)
      || r.profiles.find((p) => p.status === 'compiled');
    if (frameProfile) {
      const firstMedia = (frameProfile.beats || []).map((b) => b.mediaId).find((id) => id);
      const mediaEntry = (draft.media || []).find((m) => m.id === firstMedia);
      drawEffectiveFrame('#preview-frame-canvas', '#preview-frame-info', frameProfile.geometry, mediaEntry ? mediaEntry.path : null);
    }
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
        el('td', { text: b.sourceStartMs != null ? `${b.sourceStartMs}→${b.sourceEndMs} ms` : 'imagem' }),
        el('td', { text: b.mediaId }), el('td', { text: b.title || '—' }),
      ]));
      const card = el('div', { class: 'profile-card' }, [
        el('strong', { text: p.profileId + ' ' }),
        el('span', { class: 'badge ok', text: `${p.geometry.width}×${p.geometry.height} @ ${p.fps}fps` }),
        el('span', { class: 'badge muted', text: `total ${p.durationSeconds}s` }),
        el('table', {}, [
          el('thead', {}, el('tr', {}, [el('th', { text: 'Beat' }), el('th', { text: 'Montagem' }), el('th', { text: 'Duração' }), el('th', { text: 'Trecho da fonte' }), el('th', { text: 'Mídia' }), el('th', { text: 'Título' })])),
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
      captionsMode: ($('#work-captions-clean')?.checked) ? 'clean' : 'burned',
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
  if (currentWork && !$('#mode-review').hidden) loadReviewOverview().catch(() => {});
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
  renderExportProfileOptions();
  if (catalog.length) renderProfiles();
  renderScenes();
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
    sel.append(el('option', { value: cdraft?.profile || '', text: 'Nenhum perfil 1:1 ou 4:5 permitido neste projeto' }));
    $('#c-profile-info').textContent = 'Nenhum perfil de carrossel local (1:1 1080×1080 ou 4:5 1080×1350) permitido pela allowlist deste projeto.';
    return;
  }
  for (const p of compat) {
    sel.append(el('option', { value: p.id, text: `${p.id} — ${p.width}×${p.height} (${p.aspectRatio}, ${p.network})` }));
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
  if (currentWork) {
    currentWork = null;
    renderActiveWorkBar();
  }
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
  if (currentWork) {
    currentWork = null;
    renderActiveWorkBar();
  }
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
    const firstWithMedia = (r.cards || []).find((c) => c.mediaId);
    const mediaEntry = firstWithMedia ? (cdraft.media || []).find((m) => m.id === firstWithMedia.mediaId) : null;
    drawEffectiveFrame('#c-preview-frame-canvas', '#c-preview-frame-info', r.geometry, mediaEntry ? mediaEntry.path : null);
  } catch (err) { out.innerHTML = ''; out.append(el('pre', { text: 'Erro: ' + err.message })); }
}

// Quadro efetivo antes do render: midia ajustada a proporcao do perfil com
// bandas de preenchimento centralizadas (mesma regra do adaptador: fit + pad).
function drawEffectiveFrame(canvasSel, infoSel, geometry, mediaPath) {
  const cv = $(canvasSel);
  const info = $(infoSel);
  if (!cv || !geometry) return;
  const maxW = 320;
  const scale = Math.min(maxW / geometry.width, 480 / geometry.height);
  cv.width = Math.round(geometry.width * scale);
  cv.height = Math.round(geometry.height * scale);
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, cv.width, cv.height);
  const finish = (img, natural) => {
    let bands = 'nenhuma (proporção idêntica)';
    if (img) {
      const fit = Math.min(cv.width / natural.width, cv.height / natural.height);
      const dw = natural.width * fit;
      const dh = natural.height * fit;
      ctx.drawImage(img, (cv.width - dw) / 2, (cv.height - dh) / 2, dw, dh);
      if (dw < cv.width - 1) bands = 'verticais (pillarbox)';
      else if (dh < cv.height - 1) bands = 'horizontais (letterbox)';
    }
    if (info) {
      info.textContent = `Quadro efetivo ${geometry.width}×${geometry.height} (${geometry.aspectRatio || ''}). `
        + (img ? `Mídia ${natural.width}×${natural.height} ajustada com preservação de proporção; bandas de preenchimento: ${bands}. ` : 'Sem mídia nesta peça: fundo do layout. ')
        + 'Enquadramento do render: scale fit + pad centralizado + setsar=1.';
    }
  };
  if (!mediaPath) { finish(null, null); return; }
  const img = new Image();
  img.onload = () => finish(img, { width: img.naturalWidth, height: img.naturalHeight });
  img.onerror = () => finish(null, null);
  img.src = '/source-media?path=' + encodeURIComponent(mediaPath);
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
    if (currentWork && !$('#mode-review').hidden) loadReviewOverview().catch(() => {});
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
  const motionIds = new Set(catalog.filter((p) => p.localExportMotion).map((p) => p.id));
  const requested = (mreq && mreq.profiles && mreq.profiles.length) ? mreq.profiles : [...motionIds];
  const list = requested.filter((id) => motionIds.has(id));
  const excluded = requested.filter((id) => !motionIds.has(id));
  for (const id of list) {
    const p = catalog.find((x) => x.id === id);
    sel.append(el('option', { value: id, text: p ? `${id} — ${p.width}×${p.height} (${p.aspectRatio})` : id }));
  }
  if (list.includes(prev)) sel.value = prev;
  const note = $('#m-motion-note');
  if (note) {
    note.textContent = excluded.length
      ? `Motion disponível apenas em 9:16 nesta rodada. Perfis do pedido sem Motion: ${excluded.join(', ')} — o contorno usa coordenadas relativas ao quadro final e exige configuração própria para outro enquadramento.`
      : 'Motion disponível apenas em 9:16 nesta rodada; o contorno usa coordenadas relativas ao quadro final.';
  }
}

function currentMedia() {
  const s = currentMScene();
  if (!s || !mreq) return null;
  return mreq.media.find((m) => m.id === s.mediaId) || null;
}

function getMotionProfileId() {
  const sel = $('#m-profile-select');
  if (sel && sel.value) return sel.value;
  return (mreq && mreq.profiles || []).find((id) => catalog.some((c) => c.id === id && c.localExportMotion))
    || 'instagram-reels-video';
}

function drawMotionCanvas() {
  const cv = $('#m-canvas');
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, cv.width, cv.height);
  if (!mreq || !mplan) return;
  const scene = currentMScene();
  const media = currentMedia();
  if (!scene || !media) return;

  let drawEl = null;
  let natW = 0;
  let natH = 0;
  if (media.type === 'video') {
    const cutStart = scene.sourceStartMs || 0;
    const key = `${media.path}|${cutStart}`;
    if (mVideoMedia.key !== key) {
      const targetSec = Math.max(0, cutStart / 1000);
      const vid = el('video', { muted: '', preload: 'auto', src: '/source-media?path=' + encodeURIComponent(media.path) });
      const frameCanvas = document.createElement('canvas');
      mVideoMedia = { key, canvas: frameCanvas, ready: false, width: 0, height: 0, error: false };
      const cap = () => {
        if (mVideoMedia.key !== key) return;
        const vw = vid.videoWidth || 0;
        const vh = vid.videoHeight || 0;
        if (!vw || !vh) return;
        frameCanvas.width = vw;
        frameCanvas.height = vh;
        frameCanvas.getContext('2d').drawImage(vid, 0, 0, vw, vh);
        mVideoMedia.width = vw;
        mVideoMedia.height = vh;
        mVideoMedia.ready = true;
        drawMotionCanvas();
      };
      vid.onloadeddata = () => {
        if (mVideoMedia.key !== key) return;
        if (Math.abs((vid.currentTime || 0) - targetSec) < 0.02) cap();
        else { try { vid.currentTime = targetSec; } catch { cap(); } }
      };
      vid.onseeked = cap;
      return;
    }
    if (!mVideoMedia.ready) return;
    drawEl = mVideoMedia.canvas;
    natW = mVideoMedia.width;
    natH = mVideoMedia.height;
  } else {
    if (!mImg || mImg._src !== media.path) {
      mImg = new Image();
      mImg._src = media.path;
      mImg.onload = () => drawMotionCanvas();
      mImg.src = '/source-media?path=' + encodeURIComponent(media.path);
      return;
    }
    if (!mImg.naturalWidth || !mImg.naturalHeight) return;
    drawEl = mImg;
    natW = mImg.naturalWidth;
    natH = mImg.naturalHeight;
  }

  const profileId = getMotionProfileId();
  const profileMeta = getVideoProfileMeta(profileId);
  const outW = profileMeta ? Number(profileMeta.width) : 1080;
  const outH = profileMeta ? Number(profileMeta.height) : 1920;
  const framing = getSceneFraming(scene, profileId);
  if (framing && framing.zoomPercent) {
    const crop = computeLocalCropPreview(natW, natH, outW, outH, framing);
    ctx.drawImage(drawEl, crop.cropX, crop.cropY, crop.cropWidth, crop.cropHeight, 0, 0, cv.width, cv.height);
  } else {
    const scale = Math.min(cv.width / natW, cv.height / natH);
    const dw = natW * scale;
    const dh = natH * scale;
    ctx.drawImage(drawEl, (cv.width - dw) / 2, (cv.height - dh) / 2, dw, dh);
  }

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
  const profileId = getMotionProfileId();
  const framing = getSceneFraming(scene, profileId);
  const framingTag = framing
    ? `Enquadramento ${profileId}: Preencher ${framing.zoomPercent}% (${Number(framing.centerX).toFixed(2)}, ${Number(framing.centerY).toFixed(2)}). `
    : `Enquadramento ${profileId}: Ajustar (quadro completo). `;
  if (scene.motionIntent === 'slow-zoom') {
    $('#m-region-info').textContent = `${framingTag}Cena "${scene.id}" está com slow-zoom; altere o movimento para "none" na aba Vídeos para aplicar contorno.`;
    return;
  }
  if (!e) {
    $('#m-region-info').textContent = `${framingTag}Cena "${scene.id}" (${scene.durationMs}ms) ainda sem contorno. Arraste na imagem ou clique em "Ativar contorno nesta cena".`;
    return;
  }
  const r = e.region;
  $('#m-region-info').textContent = `${framingTag}Região (${e.sceneId}): x=${r.x.toFixed(2)} y=${r.y.toFixed(2)} w=${r.w.toFixed(2)} h=${r.h.toFixed(2)} — contorno de ${e.startMs}ms a ${e.endMs}ms (${e.color}, ${e.thickness}px).`;
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
      captionsMode: ($('#work-captions-clean')?.checked) ? 'clean' : 'burned',
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
    if (currentWork && !$('#mode-review').hidden) loadReviewOverview().catch(() => {});
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
  $('#m-profile-select')?.addEventListener('change', () => { drawMotionCanvas(); updateMRegionInfo(); });
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

function bindLegacyHomeEvents() {
  if (isAstryxHomeActive()) return;
  const root = homeLegacyRoot();
  if (!root || !root.childElementCount) return;

  homeEl('#btn-refresh-readiness')?.addEventListener('click', () => loadReadiness());

  // Sugestão automática de IDs em kebab-case nos formulários
  let workIdTouched = false;
  homeEl('#work-id')?.addEventListener('input', () => { workIdTouched = true; updateWorkPathsPreview(); });
  homeEl('#work-name')?.addEventListener('input', (e) => {
    if (!workIdTouched) {
      const workIdEl = homeEl('#work-id');
      if (workIdEl) workIdEl.value = slugifyKebab(e.target.value);
      updateWorkPathsPreview();
    }
  });
  updateWorkPathsPreview();

  let projIdTouched = false;
  homeEl('#proj-id')?.addEventListener('input', () => {
    projIdTouched = true;
    const v = (homeEl('#proj-id')?.value || '').trim();
    if (v) {
      const themeEl = homeEl('#proj-theme');
      const assetEl = homeEl('#proj-asset-root');
      if (themeEl) themeEl.value = v;
      if (assetEl) assetEl.value = `.workspace/studio/projects/${v}/assets`;
    }
  });
  homeEl('#proj-name')?.addEventListener('input', (e) => {
    if (!projIdTouched) {
      const slug = slugifyKebab(e.target.value);
      const projIdEl = homeEl('#proj-id');
      if (projIdEl) projIdEl.value = slug;
      if (slug) {
        const themeEl = homeEl('#proj-theme');
        const assetEl = homeEl('#proj-asset-root');
        if (themeEl) themeEl.value = slug;
        if (assetEl) assetEl.value = `.workspace/studio/projects/${slug}/assets`;
      }
    }
  });

  homeEl('#btn-create-project')?.addEventListener('click', createProject);
  homeEl('#btn-create-work')?.addEventListener('click', createWork);
  homeEl('#btn-demo-marca-salao')?.addEventListener('click', () => startGuidedDemo('marca-salao'));
  homeEl('#btn-demo-multitrack')?.addEventListener('click', () => startGuidedDemo('multitrack-hub'));
  homeEl('#btn-open-batch-export')?.addEventListener('click', () => openBatchExportModal().catch((e) => toast(e.message)));
  homeEl('#btn-open-template-create')?.addEventListener('click', () => openTemplateCreateDialog().catch((e) => toast(e.message)));
  homeEl('#works-select-all')?.addEventListener('change', (e) => {
    const checked = e.target.checked;
    root.querySelectorAll('.work-select-cb').forEach((cb) => {
      cb.checked = checked;
      const wid = cb.getAttribute('data-work-id');
      if (checked) selectedBatchWorks.add(wid);
      else selectedBatchWorks.delete(wid);
    });
    updateBatchSelectionCount();
  });
}

async function init() {
  draft = emptyDraft();
  await loadReadiness();
  await loadProjects();
  await renderProjectProfileBoxes();
  await loadWorks();
  await loadExamples();
  renderAll();

  $('#readiness-banner').addEventListener('click', () => {
    const details = $('#readiness-details');
    details.hidden = !details.hidden;
  });

  bindLegacyHomeEvents();
  bindLegacyQueueEvents();

  $('#btn-save-work').addEventListener('click', () => saveWork().catch((e) => toast(e.message)));
  $('#btn-work-home').addEventListener('click', () => setMode('home'));
  $('#work-captions-clean')?.addEventListener('change', () => {
    if (typeof schedulePreviewStatusRefresh === 'function') schedulePreviewStatusRefresh();
  });

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
  $('#btn-import-recording').addEventListener('click', () => $('#recording-file').click());
  $('#recording-file').addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = '';
    if (file) importRecordingFile(file).catch((err) => toast(err.message));
  });
  $('#btn-add-scene').addEventListener('click', addScene);
  $('#btn-preview').addEventListener('click', preview);
  $('#btn-export').addEventListener('click', () => startExport());
  $('#btn-load-delivery').addEventListener('click', () => loadDelivery().catch((e) => toast(e.message)));

  $('#mode-home-btn').addEventListener('click', () => setMode('home'));
  $('#mode-video-btn').addEventListener('click', () => setMode('video'));
  $('#mode-carousel-btn').addEventListener('click', () => setMode('carousel'));
  $('#mode-motion-btn').addEventListener('click', () => setMode('motion'));
  $('#mode-review-btn').addEventListener('click', () => setMode('review'));
  $('#mode-queue-btn').addEventListener('click', () => setMode('queue'));
  $('#mode-connections-btn').addEventListener('click', () => setMode('connections'));
  $('#btn-conn-new').addEventListener('click', () => openConnectionDialog(null).catch((e) => toast(e.message)));
  $('#btn-conn-select-save').addEventListener('click', () => saveConnectionSelection().catch((e) => toast(e.message)));
  $('#conn-project-select').addEventListener('change', () => fillConnectionSelection().catch((e) => toast(e.message)));
  $('#btn-r-refresh').addEventListener('click', () => loadReviewOverview().catch((e) => toast(e.message)));
  $('#btn-r-save-editorial').addEventListener('click', () => saveEditorialSheet().catch((e) => toast(e.message)));
  if (!isAstryxReviewPackageActive()) {
    $('#btn-r-build-package')?.addEventListener('click', () => buildPackageZip().catch((e) => toast(e.message)));
  }

  await initCarousel();
  await initMotion();
  initFramingAndPreviewControls();
  loadQueue().catch(() => {});
  setMode('home');
}

// ---- Revisão & Entrega ----
function isAstryxReviewPackageActive() {
  return Boolean(window.__studioAstryxReviewPackageActive);
}

function syncAstryxReviewPackageState(workId, review, pkg) {
  const payload = {
    workId: workId || null,
    review: review || null,
    packageDelivery: pkg || null,
  };
  window.__studioReviewPackageState = payload;
  if (isAstryxReviewPackageActive()) {
    window.dispatchEvent(new CustomEvent('studio:review-package-sync', { detail: payload }));
  }
}

function reviewStatusClass(status) {
  if (status === 'approved') return 'ok';
  if (status === 'changes_requested' || status === 'unavailable') return 'err';
  if (status === 'draft_outdated' || status === 'copy_outdated' || status === 'unlinked' || status === 'reexported_pending' || status === 'pending_review') return 'warn';
  return 'muted';
}

async function loadReviewOverview() {
  const seq = ++reviewSyncSeq;
  if (!currentWork) {
    renderReviewPanel(null, null);
    return null;
  }
  const d = await api('/api/works/review?id=' + encodeURIComponent(currentWork.id));
  if (seq === reviewSyncSeq) {
    renderReviewPanel(d, d.packageDelivery || null);
  }
  return d;
}

function collectBriefingFromUI() {
  return {
    objective: ($('#r-brief-objective')?.value || '').trim(),
    audience: ($('#r-brief-audience')?.value || '').trim(),
    coreMessage: ($('#r-brief-core')?.value || '').trim(),
    supportEvidence: ($('#r-brief-evidence')?.value || '').trim(),
    hook: ($('#r-brief-hook')?.value || '').trim(),
    scriptSummary: ($('#r-brief-script')?.value || '').trim(),
    cta: ($('#r-brief-cta')?.value || '').trim(),
  };
}

function readChannelCardInputs(card) {
  const pid = card.getAttribute('data-channel-id');
  const getVal = (f) => (card.querySelector(`[data-ch-field="${f}"]`)?.value || '').trim();
  return {
    profileId: pid,
    title: getVal('title'),
    postText: getVal('postText'),
    cta: getVal('cta'),
    destinationUrl: getVal('destinationUrl'),
    hashtags: getVal('hashtags'),
  };
}

function collectChannelsFromUI() {
  const out = {};
  document.querySelectorAll('#r-channels-list [data-channel-id]').forEach((card) => {
    const entry = readChannelCardInputs(card);
    out[entry.profileId] = entry;
  });
  return out;
}

async function saveEditorialSheet() {
  if (!currentWork) return;
  const seq = ++reviewSyncSeq;
  const feedback = $('#r-editorial-feedback');
  feedback.innerHTML = '';
  try {
    const d = await post('/api/works/editorial/save', {
      workId: currentWork.id,
      briefing: collectBriefingFromUI(),
      channels: collectChannelsFromUI(),
    });
    if (seq === reviewSyncSeq) renderReviewPanel(d, d.packageDelivery || null);
    feedback.append(el('div', { class: 'alert-box ok', text: 'Ficha editorial e textos por canal salvos atomicamente.' }));
    toast('Ficha editorial salva.');
  } catch (err) {
    feedback.append(el('div', { class: 'alert-box err', text: err.message }));
    toast(err.message);
  }
}

async function saveSingleChannelCopy(card) {
  if (!currentWork) return;
  const seq = ++reviewSyncSeq;
  const entry = readChannelCardInputs(card);
  const feedback = card.querySelector('.r-ch-feedback');
  if (feedback) feedback.innerHTML = '';
  try {
    const d = await post('/api/works/editorial/save', {
      workId: currentWork.id,
      channels: { [entry.profileId]: entry },
    });
    if (seq === reviewSyncSeq) renderReviewPanel(d, d.packageDelivery || null);
    toast(`Texto do canal ${entry.profileId} salvo.`);
  } catch (err) {
    if (feedback) feedback.append(el('div', { class: 'alert-box err', text: err.message }));
    toast(err.message);
  }
}

async function decideReviewTarget(payload, cardFeedback) {
  if (!currentWork) return;
  const seq = ++reviewSyncSeq;
  if (cardFeedback) cardFeedback.innerHTML = '';
  const { status, ok, data } = await apiDetailed('/api/works/review/decide', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workId: currentWork.id, ...payload }),
  });
  if (!ok) {
    if (cardFeedback) {
      cardFeedback.append(el('div', {
        class: 'alert-box err',
        text: (status === 409 ? 'Conflito de versão (HTTP 409): ' : 'Bloqueado: ') + (data.error || 'falha na revisão'),
      }));
    }
    if (status === 409) await loadReviewOverview().catch(() => {});
    toast(data.error || 'Falha na revisão');
    return;
  }
  if (seq === reviewSyncSeq) renderReviewPanel(data, data.packageDelivery || null);
  toast('Decisão de revisão registrada.');
}

async function inspectArtifactText(piece, kind, targetPre) {
  if (!currentWork) return;
  targetPre.hidden = false;
  targetPre.textContent = 'Carregando e verificando SHA-256…';
  try {
    const d = await api(
      `/api/works/artifact-text?id=${encodeURIComponent(currentWork.id)}`
      + `&modality=${encodeURIComponent(piece.modality)}`
      + `&profile=${encodeURIComponent(piece.profileId)}`
      + `&kind=${encodeURIComponent(kind)}`
    );
    targetPre.textContent = `Arquivo: ${d.path}\nSHA-256: ${d.sha256}\n\n${d.content}`;
  } catch (err) {
    targetPre.textContent = 'Erro ao carregar artefato: ' + err.message;
  }
}

async function buildPackageZip() {
  if (!currentWork) return;
  const seq = ++reviewSyncSeq;
  const statusBox = $('#r-package-status');
  statusBox.innerHTML = '<p class="muted">Validando integridade e empacotando ZIP…</p>';
  const pieces = [];
  document.querySelectorAll('#r-package-checklist input[data-pkg-type="piece"]:checked').forEach((chk) => {
    pieces.push({
      modality: chk.getAttribute('data-modality'),
      profileId: chk.getAttribute('data-profile'),
      expectedVersionId: chk.getAttribute('data-expected-version') || null,
      expectedDraftFingerprint: chk.getAttribute('data-expected-draft') || null,
    });
  });
  const channels = [];
  document.querySelectorAll('#r-package-checklist input[data-pkg-type="channel"]:checked').forEach((chk) => {
    channels.push({
      profileId: chk.getAttribute('data-profile'),
      expectedCopySha256: chk.getAttribute('data-expected-copy') || null,
    });
  });

  const { status, ok, data } = await apiDetailed('/api/works/package', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workId: currentWork.id, pieces, channels }),
  });
  statusBox.innerHTML = '';
  if (!ok) {
    statusBox.append(el('div', {
      class: 'alert-box err',
      text: (status === 409 ? 'Conflito de versão (HTTP 409): ' : 'Empacotamento bloqueado: ') + (data.error || 'erro'),
    }));
    await loadReviewOverview().catch(() => {});
    toast(data.error || 'Falha ao gerar ZIP');
    return;
  }
  statusBox.append(el('div', { class: 'alert-box ok', text: 'Pacote ZIP de entrega gerado, validado e promovido atomicamente.' }));
  if (seq === reviewSyncSeq) renderReviewPanel(data, data.packageDelivery || null);
  loadWorks().catch(() => {});
  toast('Pacote ZIP de entrega pronto para download.');
}

function renderHistoryDetails(items, isChannel) {
  if (!items || !items.length) return null;
  const box = el('details', { class: 'history-box' }, [
    el('summary', { text: `Histórico de decisões (${items.length})` }),
  ]);
  for (const h of items.slice().reverse()) {
    const ver = isChannel ? `copy ${(h.copySha256 || '').slice(0, 10)}` : `versão ${h.deliveryVersionId || 'n/d'}`;
    box.append(el('div', {
      text: `• ${h.decidedAt || ''} — ${h.decisionLabel || h.decision} [${ver}]` + (h.note ? ` — Nota: ${h.note}` : ''),
    }));
  }
  return box;
}

function renderReviewPanel(review, pkg) {
  const noWork = $('#r-no-work-alert');
  const content = $('#r-work-content');
  if (!currentWork || !review) {
    noWork.hidden = false;
    content.hidden = true;
    reviewState = null;
    syncAstryxReviewPackageState(null, null, null);
    return;
  }
  noWork.hidden = true;
  content.hidden = false;
  reviewState = { ...review, packageDelivery: pkg || null };

  const legacyBanner = $('#r-legacy-banner');
  legacyBanner.innerHTML = '';
  const hasUnlinked = (review.pieces || []).some((p) => p.status === 'unlinked');
  if (review.legacyWork || hasUnlinked) {
    legacyBanner.append(el('div', {
      class: 'alert-box warn',
      text: 'Trabalho legado ou com entrega anterior sem vínculo gravado ao rascunho atual: a ficha iniciou vazia e entregas não vinculadas exigem reexportação pelo Studio antes da aprovação.',
    }));
  }

  const b = (review.editorial && review.editorial.briefing) || {};
  $('#r-brief-objective').value = b.objective || '';
  $('#r-brief-audience').value = b.audience || '';
  $('#r-brief-core').value = b.coreMessage || '';
  $('#r-brief-evidence').value = b.supportEvidence || '';
  $('#r-brief-hook').value = b.hook || '';
  $('#r-brief-script').value = b.scriptSummary || '';
  $('#r-brief-cta').value = b.cta || '';

  // Textos por canal
  const chList = $('#r-channels-list');
  chList.innerHTML = '';
  const channels = review.channels || [];
  if (!channels.length) {
    chList.append(el('p', { class: 'muted', text: 'Nenhum destino selecionado nos rascunhos deste trabalho.' }));
  }
  for (const ch of channels) {
    const card = el('div', { class: 'review-card', 'data-channel-id': ch.profileId });
    const fb = el('div', { class: 'r-ch-feedback' });
    const noteInput = el('input', {
      'data-ch-note': ch.profileId,
      placeholder: 'Observação da revisão do texto do canal (opcional)',
      value: (ch.currentDecision && ch.currentDecision.note) || '',
    });
    const dirtyNote = el('span', { class: 'badge muted', text: 'texto salvo', hidden: 'hidden' });

    const grid = el('div', { class: 'review-grid' }, [
      el('label', {}, ['Título do post (quando aplicável)', el('input', { 'data-ch-field': 'title', value: ch.title || '' })]),
      el('label', {}, ['CTA do canal', el('input', { 'data-ch-field': 'cta', value: ch.cta || '' })]),
      el('label', {}, ['URL de destino', el('input', { 'data-ch-field': 'destinationUrl', value: ch.destinationUrl || '' })]),
      el('label', {}, ['Hashtags (opcional)', el('input', { 'data-ch-field': 'hashtags', value: ch.hashtags || '' })]),
      el('label', { style: 'grid-column: 1 / -1;' }, ['Texto / legenda de publicação', el('textarea', { 'data-ch-field': 'postText', rows: '3' }, ch.postText || '')]),
    ]);
    grid.querySelector('textarea').value = ch.postText || '';
    grid.querySelectorAll('[data-ch-field]').forEach((inp) => {
      inp.addEventListener('input', () => { dirtyNote.hidden = false; dirtyNote.textContent = 'alterado localmente — salve antes de aprovar'; });
    });

    card.append(
      el('div', { class: 'review-card-head' }, [
        el('div', {}, [
          el('strong', { text: `${ch.profileLabel || ch.profileId} ` }),
          el('span', { class: 'muted', text: `(${ch.profileId}${ch.network ? ' · ' + ch.network : ''})` }),
        ]),
        el('div', {}, [
          el('span', { class: 'badge ' + reviewStatusClass(ch.status), text: ch.statusLabel }),
          el('span', { class: 'badge muted', text: 'copy ' + (ch.copySha256 || '').slice(0, 8) }),
          dirtyNote,
        ]),
      ]),
      el('p', { class: 'muted', text: ch.readyReason || '' }),
      grid,
      el('div', { class: 'row', style: 'margin-top: 8px;' }, [
        el('button', {
          class: 'secondary',
          'data-ch-action': 'save',
          text: 'Salvar texto deste canal',
          onclick: () => saveSingleChannelCopy(card),
        }),
        noteInput,
        el('button', {
          class: 'ok-btn',
          'data-ch-action': 'approve',
          text: 'Aprovar texto do canal',
          onclick: () => decideReviewTarget({
            targetType: 'channel',
            profileId: ch.profileId,
            expectedCopySha256: ch.copySha256,
            decision: 'approved_for_local_delivery',
            note: noteInput.value,
          }, fb),
        }),
        el('button', {
          class: 'warn-btn',
          'data-ch-action': 'changes',
          text: 'Pedir ajuste no texto',
          onclick: () => decideReviewTarget({
            targetType: 'channel',
            profileId: ch.profileId,
            expectedCopySha256: ch.copySha256,
            decision: 'changes_requested',
            note: noteInput.value,
          }, fb),
        }),
      ]),
      fb,
    );
    const hist = renderHistoryDetails(ch.decisionHistory, true);
    if (hist) card.append(hist);
    chList.append(card);
  }

  // Peças exportadas
  const pList = $('#r-pieces-list');
  pList.innerHTML = '';
  const pieces = review.pieces || [];
  if (!pieces.length) {
    pList.append(el('p', { class: 'muted', text: 'Nenhuma peça selecionada ou exportada ainda.' }));
  }
  for (const p of pieces) {
    const card = el('div', { class: 'review-card', 'data-piece-key': p.pieceKey });
    const fb = el('div', { class: 'r-piece-feedback' });
    const m = p.metrics || {};
    const metricBits = [];
    if (m.width && m.height) metricBits.push(`${m.width}×${m.height}`);
    if (m.fps) metricBits.push(`${m.fps} fps`);
    if (m.durationSec != null) metricBits.push(`${Number(m.durationSec).toFixed(1)}s`);
    if (m.audioStreams != null) metricBits.push(`${m.audioStreams} áudios`);
    if (m.cardCount != null) metricBits.push(`${m.cardCount} cards`);
    if (p.deliveryVersionId) metricBits.push(`versão ${p.deliveryVersionId}`);
    if (m.videoSha256) metricBits.push(`MP4 sha256 ${m.videoSha256.slice(0, 10)}`);

    card.append(
      el('div', { class: 'review-card-head' }, [
        el('div', {}, [
          el('span', { class: 'badge muted', text: p.modalityLabel }),
          el('strong', { text: `${p.profileLabel || p.profileId} ` }),
          el('span', { class: 'muted', text: `(${p.profileId})` }),
        ]),
        el('span', { class: 'badge ' + reviewStatusClass(p.status), text: p.statusLabel }),
      ]),
      el('p', { class: 'muted', text: p.readyReason || '' }),
      metricBits.length ? el('p', { class: 'timeline', text: metricBits.join(' · ') }) : null,
    );

    if (p.lastAttempt && p.lastAttempt.status && p.lastAttempt.status !== 'completed') {
      card.append(el('div', {
        class: 'alert-box err',
        text: `Última tentativa (${p.lastAttempt.status}): ${p.lastAttempt.error || 'erro na exportação'}. Última entrega válida e decisões anteriores foram preservadas.`,
      }));
    }
    if (p.integrityErrors && p.integrityErrors.length) {
      card.append(el('div', {
        class: 'alert-box err',
        text: 'Integridade: ' + p.integrityErrors.join('; '),
      }));
    }
    if (p.mediaOrigins && p.mediaOrigins.length) {
      const originLabels = {
        'imported-manual': 'importação manual',
        'external-tool': 'ferramenta externa (importada)',
        'generated-simulator': 'ilustração gerada (simulador)',
        'generated-google-gemini': 'ilustração gerada (Google Gemini)',
        'synthetic-demo': 'fictícia de demonstração',
        'studio-work': 'arquivo do trabalho',
        'screenshot': 'captura / evidência funcional',
      };
      const originLine = p.mediaOrigins.map((mo) => {
        const label = originLabels[mo.origin] || mo.origin || 'local';
        const kind = String(mo.origin || '').startsWith('generated-') ? ' [ilustração gerada, não é captura/evidência]' : '';
        return `${mo.mediaId || 'asset'}: ${label}${kind} (${mo.license || 'n/d'})`;
      }).join(' | ');
      card.append(el('p', { class: 'muted', text: 'Origens de mídia: ' + originLine }));
    }

    if (p.modality === 'carousel' && p.cards && p.cards.length) {
      const strip = el('div', { class: 'carousel-strip' });
      for (const c of p.cards) {
        strip.append(el('div', { class: 'carousel-strip-item' }, [
          c.ok ? el('img', { src: `${c.url}&v=${encodeURIComponent(c.sha256 || '')}`, alt: c.file || '' }) : el('div', { class: 'badge err', text: 'ausente' }),
          el('div', { text: `#${c.order} ${c.file || c.id}` }),
        ]));
      }
      card.append(strip);
    } else if (p.artifacts && p.artifacts.video && p.artifacts.video.ok) {
      const vUrl = `${p.artifacts.video.url}&v=${encodeURIComponent(p.metrics?.videoSha256 || p.deliveryVersionId || '')}`;
      card.append(el('video', { controls: '', preload: 'metadata', src: vUrl }));
      const viewer = el('pre', { class: 'artifact-viewer', hidden: 'hidden' });
      card.append(
        el('div', { class: 'row' }, [
          el('button', { class: 'secondary', text: 'Inspecionar legendas (.srt)', onclick: () => inspectArtifactText(p, 'srt', viewer) }),
          el('button', { class: 'secondary', text: 'Inspecionar narração (.txt)', onclick: () => inspectArtifactText(p, 'narration', viewer) }),
        ]),
        viewer,
      );
    }

    const noteInput = el('input', {
      'data-piece-note': p.pieceKey,
      placeholder: 'Observação da revisão desta peça (opcional)',
      value: (p.currentDecision && p.currentDecision.note) || '',
    });
    card.append(
      el('div', { class: 'row', style: 'margin-top: 8px;' }, [
        noteInput,
        el('button', {
          class: 'ok-btn',
          'data-piece-action': 'approve',
          text: 'Aprovar para entrega local',
          disabled: p.status === 'no_delivery' ? 'disabled' : null,
          onclick: () => decideReviewTarget({
            targetType: 'piece',
            modality: p.modality,
            profileId: p.profileId,
            expectedVersionId: p.deliveryVersionId,
            expectedDraftFingerprint: p.currentDraftFingerprint,
            decision: 'approved_for_local_delivery',
            note: noteInput.value,
          }, fb),
        }),
        el('button', {
          class: 'warn-btn',
          'data-piece-action': 'changes',
          text: 'Pedir ajuste',
          disabled: p.status === 'no_delivery' ? 'disabled' : null,
          onclick: () => decideReviewTarget({
            targetType: 'piece',
            modality: p.modality,
            profileId: p.profileId,
            expectedVersionId: p.deliveryVersionId,
            expectedDraftFingerprint: p.currentDraftFingerprint,
            decision: 'changes_requested',
            note: noteInput.value,
          }, fb),
        }),
      ]),
      fb,
    );
    const hist = renderHistoryDetails(p.decisionHistory, false);
    if (hist) card.append(hist);
    pList.append(card);
  }

  if (isAstryxReviewPackageActive()) {
    syncAstryxReviewPackageState(currentWork.id, review, pkg || null);
    return;
  }

  // Checklist do ZIP
  const chkBox = $('#r-package-checklist');
  chkBox.innerHTML = '';
  for (const p of pieces) {
    const chk = el('input', {
      type: 'checkbox',
      'data-pkg-type': 'piece',
      'data-modality': p.modality,
      'data-profile': p.profileId,
      'data-expected-version': p.deliveryVersionId || '',
      'data-expected-draft': p.currentDraftFingerprint || '',
      checked: p.readyForPackage ? 'checked' : null,
    });
    chkBox.append(el('div', { class: 'checklist-row' }, [
      el('label', { class: 'inline-check' }, [chk, el('span', { text: `[${p.modalityLabel}] ${p.profileId}` })]),
      el('div', {}, [
        el('span', { class: 'badge ' + reviewStatusClass(p.status), text: p.readyForPackage ? 'Pronto' : p.statusLabel }),
        el('span', { class: 'muted', text: p.readyReason }),
      ]),
    ]));
  }
  for (const ch of channels) {
    const chk = el('input', {
      type: 'checkbox',
      'data-pkg-type': 'channel',
      'data-profile': ch.profileId,
      'data-expected-copy': ch.copySha256 || '',
      checked: ch.readyForPackage ? 'checked' : null,
    });
    chkBox.append(el('div', { class: 'checklist-row' }, [
      el('label', { class: 'inline-check' }, [chk, el('span', { text: `[Texto de canal] ${ch.profileId}` })]),
      el('div', {}, [
        el('span', { class: 'badge ' + reviewStatusClass(ch.status), text: ch.readyForPackage ? 'Pronto' : ch.statusLabel }),
        el('span', { class: 'muted', text: ch.readyReason }),
      ]),
    ]));
  }

  // Resultado persistido do pacote ZIP
  const resBox = $('#r-package-result');
  resBox.innerHTML = '';
  if (pkg && pkg.lastAttempt && pkg.lastAttempt.status === 'failed') {
    resBox.append(el('div', {
      class: 'alert-box err',
      text: `Última tentativa de empacotamento ZIP falhou: ${pkg.lastAttempt.error || 'erro'}. O último pacote ZIP válido (quando existente) foi preservado.`,
    }));
  }
  if (pkg && pkg.available && pkg.lastValidDelivery) {
    const lv = pkg.lastValidDelivery;
    const man = pkg.manifest || {};
    resBox.append(el('div', { class: 'review-card' }, [
      el('div', { class: 'review-card-head' }, [
        el('strong', { text: `Pacote ZIP promovido: ${lv.packageId}` }),
        el('span', { class: 'badge ok', text: 'ZIP íntegro' }),
      ]),
      el('p', {
        class: 'timeline',
        text: `${lv.zipBytes} bytes · SHA-256 ${lv.zipSha256} · Modalidades: ${(lv.modalities || []).join(', ') || 'apenas textos'} · Destinos: ${(lv.profiles || []).join(', ')}`,
      }),
      el('p', {}, [
        el('a', {
          id: 'btn-r-download-zip',
          href: pkg.downloadUrl,
          download: `${currentWork.id}-${lv.packageId}.zip`,
          text: `Baixar ZIP de entrega (${lv.packageId}.zip)`,
        }),
      ]),
      el('pre', { text: JSON.stringify(man.files || [], null, 2) }),
    ]));
  } else if (pkg && pkg.lastValidDelivery && !pkg.available) {
    resBox.append(el('div', {
      class: 'alert-box err',
      text: 'Pacote ZIP anterior indisponível: ' + (pkg.zipError || 'erro de integridade'),
    }));
  } else {
    resBox.append(el('p', { class: 'muted', text: 'Nenhum pacote ZIP de entrega gerado ainda neste trabalho.' }));
  }
}

// ---- Produção em Lote e Fila Persistente ----
let queuePollTimer = null;

function queueStatusBadge(status) {
  const map = {
    queued: { cls: 'muted', label: 'Na fila' },
    running: { cls: 'info', label: 'Em execução' },
    completed: { cls: 'ok', label: 'Concluído' },
    failed: { cls: 'err', label: 'Falhou' },
    interrupted: { cls: 'warn', label: 'Interrompido' },
    cancelled: { cls: 'muted', label: 'Cancelado' },
  };
  return map[status] || { cls: 'muted', label: status };
}

let activeBatchModalId = 0;
let activeBatchKeyHandler = null;
let lastBatchFocusEl = null;

function closeBatchExportModal() {
  activeBatchModalId += 1;
  if (activeBatchKeyHandler) {
    document.removeEventListener('keydown', activeBatchKeyHandler);
    activeBatchKeyHandler = null;
  }
  const root = $('#batch-dialog-root');
  if (root) root.innerHTML = '';
  if (lastBatchFocusEl && lastBatchFocusEl.isConnected && typeof lastBatchFocusEl.focus === 'function') {
    lastBatchFocusEl.focus();
  }
  lastBatchFocusEl = null;
}

function batchTupleKey(item) {
  return `${item.workId || ''}\u0000${item.modality || ''}\u0000${item.profileId || ''}`;
}

function renderBatchPreflightDetail(item) {
  const isReady = item.status === 'ready';
  const detail = el('div', {
    class: `batch-preflight-detail ${isReady ? 'ready' : 'blocked'}`,
    'data-preflight-status': item.status,
  });
  const pending = Array.isArray(item.pendingChecks) ? item.pendingChecks : [];
  const warnings = Array.isArray(item.warnings) ? item.warnings : [];
  const blockers = Array.isArray(item.blockers) ? item.blockers : [];
  const actions = Array.isArray(item.suggestedActions) ? item.suggestedActions : [];

  let badgeLabel = isReady ? 'Pronto' : 'Bloqueado';
  if (isReady && pending.length) badgeLabel = 'Pronto (com pendências)';

  detail.append(el('div', {}, [
    el('span', { class: `badge ${isReady ? 'ok' : 'err'}`, text: badgeLabel }),
    el('span', { text: ` ${item.summary || ''}` }),
  ]));

  if (blockers.length) {
    const ul = el('ul');
    for (const b of blockers) {
      const subj = b.subject ? ` (${b.subject})` : '';
      ul.append(el('li', { text: `[${b.code || 'BLOCKED'}]${subj}: ${b.message || ''}` }));
    }
    detail.append(ul);
  }
  if (warnings.length) {
    const ul = el('ul');
    for (const w of warnings) {
      const subj = w.subject ? ` (${w.subject})` : '';
      ul.append(el('li', { text: `Aviso [${w.code || 'WARNING'}]${subj}: ${w.message || ''}` }));
    }
    detail.append(ul);
  }
  if (pending.length) {
    const ul = el('ul');
    for (const p of pending) {
      ul.append(el('li', { text: `Pendente [${p.code || 'PENDING'}]: ${p.message || ''}` }));
    }
    detail.append(ul);
  }
  if (actions.length) {
    detail.append(el('div', {
      class: 'batch-preflight-actions',
      text: `Próximo passo: ${actions.join(' ')}`,
    }));
  }
  return detail;
}

async function openBatchExportModal() {
  const workIds = Array.from(selectedBatchWorks);
  if (!workIds.length) {
    toast('Selecione pelo menos um trabalho na tabela para exportar em lote.');
    return;
  }
  lastBatchFocusEl = document.activeElement;
  activeBatchModalId += 1;
  const modalId = activeBatchModalId;
  const plan = await post('/api/queue/plan', { workIds });
  if (activeBatchModalId !== modalId) return;

  const root = $('#batch-dialog-root');
  if (!root) return;
  if (activeBatchKeyHandler) {
    document.removeEventListener('keydown', activeBatchKeyHandler);
    activeBatchKeyHandler = null;
  }
  root.innerHTML = '';

  const isCurrentModal = () => activeBatchModalId === modalId && Boolean(document.getElementById('batch-export-dialog'));
  let busyState = false;
  let lastEnqueueAttempt = { sig: null, key: null };

  const overlay = el('div', { class: 'media-dialog-overlay', id: 'batch-export-overlay' });
  const dialog = el('div', {
    class: 'media-dialog',
    id: 'batch-export-dialog',
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'batch-export-title',
    tabindex: '-1',
  });
  const head = el('div', { class: 'media-dialog-head' }, [
    el('h2', { id: 'batch-export-title', style: 'margin:0;', text: `Exportar em lote (${workIds.length} trabalho(s))` }),
    el('button', { id: 'btn-batch-close', class: 'secondary', text: 'Fechar', onclick: closeBatchExportModal }),
  ]);

  const body = el('div', { class: 'media-dialog-body' });
  const unsavedBox = el('div', { id: 'batch-unsaved-box' });
  const preflightSummaryBox = el('div', { id: 'batch-preflight-summary', role: 'status', 'aria-live': 'polite' });
  const fb = el('div', { id: 'batch-confirm-feedback', role: 'status', 'aria-live': 'polite' });
  const rowMap = new Map();

  const clearPreflightDisplay = () => {
    preflightSummaryBox.innerHTML = '';
    for (const row of rowMap.values()) {
      const slot = row.querySelector('.batch-preflight-slot');
      if (slot) slot.innerHTML = '';
    }
  };

  const renderUnsaved = () => {
    unsavedBox.innerHTML = '';
    if (hasUnsavedWorkChanges()) {
      unsavedBox.append(el('div', { class: 'alert-box warn' }, [
        el('div', { text: `Há alterações não salvas no trabalho ativo (${currentWork.id}). A fila congela a versão salva em disco.` }),
        el('div', { class: 'row', style: 'margin-top:8px; margin-bottom:0;' }, [
          el('button', {
            id: 'btn-batch-save-active',
            class: 'ok-btn',
            text: 'Salvar trabalho ativo antes de confirmar',
            onclick: async () => {
              await saveWork();
              if (!isCurrentModal()) return;
              clearPreflightDisplay();
              closeBatchExportModal();
              await openBatchExportModal();
            },
          }),
        ]),
      ]));
    }
  };
  renderUnsaved();

  const labelInput = el('input', {
    id: 'batch-label-input',
    type: 'text',
    placeholder: `Lote (${workIds.length} trabalho(s))`,
  });

  const groupsBox = el('div', { id: 'batch-options-groups' });
  for (const w of (plan.works || [])) {
    const group = el('div', { class: 'batch-work-group', 'data-batch-work-id': w.workId }, [
      el('div', { style: 'margin-bottom:6px;' }, [
        el('strong', { text: `${w.title} ` }),
        el('span', { class: 'muted', text: `(${w.workId} · ${w.project})` }),
      ]),
    ]);
    for (const opt of (w.options || [])) {
      const cb = el('input', {
        type: 'checkbox',
        class: 'batch-opt-cb',
        'data-work-id': opt.workId,
        'data-modality': opt.modality,
        'data-profile-id': opt.profileId,
      });
      cb.checked = Boolean(opt.available && opt.selectedByDefault);
      cb.disabled = !opt.available;
      const row = el('div', {
        class: 'batch-option-row',
        'data-work-id': opt.workId,
        'data-modality': opt.modality,
        'data-profile-id': opt.profileId,
      }, [
        el('label', { class: 'inline-check batch-option-main' }, [
          cb,
          el('span', { class: 'badge muted', text: opt.modalityLabel }),
          el('strong', { text: opt.profileLabel || opt.profileId }),
          el('span', { class: 'muted', text: ` (${opt.profileId})` }),
        ]),
        opt.available
          ? el('span', { class: 'badge ok', text: 'disponível' })
          : el('span', { class: 'badge err', text: opt.unavailableReason || 'indisponível' }),
        el('div', { class: 'batch-preflight-slot', style: 'flex-basis:100%;' }),
      ]);
      rowMap.set(batchTupleKey(opt), row);
      group.append(row);
    }
    groupsBox.append(group);
  }

  const getSelectedTuples = () => Array.from(dialog.querySelectorAll('.batch-opt-cb:checked')).map((cb) => ({
    workId: cb.getAttribute('data-work-id'),
    modality: cb.getAttribute('data-modality'),
    profileId: cb.getAttribute('data-profile-id'),
  }));

  const selectionSignature = (items, label) => {
    const sorted = items.map((it) => batchTupleKey(it)).sort().join('\n');
    return `${sorted}\u0001${label}`;
  };

  const validateAndRenderPreflight = (selected, res) => {
    if (!res || res.ok !== true || res.schemaVersion !== 1 || !Array.isArray(res.items)) {
      return { valid: false, error: 'Resposta inválida do pré-voo (formato ou versão desconhecida). Tente novamente.' };
    }
    const expectedKeys = new Set(selected.map((it) => batchTupleKey(it)));
    const byKey = new Map();
    for (const item of res.items) {
      if (!item || typeof item !== 'object') {
        return { valid: false, error: 'Resposta inválida do pré-voo (item malformado).' };
      }
      const key = batchTupleKey(item);
      if (!expectedKeys.has(key) || byKey.has(key)) {
        return { valid: false, error: 'Resposta do pré-voo não corresponde exatamente à seleção atual. Tente novamente.' };
      }
      byKey.set(key, item);
    }
    if (byKey.size !== expectedKeys.size) {
      return { valid: false, error: 'Resposta do pré-voo incompleta para a seleção atual. Tente novamente.' };
    }

    clearPreflightDisplay();
    let readyCount = 0;
    let blockedCount = 0;
    let pendingCount = 0;
    for (const key of expectedKeys) {
      const item = byKey.get(key);
      if (item.status === 'ready') readyCount += 1;
      else blockedCount += 1;
      if (Array.isArray(item.pendingChecks) && item.pendingChecks.length) pendingCount += 1;
      const row = rowMap.get(key);
      const slot = row?.querySelector('.batch-preflight-slot');
      if (slot) slot.append(renderBatchPreflightDetail(item));
    }

    const summaryCls = blockedCount > 0 ? 'err' : (pendingCount > 0 ? 'warn' : 'ok');
    let summaryText = `Pré-voo: ${readyCount} destino(s) pronto(s), ${blockedCount} bloqueado(s).`;
    if (blockedCount === 0 && pendingCount > 0) {
      summaryText = `Pré-voo: ${readyCount} destino(s) pronto(s) nas checagens executadas (${pendingCount} com checagens pendentes).`;
    }
    preflightSummaryBox.append(el('div', { class: `alert-box ${summaryCls}`, text: summaryText }));
    return { valid: true, allReady: blockedCount === 0 && res.ready === true, readyCount, blockedCount };
  };

  const verifyBtn = el('button', {
    id: 'btn-batch-verify',
    class: 'secondary',
    text: 'Verificar seleção',
  });
  const confirmBtn = el('button', {
    id: 'btn-batch-confirm',
    class: 'ok-btn',
    text: 'Confirmar e enfileirar lote',
  });

  const setBusy = (busy, message = '') => {
    busyState = busy;
    verifyBtn.disabled = busy;
    confirmBtn.disabled = busy;
    if (busy && message) {
      preflightSummaryBox.innerHTML = '';
      preflightSummaryBox.append(el('div', { class: 'alert-box warn', text: message }));
    }
  };

  verifyBtn.onclick = async () => {
    if (busyState) return;
    fb.innerHTML = '';
    const selected = getSelectedTuples();
    if (!selected.length) {
      fb.append(el('div', { class: 'alert-box err', text: 'Selecione pelo menos uma peça disponível.' }));
      return;
    }
    setBusy(true, 'Verificando destinos selecionados...');
    try {
      const res = await post('/api/queue/preflight', { items: selected });
      if (!isCurrentModal()) return;
      const check = validateAndRenderPreflight(selected, res);
      if (!check.valid) {
        preflightSummaryBox.innerHTML = '';
        preflightSummaryBox.append(el('div', { class: 'alert-box err', text: check.error }));
      }
    } catch (err) {
      if (!isCurrentModal()) return;
      preflightSummaryBox.innerHTML = '';
      preflightSummaryBox.append(el('div', {
        class: 'alert-box err',
        text: `Falha ao consultar pré-voo (${err.message}). Verifique a conexão e tente novamente.`,
      }));
    } finally {
      if (isCurrentModal()) setBusy(false);
    }
  };

  confirmBtn.onclick = async () => {
    if (busyState) return;
    fb.innerHTML = '';
    const selected = getSelectedTuples();
    const label = labelInput.value.trim();
    if (!selected.length) {
      fb.append(el('div', { class: 'alert-box err', text: 'Selecione pelo menos uma peça disponível.' }));
      return;
    }
    setBusy(true, 'Validando seleção no pré-voo antes de enfileirar...');
    let preflightRes;
    try {
      preflightRes = await post('/api/queue/preflight', { items: selected });
    } catch (err) {
      if (!isCurrentModal()) return;
      preflightSummaryBox.innerHTML = '';
      fb.append(el('div', {
        class: 'alert-box err',
        text: `Não foi possível validar o pré-voo (${err.message}). Tente confirmar novamente.`,
      }));
      setBusy(false);
      return;
    }
    if (!isCurrentModal()) return;

    const check = validateAndRenderPreflight(selected, preflightRes);
    if (!check.valid) {
      preflightSummaryBox.innerHTML = '';
      fb.append(el('div', { class: 'alert-box err', text: check.error }));
      setBusy(false);
      return;
    }
    if (!check.allReady) {
      fb.append(el('div', {
        class: 'alert-box err',
        text: 'Enfileiramento bloqueado: corrija os impedimentos destacados ou desmarque os itens bloqueados antes de confirmar.',
      }));
      setBusy(false);
      return;
    }

    const sig = selectionSignature(selected, label);
    if (lastEnqueueAttempt.sig !== sig) {
      lastEnqueueAttempt = {
        sig,
        key: `batch-ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      };
    }

    try {
      const res = await post('/api/queue/enqueue', {
        items: selected,
        idempotencyKey: lastEnqueueAttempt.key,
        label: label || undefined,
      });
      const msg = res.deduplicated
        ? `Lote ${res.batch.batchId} já enfileirado (requisição idempotente).`
        : `Lote ${res.batch.batchId} enfileirado (${res.batch.counts.total} peça(s)).`;
      if (isCurrentModal()) {
        closeBatchExportModal();
        toast(msg);
        setMode('queue');
        await loadQueue();
      } else {
        toast(msg);
        loadQueue().catch(() => {});
      }
    } catch (err) {
      if (!isCurrentModal()) return;
      fb.append(el('div', { class: 'alert-box err', text: `Falha ao enfileirar lote: ${err.message}` }));
      setBusy(false);
    }
  };

  activeBatchKeyHandler = (ev) => {
    if (ev.key === 'Escape' && isCurrentModal()) {
      ev.preventDefault();
      closeBatchExportModal();
    }
  };
  document.addEventListener('keydown', activeBatchKeyHandler);

  body.append(
    unsavedBox,
    el('label', {}, ['Nome do lote (opcional)', labelInput]),
    preflightSummaryBox,
    groupsBox,
    fb,
    el('div', { class: 'row', style: 'margin-top:12px;' }, [
      verifyBtn,
      confirmBtn,
      el('button', { id: 'btn-batch-cancel', class: 'secondary', text: 'Cancelar', onclick: closeBatchExportModal }),
    ]),
  );
  dialog.append(head, body);
  overlay.append(dialog);
  root.append(overlay);
  dialog.focus();
}

function scheduleQueuePoll(hasActive) {
  if (queuePollTimer) {
    clearTimeout(queuePollTimer);
    queuePollTimer = null;
  }
  if (hasActive) {
    queuePollTimer = setTimeout(() => {
      loadQueue().catch(() => {});
    }, 1500);
  }
}

async function openQueueWorkReview(workId) {
  await openWork(workId);
  setMode('review');
  await loadReviewOverview();
}

async function cancelQueueItem(itemId) {
  await post('/api/queue/cancel', { itemId });
  toast('Item cancelado na fila.');
  await loadQueue();
}

async function retryQueueItem(itemId, useCurrent = false, feedbackEl = null) {
  try {
    await post('/api/queue/retry', { itemId, useCurrent });
    toast(useCurrent ? 'Item reenfileirado com a versão atual.' : 'Nova tentativa enfileirada com o snapshot anterior.');
    await loadQueue();
  } catch (err) {
    if (err.payload && err.payload.canUseCurrent && feedbackEl) {
      feedbackEl.innerHTML = '';
      feedbackEl.append(el('div', { class: 'alert-box warn' }, [
        el('div', { text: err.message }),
        el('div', { class: 'row', style: 'margin-top:6px; margin-bottom:0;' }, [
          el('button', {
            class: 'ok-btn',
            text: 'Enfileirar versão atual',
            onclick: () => retryQueueItem(itemId, true, feedbackEl),
          }),
        ]),
      ]));
    } else {
      toast(err.message);
    }
  }
}

function bindLegacyQueueEvents() {
  if (isAstryxQueueActive()) return;
  const root = queueLegacyRoot();
  if (!root || !root.childElementCount) return;
  queueEl('#btn-q-refresh')?.addEventListener('click', () => loadQueue().catch((e) => toast(e.message)));
  queueEl('#q-filter-status')?.addEventListener('change', () => loadQueue().catch((e) => toast(e.message)));
  queueEl('#q-filter-work')?.addEventListener('change', () => loadQueue().catch((e) => toast(e.message)));
}

let legacyQueueSeq = 0;

async function loadQueue() {
  if (isAstryxQueueActive()) {
    if (queuePollTimer) {
      clearTimeout(queuePollTimer);
      queuePollTimer = null;
    }
    window.__studioAstryxQueueRefresh?.();
    return;
  }
  const seq = ++legacyQueueSeq;
  const statusFilter = queueEl('#q-filter-status')?.value || '';
  const workFilter = queueEl('#q-filter-work')?.value || '';
  const params = new URLSearchParams();
  if (statusFilter) params.set('status', statusFilter);
  if (workFilter) params.set('workId', workFilter);
  const qs = params.toString() ? '?' + params.toString() : '';
  const data = await api('/api/queue' + qs);
  if (seq !== legacyQueueSeq) return;

  const counts = data.counts || {};
  const pendingCount = (counts.queued || 0) + (counts.running || 0);
  const navBadge = $('#queue-nav-badge');
  if (navBadge) {
    navBadge.textContent = String(pendingCount);
    navBadge.hidden = pendingCount === 0;
  }

  const bar = queueEl('#queue-counts-bar');
  if (bar) {
    bar.innerHTML = '';
    const labels = [
      ['Total', counts.total || 0],
      ['Na fila', counts.queued || 0],
      ['Em execução', counts.running || 0],
      ['Concluídos', counts.completed || 0],
      ['Falhos', counts.failed || 0],
      ['Interrompidos', counts.interrupted || 0],
      ['Cancelados', counts.cancelled || 0],
    ];
    for (const [k, v] of labels) {
      bar.append(el('div', { class: 'queue-count-pill' }, [
        el('span', { class: 'muted', text: `${k}: ` }),
        el('strong', { text: String(v) }),
      ]));
    }
  }

  // Atualiza opcoes do filtro por trabalho preservando selecao atual
  const workSel = queueEl('#q-filter-work');
  if (workSel) {
    const allWorksData = await api('/api/queue');
    if (seq !== legacyQueueSeq) return;
    const seenWorks = new Set();
    for (const it of (allWorksData.items || [])) seenWorks.add(it.workId);
    const prev = workSel.value;
    workSel.innerHTML = '';
    workSel.append(el('option', { value: '', text: 'Todos os trabalhos' }));
    for (const wid of Array.from(seenWorks).sort()) {
      workSel.append(el('option', { value: wid, text: wid }));
    }
    workSel.value = seenWorks.has(prev) ? prev : '';
  }

  const batchesBox = queueEl('#q-batches-list');
  if (batchesBox) {
    batchesBox.innerHTML = '';
    const batches = data.batches || [];
    if (!batches.length) {
      batchesBox.append(el('p', { class: 'muted', text: 'Nenhum lote enfileirado ainda.' }));
    }
    for (const b of batches) {
      const bc = b.counts || {};
      const stInfo = queueStatusBadge(b.batchStatus);
      batchesBox.append(el('div', { class: 'queue-item-card', 'data-batch-id': b.batchId }, [
        el('div', { class: 'queue-item-head' }, [
          el('div', {}, [
            el('strong', { text: `${b.label || b.batchId} ` }),
            el('span', { class: 'muted', text: `(${b.batchId})` }),
          ]),
          el('span', { class: 'badge ' + stInfo.cls, text: stInfo.label }),
        ]),
        el('p', {
          class: 'timeline',
          text: `Total ${bc.total || 0} · Na fila ${bc.queued || 0} · Em execução ${bc.running || 0} · Concluídos ${bc.completed || 0} · Falhos ${bc.failed || 0} · Interrompidos ${bc.interrupted || 0} · Cancelados ${bc.cancelled || 0}`,
        }),
        el('div', { class: 'row', style: 'margin-bottom:0;' }, [
          el('a', {
            href: `/api/queue/batch/summary?id=${encodeURIComponent(b.batchId)}`,
            download: `${b.batchId}-summary.json`,
            text: 'Baixar resumo JSON do lote',
          }),
        ]),
      ]));
    }
  }

  const itemsBox = queueEl('#q-items-list');
  if (itemsBox) {
    itemsBox.innerHTML = '';
    const items = data.items || [];
    if (!items.length) {
      itemsBox.append(el('p', { class: 'muted', text: 'Nenhuma peça corresponde aos filtros atuais.' }));
    }
    for (const it of items) {
      const stInfo = queueStatusBadge(it.status);
      const card = el('div', { class: 'queue-item-card', 'data-queue-item-id': it.itemId });
      const retryFb = el('div', { class: 'q-item-retry-feedback' });
      const actions = [];
      if (it.status === 'queued') {
        actions.push(el('button', {
          class: 'secondary q-btn-cancel',
          text: 'Cancelar',
          onclick: () => cancelQueueItem(it.itemId).catch((e) => toast(e.message)),
        }));
      }
      if (it.status === 'failed' || it.status === 'interrupted') {
        actions.push(el('button', {
          class: 'warn-btn q-btn-retry',
          text: 'Tentar novamente',
          onclick: () => retryQueueItem(it.itemId, false, retryFb),
        }));
        if (it.canUseCurrent) {
          actions.push(el('button', {
            class: 'ok-btn q-btn-retry-current',
            text: 'Enfileirar versão atual',
            onclick: () => retryQueueItem(it.itemId, true, retryFb),
          }));
        }
      }
      actions.push(el('button', {
        class: 'q-btn-open-review',
        text: 'Abrir revisão',
        onclick: () => openQueueWorkReview(it.workId).catch((e) => toast(e.message)),
      }));

      card.append(
        el('div', { class: 'queue-item-head' }, [
          el('div', {}, [
            el('span', { class: 'badge muted', text: it.modalityLabel }),
            el('strong', { text: `${it.workTitle} ` }),
            el('span', { class: 'muted', text: `(${it.workId} · ${it.profileId})` }),
          ]),
          el('span', { class: 'badge ' + stInfo.cls, text: stInfo.label }),
        ]),
        el('p', {
          class: 'timeline',
          text: `Lote ${it.batchId} · Tentativas: ${(it.attempts || []).length}` +
            (it.deliveryVersionId ? ` · Entrega: ${it.deliveryVersionId}` : ''),
        }),
        it.errorMessage ? el('div', { class: 'alert-box ' + (it.status === 'cancelled' ? 'warn' : 'err'), text: it.errorMessage }) : null,
        retryFb,
        el('div', { class: 'row', style: 'margin-bottom:0;' }, actions),
      );
      itemsBox.append(card);
    }
  }

  scheduleQueuePoll(pendingCount > 0 && (!$('#mode-queue').hidden || pendingCount > 0));
}

// ---- Modelos reutilizáveis e variações em série ----

function closeTemplateDialog() {
  const root = $('#template-dialog-root');
  if (root) root.innerHTML = '';
}

function templateDialogShell(title) {
  const root = $('#template-dialog-root');
  root.innerHTML = '';
  const overlay = el('div', { class: 'media-dialog-overlay', id: 'template-dialog-overlay' });
  const dialog = el('div', { class: 'media-dialog', id: 'template-dialog' });
  dialog.append(el('div', { class: 'row', style: 'justify-content: space-between; align-items: center;' }, [
    el('h3', { text: title, style: 'margin: 0;' }),
    el('button', { class: 'secondary', text: 'Fechar', onclick: closeTemplateDialog }),
  ]));
  overlay.append(dialog);
  root.append(overlay);
  return dialog;
}

async function saveWorkAsModel(workId) {
  const dialog = templateDialogShell(`Salvar como modelo — ${workId}`);
  const nameInput = el('input', { type: 'text', id: 'tpl-save-name', placeholder: 'Nome do modelo (ex.: Agenda semanal)' });
  const labelInput = el('input', { type: 'text', id: 'tpl-save-label', placeholder: 'Rótulo da revisão (opcional)' });
  const existing = await api('/api/templates');
  const select = el('select', { id: 'tpl-save-target' }, [
    el('option', { value: '', text: 'Novo modelo' }),
    ...(existing.templates || []).map((t) => el('option', { value: t.id, text: `${t.name} (${t.id}) — nova revisão` })),
  ]);
  const fb = el('div', { id: 'tpl-save-feedback' });
  dialog.append(
    el('p', { class: 'muted', text: 'Captura a versão salva do trabalho: cortes, destinos, enquadramentos, estilo, Motion, ficha editorial e mídias com origem, licença e SHA-256. A revisão é imutável.' }),
    el('label', {}, ['Nome do modelo', nameInput]),
    el('label', {}, ['Modelo existente (opcional)', select]),
    el('label', {}, ['Rótulo da revisão', labelInput]),
    fb,
    el('button', {
      id: 'btn-tpl-save-confirm',
      text: 'Salvar modelo',
      onclick: async () => {
        fb.innerHTML = '';
        try {
          const res = await post('/api/templates/save', {
            workId,
            name: nameInput.value.trim(),
            templateId: select.value || undefined,
            label: labelInput.value.trim() || undefined,
          });
          toast(`Modelo ${res.template.id} salvo (${res.revisionId}).`);
          closeTemplateDialog();
        } catch (e) {
          fb.append(el('div', { class: 'alert-box err', text: e.message }));
        }
      },
    }),
  );
}

async function duplicateWorkDialog(workId) {
  const dialog = templateDialogShell(`Duplicar como rascunho — ${workId}`);
  const idInput = el('input', { type: 'text', id: 'tpl-dup-id', value: `${workId}-copia` });
  const nameInput = el('input', { type: 'text', id: 'tpl-dup-name', placeholder: 'Nome do novo trabalho (opcional)' });
  const fb = el('div', { id: 'tpl-dup-feedback' });
  dialog.append(
    el('p', { class: 'muted', text: 'Cria um trabalho novo a partir da versão salva, sem exigir modelo permanente. O novo trabalho começa com ficha própria, revisão em aberto e entregas vazias.' }),
    el('label', {}, ['Novo ID (kebab-case)', idInput]),
    el('label', {}, ['Nome', nameInput]),
    fb,
    el('button', {
      id: 'btn-tpl-dup-confirm',
      text: 'Duplicar trabalho',
      onclick: async () => {
        fb.innerHTML = '';
        try {
          const res = await post('/api/works/duplicate', {
            workId, newId: idInput.value.trim(), name: nameInput.value.trim() || undefined,
          });
          toast(`Trabalho duplicado: ${res.work.id}`);
          closeTemplateDialog();
          loadWorks().catch(() => {});
        } catch (e) {
          fb.append(el('div', { class: 'alert-box err', text: e.message }));
        }
      },
    }),
  );
}

async function openTemplateCreateDialog() {
  const dialog = templateDialogShell('Criar a partir de modelo');
  const data = await api('/api/templates');
  const templates = data.templates || [];
  if (!templates.length) {
    dialog.append(el('div', { class: 'alert-box warn', text: 'Nenhum modelo salvo ainda. Use "Salvar como modelo" em um trabalho da lista.' }));
    return;
  }
  const state = {
    templateId: templates[0].id,
    revisionId: (templates[0].revisions || [])[0]?.revisionId || '',
    rows: [{ id: '', name: '', title: '', hook: '', cta: '' }],
    planned: false,
    idempotencyKey: `tpl-ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  };

  const tplSelect = el('select', { id: 'tpl-create-template' },
    templates.map((t) => el('option', { value: t.id, text: `${t.name} (${t.id})` })));
  const revSelect = el('select', { id: 'tpl-create-revision' });
  const rowsBox = el('div', { id: 'tpl-create-rows' });
  const planBox = el('div', { id: 'tpl-create-plan' });
  const resultBox = el('div', { id: 'tpl-create-results' });
  const fb = el('div', { id: 'tpl-create-feedback' });
  const confirmBtn = el('button', { id: 'btn-tpl-create-confirm', text: 'Confirmar criação', disabled: 'disabled' });

  function fillRevisions() {
    const tpl = templates.find((t) => t.id === state.templateId);
    revSelect.innerHTML = '';
    for (const rev of (tpl?.revisions || []).slice().reverse()) {
      revSelect.append(el('option', {
        value: rev.revisionId,
        text: `${rev.revisionId} — ${rev.label || ''} (${rev.createdAt || ''})`,
      }));
    }
    state.revisionId = revSelect.value || '';
  }

  function invalidatePlan() {
    state.planned = false;
    confirmBtn.setAttribute('disabled', 'disabled');
    planBox.innerHTML = '';
  }

  function renderRows() {
    rowsBox.innerHTML = '';
    state.rows.forEach((row, i) => {
      const mkInput = (key, label, placeholder) => el('label', {}, [
        label,
        el('input', {
          type: 'text', value: row[key], placeholder: placeholder || 'herda do modelo',
          oninput: (e) => { row[key] = e.target.value; invalidatePlan(); },
        }),
      ]);
      rowsBox.append(el('div', { class: 'batch-work-group', 'data-tpl-row': String(i) }, [
        el('div', { class: 'row', style: 'justify-content: space-between;' }, [
          el('strong', { text: `Variação ${i + 1}` }),
          el('button', {
            class: 'secondary', text: 'Remover linha',
            onclick: () => { state.rows.splice(i, 1); renderRows(); invalidatePlan(); },
          }),
        ]),
        mkInput('id', 'Novo ID (kebab-case)', 'ex.: agenda-semana-42'),
        mkInput('name', 'Nome do trabalho'),
        mkInput('title', 'Título da peça'),
        mkInput('hook', 'Gancho da ficha'),
        mkInput('cta', 'CTA da ficha'),
      ]));
    });
  }

  tplSelect.addEventListener('change', () => {
    state.templateId = tplSelect.value;
    fillRevisions();
    invalidatePlan();
  });
  revSelect.addEventListener('change', () => {
    state.revisionId = revSelect.value;
    invalidatePlan();
  });

  async function runPlan() {
    fb.innerHTML = '';
    planBox.innerHTML = '';
    resultBox.innerHTML = '';
    const res = await post('/api/templates/plan', {
      templateId: state.templateId, revisionId: state.revisionId, rows: state.rows,
    });
    if ((res.profileAdjustments || []).length) {
      planBox.append(el('div', {
        class: 'alert-box warn',
        text: 'Perfis que exigem ajuste: ' + res.profileAdjustments.map((a) => `${a.profileId} (${a.modality}): ${a.reason}`).join('; '),
      }));
    }
    let allOk = true;
    for (const plan of res.plans || []) {
      const card = el('div', { class: 'batch-work-group', 'data-tpl-plan-row': String(plan.row) });
      card.append(el('div', {}, [
        el('span', { class: 'badge ' + (plan.ok ? 'ok' : 'err'), text: plan.ok ? 'pronta' : 'bloqueada' }),
        el('strong', { text: ` ${plan.id || '(sem id)'}` }),
      ]));
      const changes = plan.changes || {};
      const summary = Object.entries(changes)
        .map(([k, c]) => {
          const val = c.effective ?? '';
          return c.changed ? `${k}: "${c.inherited ?? ''}" → "${val}"` : `${k}: herdado ("${val}")`;
        })
        .join(' · ');
      card.append(el('p', { class: 'muted', text: summary }));
      for (const c of [...(plan.conflicts || []), ...(plan.conditions || [])]) {
        card.append(el('div', { class: 'alert-box err', text: `${c.code}: ${c.message}` }));
        allOk = false;
      }
      if (!plan.ok && !(plan.conflicts || []).length && !(plan.conditions || []).length) allOk = false;
      planBox.append(card);
    }
    state.planned = true;
    if (allOk && (res.plans || []).length) confirmBtn.removeAttribute('disabled');
  }

  async function runCreate() {
    fb.innerHTML = '';
    resultBox.innerHTML = '';
    const res = await post('/api/templates/create', {
      templateId: state.templateId, revisionId: state.revisionId,
      rows: state.rows, idempotencyKey: state.idempotencyKey,
    });
    const createdIds = [];
    for (const c of res.creations || []) {
      const card = el('div', { class: 'batch-work-group', 'data-tpl-result-row': String(c.row) });
      if (c.status === 'created') {
        createdIds.push(c.id);
        card.append(el('div', {}, [
          el('span', { class: 'badge ok', text: 'criado' }),
          el('strong', { text: ` ${c.id} — ${c.name || ''}` }),
        ]));
        card.append(el('div', { class: 'row' }, [
          el('button', {
            text: 'Abrir trabalho',
            onclick: () => {
              closeTemplateDialog();
              openWork(c.id).then(() => setMode('video')).catch((e) => toast(e.message));
            },
          }),
        ]));
      } else {
        card.append(el('div', {}, [
          el('span', { class: 'badge err', text: 'falhou' }),
          el('strong', { text: ` ${c.id || '(sem id)'}` }),
        ]));
        card.append(el('div', { class: 'alert-box err', text: `${c.error?.code || ''}: ${c.error?.message || ''}` }));
      }
      resultBox.append(card);
    }
    if (res.deduplicated) {
      fb.append(el('div', { class: 'alert-box warn', text: 'Confirmação repetida: os mesmos trabalhos foram devolvidos (idempotente).' }));
    }
    if (createdIds.length) {
      resultBox.append(el('button', {
        id: 'btn-tpl-send-queue',
        text: `Enviar para a Fila de Produção (${createdIds.length})`,
        onclick: () => {
          selectedBatchWorks.clear();
          createdIds.forEach((id) => selectedBatchWorks.add(id));
          updateBatchSelectionCount();
          closeTemplateDialog();
          openBatchExportModal().catch((e) => toast(e.message));
        },
      }));
      resultBox.append(el('p', { class: 'muted', text: 'A criação termina em rascunhos locais prontos para edição. O envio à fila reutiliza o planejamento e a confirmação de destinos existentes.' }));
    }
    loadWorks().catch(() => {});
  }

  dialog.append(
    el('label', {}, ['Modelo', tplSelect]),
    el('label', {}, ['Revisão do modelo', revSelect]),
    el('p', { class: 'muted', text: 'Campos em branco herdam o valor daquela revisão do modelo. O plano mostra as mudanças e conflitos por linha sem criar arquivos.' }),
    rowsBox,
    el('div', { class: 'row' }, [
      el('button', {
        class: 'secondary', id: 'btn-tpl-add-row', text: 'Adicionar linha de variação',
        onclick: () => { state.rows.push({ id: '', name: '', title: '', hook: '', cta: '' }); renderRows(); invalidatePlan(); },
      }),
      el('button', {
        id: 'btn-tpl-plan', text: 'Planejar variações',
        onclick: () => runPlan().catch((e) => fb.append(el('div', { class: 'alert-box err', text: e.message }))),
      }),
      confirmBtn,
    ]),
    planBox,
    fb,
    resultBox,
  );
  confirmBtn.addEventListener('click', () => runCreate().catch((e) => fb.append(el('div', { class: 'alert-box err', text: e.message }))));
  fillRevisions();
  renderRows();
}

// ---- Conexões de texto e imagem ----

let connectionsCache = null;

function closeConnectionDialog() {
  const root = $('#conn-dialog-root');
  if (root) root.innerHTML = '';
}

async function loadConnections() {
  const data = await api('/api/connections');
  connectionsCache = data;
  const banner = $('#conn-store-banner');
  const backend = data.storeBackend;
  banner.textContent = backend === 'windows-credential-manager'
    ? 'Cofre de credenciais: Windows Credential Manager desta estação.'
    : backend === 'simulated'
      ? 'Cofre de credenciais: backend SIMULADO (apenas testes/demonstração).'
      : 'Cofre de credenciais indisponível nesta estação — use conexões por variável de ambiente.';
  banner.className = backend === 'unavailable' ? 'alert-box warn' : 'muted';

  const tbody = $('#conn-table tbody');
  tbody.innerHTML = '';
  if (!(data.connections || []).length) {
    tbody.append(el('tr', {}, el('td', { colspan: '7', class: 'muted', text: 'Nenhuma conexão cadastrada. Crie uma conexão ou siga com o legado por variáveis de ambiente.' })));
  }
  for (const c of data.connections || []) {
    const cred = c.credential || {};
    const credLabel = cred.kind === 'vault' ? `cofre (${cred.vaultRef || '—'})`
      : cred.kind === 'env' ? `env ${cred.envVar || '—'}` : 'sem chave';
    const test = c.lastTest;
    tbody.append(el('tr', { 'data-conn-id': c.id }, [
      el('td', {}, [el('strong', { text: c.name || c.id }), el('div', { class: 'muted', text: c.id })]),
      el('td', { text: c.providerLabel || c.provider }),
      el('td', { text: (c.capabilities || []).join(', ') }),
      el('td', {}, [el('div', { text: c.model || '—' }), el('div', { class: 'muted', text: c.endpoint || '' })]),
      el('td', {}, [
        el('span', { class: 'badge ' + (cred.configured ? 'ok' : 'warn'), text: cred.configured ? 'configurada' : 'pendente' }),
        el('div', { class: 'muted', text: credLabel }),
      ]),
      el('td', {}, test
        ? [el('span', { class: 'badge ' + (test.status === 'ok' ? 'ok' : 'err'), text: test.code || test.status }),
           el('div', { class: 'muted', text: (test.at || '').replace('T', ' ').replace('Z', '') }),
           test.videoModel ? el('div', { class: 'muted', text: `vídeo ${test.videoModel.model}: ${test.videoModel.listed == null ? 'não verificado' : test.videoModel.listed ? 'listado' : 'não listado'}` }) : null]
        : el('span', { class: 'badge muted', text: 'nunca testada' })),
      el('td', {}, [
        el('button', { class: 'secondary', text: 'Testar', onclick: () => testConnection(c.id).catch((e) => toast(e.message)) }),
        el('button', { class: 'secondary', text: 'Editar', onclick: () => openConnectionDialog(c).catch((e) => toast(e.message)) }),
        cred.kind === 'vault' ? el('button', { class: 'secondary', text: 'Trocar chave', onclick: () => openCredentialDialog(c).catch((e) => toast(e.message)) }) : null,
        el('button', { class: 'warn-btn', text: 'Excluir', onclick: () => deleteConnection(c.id).catch((e) => toast(e.message)) }),
      ]),
    ]));
  }

  const projSel = $('#conn-project-select');
  const previous = projSel.value;
  projSel.innerHTML = '';
  for (const p of allProjects || []) {
    projSel.append(el('option', { value: p.path || p.id, text: `${p.name || p.id} (${p.sourceLabel || p.source || 'projeto'})` }));
  }
  if (previous && Array.from(projSel.options).some((o) => o.value === previous)) projSel.value = previous;
  await fillConnectionSelection();

  const hbody = $('#conn-history-table tbody');
  hbody.innerHTML = '';
  const calls = data.calls || [];
  if (!calls.length) {
    hbody.append(el('tr', {}, el('td', { colspan: '7', class: 'muted', text: 'Nenhuma chamada registrada ainda.' })));
  }
  for (const call of calls.slice(0, 60)) {
    const usage = call.usage || {};
    const info = call.providerInfo || {};
    const usageText = [
      usage.promptTokens != null ? `prompt ${usage.promptTokens}` : null,
      usage.completionTokens != null ? `resposta ${usage.completionTokens}` : null,
      usage.totalTokens != null ? `total ${usage.totalTokens}` : null,
      usage.imageCount != null ? `${usage.imageCount} imagem(ns)` : null,
      info.cost != null ? `custo ${info.cost}${info.currency ? ' ' + info.currency : ''}` : null,
      info.quota != null ? `cota ${info.quota}` : null,
      info.balance != null ? `saldo ${info.balance}` : null,
    ].filter(Boolean).join(' · ');
    hbody.append(el('tr', {}, [
      el('td', { text: (call.at || '').replace('T', ' ').replace('Z', '') }),
      el('td', { class: 'muted', text: call.project || '—' }),
      el('td', { text: call.connectionId || 'legado (env)' }),
      el('td', { text: call.capability }),
      el('td', { text: call.model || '—' }),
      el('td', {}, el('span', { class: 'badge ' + (call.status === 'completed' || call.status === 'ok' ? 'ok' : 'err'), text: call.code || call.status })),
      el('td', { class: 'muted', text: usageText || '—' }),
    ]));
  }
}

async function fillConnectionSelection() {
  const data = connectionsCache || await api('/api/connections');
  const project = $('#conn-project-select').value;
  const sel = (data.selections || {})[project] || {};
  const fill = (selectId, modelId, capability) => {
    const select = $(selectId);
    select.innerHTML = '';
    select.append(el('option', { value: '', text: capability === 'video' ? 'Sem seleção (necessária para clipes)' : 'Legado (variáveis de ambiente)' }));
    for (const c of data.connections || []) {
      if ((c.capabilities || []).includes(capability)) {
        select.append(el('option', { value: c.id, text: `${c.name} (${c.id})` }));
      }
    }
    const chosen = sel[capability] || {};
    select.value = chosen.connectionId || '';
    $(modelId).value = chosen.model || '';
  };
  fill('#conn-text-select', '#conn-text-model', 'text');
  fill('#conn-image-select', '#conn-image-model', 'image');
  fill('#conn-video-select', '#conn-video-model', 'video');
  const fb = $('#conn-selection-feedback');
  fb.textContent = project
    ? `Seleção atual do projeto: texto ${sel.text ? sel.text.connectionId : 'legado'} · imagem ${sel.image ? sel.image.connectionId : 'legado'} · vídeo ${sel.video ? sel.video.connectionId : 'sem seleção'}.`
    : 'Selecione um projeto para ver e editar a seleção.';
}

async function saveConnectionSelection() {
  const project = $('#conn-project-select').value;
  if (!project) throw new Error('selecione um projeto');
  for (const [capability, selectId, modelId] of [['text', '#conn-text-select', '#conn-text-model'], ['image', '#conn-image-select', '#conn-image-model'], ['video', '#conn-video-select', '#conn-video-model']]) {
    await post('/api/connections/select', {
      project, capability,
      connectionId: $(selectId).value || null,
      model: $(modelId).value.trim() || null,
    });
  }
  toast('Seleção do projeto salva.');
  await loadConnections();
}

async function testConnection(connectionId) {
  const res = await post('/api/connections/test', { connectionId });
  const t = res.test || {};
  toast(`Teste de ${connectionId}: ${t.code || t.status} — ${t.message || ''}`);
  await loadConnections();
}

async function deleteConnection(connectionId) {
  await post('/api/connections/delete', { connectionId });
  toast(`Conexão ${connectionId} excluída; seleções que a usavam voltaram ao legado.`);
  await loadConnections();
}

function openCredentialDialog(conn) {
  const root = $('#conn-dialog-root');
  root.innerHTML = '';
  const overlay = el('div', { class: 'media-dialog-overlay' });
  const dialog = el('div', { class: 'media-dialog', id: 'conn-credential-dialog' });
  const input = el('input', { type: 'password', id: 'conn-credential-value', placeholder: 'Novo valor da chave' });
  const fb = el('div', {});
  dialog.append(
    el('div', { class: 'row', style: 'justify-content: space-between;' }, [
      el('h3', { text: `Trocar chave — ${conn.name}`, style: 'margin:0;' }),
      el('button', { class: 'secondary', text: 'Fechar', onclick: closeConnectionDialog }),
    ]),
    el('p', { class: 'muted', text: `A referência ${conn.credential.vaultRef} e as escolhas dos projetos são mantidas; apenas o valor no cofre é substituído.` }),
    el('label', {}, ['Nova chave', input]),
    fb,
    el('button', {
      text: 'Gravar no cofre',
      onclick: async () => {
        fb.innerHTML = '';
        try {
          await post('/api/connections/credential', { connectionId: conn.id, value: input.value });
          toast('Chave substituída no cofre.');
          closeConnectionDialog();
          await loadConnections();
        } catch (e) {
          fb.append(el('div', { class: 'alert-box err', text: e.message }));
        }
      },
    }),
  );
  overlay.append(dialog);
  root.append(overlay);
  return Promise.resolve();
}

async function openConnectionDialog(existing) {
  const root = $('#conn-dialog-root');
  root.innerHTML = '';
  const overlay = el('div', { class: 'media-dialog-overlay' });
  const dialog = el('div', { class: 'media-dialog', id: 'conn-edit-dialog' });
  const nameInput = el('input', { type: 'text', id: 'conn-f-name', value: existing ? existing.name : '' });
  const providerSelect = el('select', { id: 'conn-f-provider' }, [
    el('option', { value: 'local-llm', text: 'Modelo local de texto (OpenAI-compatível)' }),
    el('option', { value: 'google-gemini', text: 'Google Gemini (imagem e vídeo)' }),
  ]);
  if (existing) {
    providerSelect.value = existing.provider;
    providerSelect.disabled = true;
  }
  const endpointInput = el('input', { type: 'text', id: 'conn-f-endpoint', value: existing ? existing.endpoint : '' });
  const modelInput = el('input', { type: 'text', id: 'conn-f-model', value: existing ? existing.model : '' });
  const timeoutInput = el('input', { type: 'number', id: 'conn-f-timeout', value: existing ? existing.timeoutSec : '', placeholder: 'padrão do provedor' });
  const kindSelect = el('select', { id: 'conn-f-kind' }, [
    el('option', { value: 'none', text: 'Sem chave (servidor local aberto)' }),
    el('option', { value: 'vault', text: 'Cofre da estação (gravar chave)' }),
    el('option', { value: 'env', text: 'Variável de ambiente' }),
  ]);
  kindSelect.value = existing ? (existing.credential || {}).kind || 'none' : 'none';
  const envInput = el('input', { type: 'text', id: 'conn-f-env', value: existing ? (existing.credential || {}).envVar || '' : '', placeholder: 'ex.: GEMINI_API_KEY' });
  const secretInput = el('input', { type: 'password', id: 'conn-f-secret', placeholder: existing ? 'deixe vazio para manter a chave atual' : 'valor da chave (gravado no cofre)' });
  const fb = el('div', {});
  const syncVisibility = () => {
    envInput.parentElement.hidden = kindSelect.value !== 'env';
    secretInput.parentElement.hidden = kindSelect.value !== 'vault';
  };
  kindSelect.addEventListener('change', syncVisibility);
  dialog.append(
    el('div', { class: 'row', style: 'justify-content: space-between;' }, [
      el('h3', { text: existing ? `Editar conexão — ${existing.id}` : 'Nova conexão', style: 'margin:0;' }),
      el('button', { class: 'secondary', text: 'Fechar', onclick: closeConnectionDialog }),
    ]),
    el('label', {}, ['Nome', nameInput]),
    el('label', {}, ['Provedor / capacidade', providerSelect]),
    el('label', {}, ['Endpoint', endpointInput]),
    el('label', {}, ['Modelo', modelInput]),
    el('label', {}, ['Timeout (s)', timeoutInput]),
    el('label', {}, ['Credencial', kindSelect]),
    el('label', {}, ['Variável de ambiente', envInput]),
    el('label', {}, ['Chave (cofre)', secretInput]),
    fb,
    el('button', {
      id: 'btn-conn-save',
      text: existing ? 'Salvar conexão' : 'Cadastrar conexão',
      onclick: async () => {
        fb.innerHTML = '';
        try {
          const body = {
            id: existing ? existing.id : undefined,
            name: nameInput.value.trim(),
            provider: providerSelect.value,
            endpoint: endpointInput.value.trim() || undefined,
            model: modelInput.value.trim() || undefined,
            timeoutSec: timeoutInput.value ? Number(timeoutInput.value) : undefined,
            credential: { kind: kindSelect.value, envVar: envInput.value.trim() || undefined },
          };
          if (kindSelect.value === 'vault' && secretInput.value) body.credentialValue = secretInput.value;
          await post('/api/connections/save', body);
          toast(existing ? 'Conexão atualizada.' : 'Conexão cadastrada.');
          closeConnectionDialog();
          await loadConnections();
        } catch (e) {
          fb.append(el('div', { class: 'alert-box err', text: e.message }));
        }
      },
    }),
  );
  overlay.append(dialog);
  root.append(overlay);
  syncVisibility();
}

window.StudioBridge = {
  applyOpenedWork: (data) => applyOpenedWork(data),
  setMode: (mode) => setMode(mode),
  toast: (msg) => toast(msg),
  checkReadiness: () => loadReadiness(),
  loadProjects: () => loadProjects(),
  openQueueWorkReview: (workId) => openQueueWorkReview(workId),
  applyReviewPackageResult: (workId, data) => {
    if (currentWork && currentWork.id === workId && data) {
      renderReviewPanel(data, data.packageDelivery || null);
    }
    loadWorks().catch(() => {});
  },
  refreshReviewOverview: (workId) => {
    if (currentWork && currentWork.id === workId) {
      return loadReviewOverview();
    }
    return Promise.resolve(null);
  },
  updateQueueNavBadge: (pendingCount) => {
    const navBadge = $('#queue-nav-badge');
    if (navBadge) {
      navBadge.textContent = String(pendingCount);
      navBadge.hidden = pendingCount === 0;
    }
  },
  openBatchExportModal: (ids) => {
    selectedBatchWorks.clear();
    for (const id of ids || []) selectedBatchWorks.add(id);
    updateBatchSelectionCount();
    return openBatchExportModal();
  },
};

init();
