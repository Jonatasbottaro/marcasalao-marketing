/* Aba Planejamento e integracao de sugestoes no Motion (Studio local) */

(function () {
  let planningOverview = null;
  let stagedSuggestionState = null;
  let planningFillMode = 'manual';
  let planningLoadSeq = 0;

  const MODES_ALL = ['home', 'planning', 'video', 'carousel', 'motion', 'review'];

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === undefined || v === null || v === false) continue;
        if (k === 'text') node.textContent = String(v);
        else if (k === 'html') node.innerHTML = String(v);
        else if (k === 'class') node.className = String(v);
        else if (k === 'checked') {
          node.checked = true;
          node.setAttribute('checked', '');
        } else if (k === 'disabled') {
          node.disabled = Boolean(v);
          if (v) node.setAttribute('disabled', '');
        } else if (k === 'value') {
          node.setAttribute('value', String(v));
          if (tag !== 'textarea') node.value = String(v);
        } else if (k.startsWith('on') && typeof v === 'function') {
          node.addEventListener(k.slice(2), v);
        } else if (v === true) {
          node.setAttribute(k, '');
        } else {
          node.setAttribute(k, String(v));
        }
      }
    }
    const appendItem = (item) => {
      if (item === undefined || item === null || item === false || item === '') return;
      if (Array.isArray(item)) {
        for (const sub of item) appendItem(sub);
        return;
      }
      node.append(item);
    };
    for (const child of children) appendItem(child);
    return node;
  }

  function pHideError() {
    const box = $('#p-error-box');
    if (box) {
      box.hidden = true;
      box.innerHTML = '';
    }
  }

  function pShowError(err, payload) {
    const box = $('#p-error-box');
    if (!box) return;
    box.hidden = false;
    box.innerHTML = '';
    const msg = (payload && payload.error) || (err && err.message) || String(err || 'Erro desconhecido');
    box.append(el('strong', { text: payload && payload.conflict ? 'Conflito de versão (HTTP 409): ' : 'Atenção: ' }));
    box.append(document.createTextNode(msg));
    const extras = [];
    if (payload && payload.failureCode) extras.push(`Código: ${payload.failureCode}`);
    if (payload && payload.subject) extras.push(`Alvo: ${payload.subject}`);
    if (payload && payload.stage) extras.push(`Etapa: ${payload.stage}`);
    if (payload && payload.code) extras.push(`Detalhe: ${payload.code}`);
    if (extras.length) {
      box.append(el('div', { class: 'muted', text: extras.join(' · ') }));
    }
    if (payload && payload.conflict) {
      box.append(el('div', { style: 'margin-top:6px;' },
        el('button', {
          type: 'button',
          class: 'secondary',
          text: 'Recarregar estado atual do trabalho',
          onclick: () => loadPlanningOverview().catch((e) => toast(e.message)),
        }),
      ));
    }
  }

  async function pRequest(method, url, body) {
    pHideError();
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { ok: false, error: text || `HTTP ${res.status}` };
    }
    if (!res.ok || data.ok === false) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.status = res.status;
      err.payload = data;
      pShowError(err, data);
      throw err;
    }
    return data;
  }

  function updateWorkBarPlanningBadge(overview) {
    const bar = $('#active-work-bar');
    if (!bar) return;
    let badge = $('#active-work-planning-stage');
    if (!overview || !overview.work) {
      if (badge) badge.remove();
      return;
    }
    if (!badge) {
      badge = el('span', { id: 'active-work-planning-stage', class: 'badge muted' });
      const meta = $('#active-work-meta');
      if (meta && meta.parentNode) {
        meta.parentNode.append(document.createTextNode(' '), badge);
      }
    }
    badge.textContent = `Planejamento: ${overview.currentStageLabel || overview.planning?.currentStage || '1. Ideia e briefing'}`;
  }

  function mediaSelectOptions(workMedia, selectedId, emptyLabel) {
    const opts = [el('option', { value: '', text: emptyLabel || 'Mídia local pendente (selecionar arquivo)' })];
    for (const m of (workMedia || [])) {
      opts.push(el('option', {
        value: m.id,
        text: `${m.id} (${m.type}) — ${m.name || m.path}`,
      }));
    }
    return opts;
  }

  function updateFillModeUI(mode) {
    planningFillMode = mode || 'manual';
    const importPanel = $('#p-panel-import');
    const llmPanel = $('#p-panel-local-llm');
    const help = $('#p-fill-mode-help');
    if (importPanel) importPanel.hidden = planningFillMode !== 'import';
    if (llmPanel) llmPanel.hidden = planningFillMode !== 'local-llm';
    if (help) {
      if (planningFillMode === 'manual') {
        help.textContent = 'Modo Manual: edite as etapas 1 e 2 diretamente abaixo e salve no trabalho.';
      } else if (planningFillMode === 'import') {
        help.textContent = 'Modo Copiar e importar: gere o prompt estrito da etapa, cole o JSON PlanningSuggestion v1 retornado e confira a diferença antes de incorporar.';
      } else {
        help.textContent = 'Modo Modelo local opcional: chama POST /v1/chat/completions (padrão desativado) com contexto estrito da etapa e valida via contrato do núcleo.';
      }
    }
  }

  function applyPlanningOverview(overview) {
    planningOverview = overview || null;
    updateWorkBarPlanningBadge(planningOverview);
    renderPlanningPanel();
    renderMotionPlanningSuggestions();
  }

  async function loadPlanningOverview() {
    const seq = ++planningLoadSeq;
    if (!currentWork) {
      planningOverview = null;
      stagedSuggestionState = null;
      renderPlanningPanel();
      renderMotionPlanningSuggestions();
      return null;
    }
    const data = await api('/api/works/planning?id=' + encodeURIComponent(currentWork.id));
    if (seq === planningLoadSeq) {
      applyPlanningOverview(data);
    }
    return data;
  }

  function setPlanningStageButtons(stage) {
    document.querySelectorAll('.p-stage-btn').forEach((btn) => {
      const id = btn.id.replace('p-stage-btn-', '');
      btn.classList.toggle('active', id === stage);
    });
  }

  function renderWorkBanner() {
    const banner = $('#p-work-banner');
    const stageBadge = $('#p-stage-badge');
    const recheckBanner = $('#p-recheck-banner');
    if (!planningOverview || !planningOverview.work) {
      banner.className = 'alert-box';
      banner.innerHTML = 'Abra ou crie um trabalho em <strong>Trabalhos &amp; Projetos</strong> para planejar.';
      stageBadge.className = 'badge muted';
      stageBadge.textContent = 'Sem trabalho';
      recheckBanner.hidden = true;
      recheckBanner.innerHTML = '';
      setPlanningStageButtons('');
      return;
    }
    const w = planningOverview.work;
    const pl = planningOverview.planning;
    const analysis = planningOverview.analysis || {};
    stageBadge.className = 'badge ok';
    stageBadge.textContent = planningOverview.currentStageLabel || pl.currentStage;
    setPlanningStageButtons(pl.currentStage);

    banner.className = 'alert-box';
    banner.innerHTML = '';
    banner.append(
      el('strong', { text: `${w.name} (${w.id})` }),
      el('span', { class: 'muted', text: ` · Projeto: ${w.project} · Cenas: ${pl.creative.videoScenes.length} · Cards: ${pl.creative.carouselCards.length} · Pendências de mídia: ${(analysis.missingMediaSceneIds || []).length}` }),
    );

    const warnMsgs = [];
    if (analysis.creativeNeedsRecheck && analysis.recheckReason) warnMsgs.push(analysis.recheckReason);
    if (analysis.editorialBriefingDiverged) {
      warnMsgs.push('A ficha editorial em "Revisão & Entrega" foi alterada fora desta aba.');
    }
    for (const wMsg of (analysis.warnings || [])) warnMsgs.push(wMsg);
    if (warnMsgs.length) {
      recheckBanner.hidden = false;
      recheckBanner.innerHTML = '';
      recheckBanner.append(el('strong', { text: 'Avisos do planejamento:' }));
      const ul = el('ul', { style: 'margin: 6px 0 0 18px;' });
      for (const m of warnMsgs) ul.append(el('li', { text: m }));
      recheckBanner.append(ul);
      if (analysis.editorialBriefingDiverged) {
        recheckBanner.append(el('div', { style: 'margin-top:6px;' },
          el('button', {
            type: 'button',
            class: 'secondary',
            text: 'Importar briefing da Ficha Editorial',
            onclick: () => syncFromEditorialBriefing().catch(() => {}),
          }),
        ));
      }
    } else {
      recheckBanner.hidden = true;
      recheckBanner.innerHTML = '';
    }
  }

  function renderAnalysisBoxes() {
    const filledBox = $('#p-dims-filled');
    const gapsBox = $('#p-dims-gaps');
    const warnBox = $('#p-briefing-warnings');
    filledBox.innerHTML = '';
    gapsBox.innerHTML = '';
    warnBox.innerHTML = '';
    if (!planningOverview) return;
    const a = planningOverview.analysis || {};
    const filled = a.filledFields || [];
    if (!filled.length) {
      filledBox.append(el('p', { class: 'muted', text: 'Nenhuma dimensão preenchida ainda.' }));
    } else {
      const ul = el('ul', { style: 'margin: 0 0 0 18px;' });
      for (const item of filled) {
        ul.append(el('li', {}, el('strong', { text: item.label + ': ' }), document.createTextNode(item.value)));
      }
      filledBox.append(ul);
    }

    const gaps = a.detectedGaps || [];
    if (!gaps.length) {
      gapsBox.append(el('p', { class: 'muted', text: 'Nenhuma lacuna aberta nas 8 dimensões.' }));
    } else {
      const ul = el('ul', { style: 'margin: 0 0 0 18px;' });
      for (const g of gaps) ul.append(el('li', { text: g }));
      gapsBox.append(ul);
    }

    if ((a.warnings || []).length) {
      const box = el('div', { class: 'alert-box warn' });
      box.append(el('strong', { text: 'Alertas de política/evidência:' }));
      const ul = el('ul', { style: 'margin: 4px 0 0 18px;' });
      for (const w of a.warnings) ul.append(el('li', { text: w }));
      box.append(ul);
      warnBox.append(box);
    }
  }

  function renderAllowedProfilesCheckboxes() {
    const box = $('#p-b-profiles-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const rec = new Set(planningOverview.planning?.briefingExtended?.recommendedProfiles || []);
    for (const p of (planningOverview.allowedProfiles || [])) {
      const caps = [];
      if (p.localExportVideo) caps.push('vídeo');
      if (p.localExportCarousel) caps.push('carrossel');
      if (p.localExportMotion) caps.push('motion');
      const chk = el('input', {
        type: 'checkbox',
        class: 'p-profile-check',
        value: p.id,
        ...(rec.has(p.id) ? { checked: '' } : {}),
      });
      box.append(el('label', { class: 'inline-check' }, chk, el('span', { text: `${p.id} (${p.aspectRatio || ''} · ${caps.join('/') || 'texto'})` })));
    }
  }

  function renderQuestionsList() {
    const box = $('#p-questions-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const questions = planningOverview.planning.questions || [];
    questions.forEach((q, idx) => {
      const answered = Boolean((q.answer || '').trim());
      const row = el('div', { class: 'planning-item', 'data-q-index': String(idx), 'data-q-id': q.id || '' });
      const dimSel = el('select', { class: 'p-q-dim' },
        ...(['product', 'audience', 'objective', 'coreMessage', 'supportEvidence', 'cta', 'tone', 'channels']
          .map((d) => el('option', { value: d, text: d }))),
      );
      dimSel.value = q.dimension || 'objective';
      const head = el('div', { class: 'planning-item-head' },
        el('div', { class: 'row' },
          el('strong', { text: `#${idx + 1}` }),
          dimSel,
          el('span', { class: 'badge ' + (answered ? 'ok' : 'warn'), text: answered ? 'Respondida' : 'Pendente' }),
        ),
        el('button', {
          type: 'button',
          class: 'secondary',
          text: 'Remover',
          onclick: () => {
            syncPlanningFromDOM();
            planningOverview.planning.questions.splice(idx, 1);
            renderQuestionsList();
          },
        }),
      );
      const qInput = el('input', { type: 'text', class: 'p-q-text', value: q.question || '', placeholder: 'Pergunta de esclarecimento' });
      const aInput = el('textarea', { class: 'p-q-answer', rows: '2', placeholder: 'Resposta do operador (opcional: deixe em branco enquanto pendente)' });
      aInput.value = q.answer || '';
      row.append(head,
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'Pergunta ', qInput),
          el('label', {}, 'Resposta ', aInput),
        ),
        q.suggestedAnswer ? el('div', { class: 'muted', style: 'margin-top:4px;', text: `Sugestão de referência: ${q.suggestedAnswer}` }) : '',
      );
      box.append(row);
    });
  }

  function renderClaimsList() {
    const box = $('#p-claims-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const claims = planningOverview.planning.claims || [];
    const media = planningOverview.workMedia || [];
    if (!claims.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma afirmação sensível cadastrada.' }));
      return;
    }
    claims.forEach((c, idx) => {
      const row = el('div', { class: 'planning-item', 'data-c-index': String(idx), 'data-c-id': c.id || '' });
      const stSel = el('select', { class: 'p-claim-status' },
        el('option', { value: 'pending_validation', text: 'Pendente de validação' }),
        el('option', { value: 'hypothesis', text: 'Hipótese / depende de confirmação' }),
        el('option', { value: 'confirmed', text: 'Confirmada' }),
      );
      stSel.value = c.status || 'pending_validation';
      const medSel = el('select', { class: 'p-claim-evidence-media' },
        ...mediaSelectOptions(media, c.evidenceMediaId, 'Sem mídia vinculada'),
      );
      medSel.value = c.evidenceMediaId || '';
      const reqConf = el('input', {
        type: 'checkbox',
        class: 'p-claim-requires-conf',
        ...(c.requiresConfirmation ? { checked: '' } : {}),
      });
      const stmtInput = el('input', { type: 'text', class: 'p-claim-statement', value: c.statement || '', placeholder: 'Afirmação ou promessa a verificar' });
      const warnInput = el('input', { type: 'text', class: 'p-claim-warning', value: c.warning || '', placeholder: 'Observação ou alerta de política' });
      row.append(
        el('div', { class: 'planning-item-head' },
          el('div', { class: 'row' },
            el('strong', { text: c.id || `claim-${idx + 1}` }),
            el('span', { class: 'badge ' + (c.status === 'confirmed' ? 'ok' : 'warn'), text: c.status }),
          ),
          el('button', {
            type: 'button',
            class: 'secondary',
            text: 'Remover',
            onclick: () => {
              syncPlanningFromDOM();
              planningOverview.planning.claims.splice(idx, 1);
              renderClaimsList();
            },
          }),
        ),
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'Afirmação ', stmtInput),
          el('label', {}, 'Status ', stSel),
          el('label', {}, 'Evidência (mídia do trabalho) ', medSel),
          el('label', {}, 'Alerta ', warnInput),
        ),
        el('label', { class: 'inline-check', style: 'margin-top:6px;' }, reqConf, el('span', { text: 'Exige confirmação editorial antes da aprovação' })),
      );
      box.append(row);
    });
  }

  function renderHooksList() {
    const box = $('#p-hooks-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const hooks = planningOverview.planning.creative.hookOptions || [];
    const selectedId = planningOverview.planning.creative.selectedHookId || '';
    if (!hooks.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma opção de hook ainda. Adicione opções para comparar ou preencha o gancho diretamente abaixo.' }));
      return;
    }
    hooks.forEach((h, idx) => {
      const row = el('div', { class: 'planning-item', 'data-h-index': String(idx), 'data-h-id': h.id || '' });
      const radio = el('input', {
        type: 'radio',
        name: 'p-selected-hook',
        class: 'p-hook-radio',
        value: h.id || `hook-${idx + 1}`,
        ...(h.id === selectedId ? { checked: '' } : {}),
        onchange: () => {
          planningOverview.planning.creative.selectedHookId = radio.value;
          const currentText = row.querySelector('.p-hook-text')?.value || h.text || '';
          planningOverview.planning.briefing.hook = currentText;
          if ($('#p-b-hook')) $('#p-b-hook').value = currentText;
        },
      });
      const textInput = el('input', {
        type: 'text',
        class: 'p-hook-text',
        value: h.text || '',
        placeholder: 'Texto do hook',
        oninput: () => {
          if (radio.checked && $('#p-b-hook')) $('#p-b-hook').value = textInput.value;
        },
      });
      const angleInput = el('input', { type: 'text', class: 'p-hook-angle', value: h.angle || '', placeholder: 'Ângulo (ex.: dor prática, demonstração)' });
      row.append(
        el('div', { class: 'planning-item-head' },
          el('label', { class: 'inline-check' }, radio, el('strong', { text: `Usar este hook (${h.id})` })),
          el('button', {
            type: 'button',
            class: 'secondary',
            text: 'Remover',
            onclick: () => {
              syncPlanningFromDOM();
              planningOverview.planning.creative.hookOptions.splice(idx, 1);
              renderHooksList();
            },
          }),
        ),
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'Texto do hook ', textInput),
          el('label', {}, 'Ângulo ', angleInput),
        ),
      );
      box.append(row);
    });
  }

  function renderScenesList() {
    const box = $('#p-scenes-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const scenes = planningOverview.planning.creative.videoScenes || [];
    const media = planningOverview.workMedia || [];
    const mediaIds = new Set(media.map((m) => m.id));
    if (!scenes.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma cena planejada ainda.' }));
      return;
    }
    const narrativeOpts = ['hook', 'context', 'problem', 'demonstration', 'explanation', 'proof', 'transition', 'cta', 'closing'];
    scenes.forEach((s, idx) => {
      const hasMedia = Boolean(s.mediaId && mediaIds.has(s.mediaId));
      const row = el('div', {
        class: 'planning-item' + (hasMedia ? '' : ' pending-media'),
        'data-s-index': String(idx),
      });
      const idInput = el('input', { type: 'text', class: 'p-scene-id', value: s.id || `cena-${idx + 1}`, placeholder: 'kebab-case' });
      const nfSel = el('select', { class: 'p-scene-nf' }, ...narrativeOpts.map((n) => el('option', { value: n, text: n })));
      nfSel.value = s.narrativeFunction || 'demonstration';
      const motionSel = el('select', { class: 'p-scene-motion' },
        el('option', { value: 'none', text: 'none (permite contorno Motion)' }),
        el('option', { value: 'slow-zoom', text: 'slow-zoom' }),
      );
      motionSel.value = s.motionIntent || 'none';
      const durInput = el('input', { type: 'number', class: 'p-scene-duration', value: String(s.durationMs || 4000), min: '1000', max: '60000', step: '500' });
      const mediaSel = el('select', { class: 'p-scene-media' },
        ...mediaSelectOptions(media, s.mediaId, 'Mídia pendente — selecione depois de importar arquivos'),
      );
      mediaSel.value = hasMedia ? s.mediaId : '';
      const titleInput = el('input', { type: 'text', class: 'p-scene-title', value: s.titleOverlay || '', placeholder: 'Título na tela (VisualStyle / TextOverlay)' });
      const captionInput = el('input', { type: 'text', class: 'p-scene-caption', value: s.caption || '', placeholder: 'Legenda curta (.srt)' });
      const narrationInput = el('textarea', { class: 'p-scene-narration', rows: '2', placeholder: 'Texto de narração externa (.txt, não vai ao MP4)' });
      narrationInput.value = s.narration || '';
      const descInput = el('input', { type: 'text', class: 'p-scene-desc', value: s.requiredMediaDescriptor || '', placeholder: 'Descritor da mídia necessária (ex.: captura real da agenda confirmada)' });
      const objInput = el('input', { type: 'text', class: 'p-scene-objective', value: s.objective || '', placeholder: 'Objetivo da cena' });

      const controls = el('div', { class: 'row' },
        el('button', {
          type: 'button', class: 'secondary', text: '↑', disabled: idx === 0,
          onclick: () => {
            syncPlanningFromDOM();
            const arr = planningOverview.planning.creative.videoScenes;
            if (idx > 0) { [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]; renderScenesList(); }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: '↓', disabled: idx === scenes.length - 1,
          onclick: () => {
            syncPlanningFromDOM();
            const arr = planningOverview.planning.creative.videoScenes;
            if (idx < arr.length - 1) { [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]; renderScenesList(); }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: 'Preparar imagem',
          title: 'Abrir pedido visual desta cena (importar, gerar, comparar e aplicar)',
          onclick: () => {
            if (window.StudioMedia) {
              window.StudioMedia.openRequest('video_scene', idInput.value.trim()).catch((e) => toast(e.message));
            }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: 'Remover',
          onclick: () => {
            syncPlanningFromDOM();
            planningOverview.planning.creative.videoScenes.splice(idx, 1);
            renderScenesList();
          },
        }),
      );
      row.append(
        el('div', { class: 'planning-item-head' },
          el('div', { class: 'row' },
            el('strong', { text: `Cena #${idx + 1}` }),
            el('span', { class: 'badge ' + (hasMedia ? 'ok' : 'warn'), text: hasMedia ? `Mídia: ${s.mediaId}` : 'Pendente de mídia local' }),
          ),
          controls,
        ),
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'ID da cena (Motion) ', idInput),
          el('label', {}, 'Função narrativa ', nfSel),
          el('label', {}, 'Duração (ms) ', durInput),
          el('label', {}, 'Movimento ', motionSel),
          el('label', {}, 'Mídia local do trabalho ', mediaSel),
          el('label', {}, 'Descritor da mídia necessária ', descInput),
          el('label', {}, 'Título sobreposto ', titleInput),
          el('label', {}, 'Legenda curta (.srt) ', captionInput),
          el('label', {}, 'Objetivo da cena ', objInput),
          el('label', { style: 'grid-column: 1 / -1;' }, 'Narração externa (.txt) ', narrationInput),
        ),
      );
      box.append(row);
    });
  }

  function renderCardsList() {
    const box = $('#p-cards-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const cards = planningOverview.planning.creative.carouselCards || [];
    const media = planningOverview.workMedia || [];
    const mediaIds = new Set(media.map((m) => m.id));
    if (!cards.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhum card planejado ainda.' }));
      return;
    }
    cards.forEach((c, idx) => {
      const hasMedia = Boolean(c.mediaId && mediaIds.has(c.mediaId));
      const row = el('div', { class: 'planning-item', 'data-card-index': String(idx) });
      const idInput = el('input', { type: 'text', class: 'p-card-id', value: c.id || `card-${idx + 1}` });
      const roleSel = el('select', { class: 'p-card-role' },
        el('option', { value: 'cover', text: 'cover (capa)' }),
        el('option', { value: 'content', text: 'content (conteúdo)' }),
        el('option', { value: 'cta', text: 'cta (chamada final)' }),
      );
      roleSel.value = c.role || 'content';
      const titleInput = el('input', { type: 'text', class: 'p-card-title', value: c.title || '', placeholder: 'Título do card' });
      const bodyInput = el('textarea', { class: 'p-card-body', rows: '2', placeholder: 'Texto de apoio do card' });
      bodyInput.value = c.body || '';
      const descInput = el('input', { type: 'text', class: 'p-card-desc', value: c.requiredMediaDescriptor || '', placeholder: 'Descritor visual necessário (ou fundo tipográfico)' });
      const mediaSel = el('select', { class: 'p-card-media' },
        ...mediaSelectOptions(media, c.mediaId, 'Automático / fundo do projeto (sem imagem específica)'),
      );
      mediaSel.value = hasMedia ? c.mediaId : '';

      const controls = el('div', { class: 'row' },
        el('button', {
          type: 'button', class: 'secondary', text: '↑', disabled: idx === 0,
          onclick: () => {
            syncPlanningFromDOM();
            const arr = planningOverview.planning.creative.carouselCards;
            if (idx > 0) { [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]; renderCardsList(); }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: '↓', disabled: idx === cards.length - 1,
          onclick: () => {
            syncPlanningFromDOM();
            const arr = planningOverview.planning.creative.carouselCards;
            if (idx < arr.length - 1) { [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]; renderCardsList(); }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: 'Preparar imagem',
          title: 'Abrir pedido visual deste card (importar, gerar, comparar e aplicar)',
          onclick: () => {
            if (window.StudioMedia) {
              window.StudioMedia.openRequest('carousel_card', idInput.value.trim()).catch((e) => toast(e.message));
            }
          },
        }),
        el('button', {
          type: 'button', class: 'secondary', text: 'Remover',
          onclick: () => {
            syncPlanningFromDOM();
            planningOverview.planning.creative.carouselCards.splice(idx, 1);
            renderCardsList();
          },
        }),
      );
      row.append(
        el('div', { class: 'planning-item-head' },
          el('div', { class: 'row' },
            el('strong', { text: `Card #${idx + 1}` }),
            el('span', { class: 'badge muted', text: c.role || 'content' }),
          ),
          controls,
        ),
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'ID do card ', idInput),
          el('label', {}, 'Papel ', roleSel),
          el('label', {}, 'Imagem local ', mediaSel),
          el('label', {}, 'Descritor visual ', descInput),
          el('label', { style: 'grid-column: 1 / -1;' }, 'Título ', titleInput),
          el('label', { style: 'grid-column: 1 / -1;' }, 'Texto do card ', bodyInput),
        ),
      );
      box.append(row);
    });
  }

  function renderPlanningChannelsList() {
    const box = $('#p-channels-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const chMap = planningOverview.planning.creative.channelCopies || {};
    for (const prof of (planningOverview.allowedProfiles || [])) {
      const pid = prof.id;
      const entry = chMap[pid] || { profileId: pid, title: '', postText: '', cta: '', destinationUrl: '', hashtags: '', flags: [] };
      const card = el('div', { class: 'review-card', 'data-p-channel-id': pid });
      const postArea = el('textarea', { rows: '3', 'data-pch-field': 'postText', placeholder: `Texto de publicação para ${pid}` });
      postArea.value = entry.postText || '';
      card.append(
        el('div', { class: 'review-card-head' },
          el('strong', { text: pid }),
          el('span', { class: 'badge muted', text: prof.aspectRatio || 'perfil' }),
        ),
        (entry.flags || []).length ? el('div', { class: 'alert-box warn', style: 'margin-bottom:6px;', text: entry.flags.join(' | ') }) : '',
        el('label', {}, 'Título do post ', el('input', { type: 'text', value: entry.title || '', 'data-pch-field': 'title' })),
        el('label', {}, 'Texto da publicação ', postArea),
        el('label', {}, 'CTA do canal ', el('input', { type: 'text', value: entry.cta || '', 'data-pch-field': 'cta' })),
        el('label', {}, 'URL de destino ', el('input', { type: 'text', value: entry.destinationUrl || '', 'data-pch-field': 'destinationUrl' })),
        el('label', {}, 'Hashtags ', el('input', { type: 'text', value: entry.hashtags || '', 'data-pch-field': 'hashtags' })),
      );
      box.append(card);
    }
  }

  function renderMotionSuggestionsEditor() {
    const box = $('#p-motion-suggestions-list');
    box.innerHTML = '';
    if (!planningOverview) return;
    const list = planningOverview.planning.creative.motionSuggestions || [];
    if (!list.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma sugestão de destaque Motion cadastrada.' }));
      return;
    }
    list.forEach((ms, idx) => {
      const row = el('div', { class: 'planning-item', 'data-ms-index': String(idx) });
      row.append(
        el('div', { class: 'planning-item-head' },
          el('strong', { text: `Sugestão Motion #${idx + 1}` }),
          el('button', {
            type: 'button', class: 'secondary', text: 'Remover',
            onclick: () => {
              syncPlanningFromDOM();
              planningOverview.planning.creative.motionSuggestions.splice(idx, 1);
              renderMotionSuggestionsEditor();
            },
          }),
        ),
        el('div', { class: 'planning-item-grid' },
          el('label', {}, 'ID da cena ', el('input', { type: 'text', class: 'p-ms-scene', value: ms.sceneId || '' })),
          el('label', {}, 'Elemento a destacar ', el('input', { type: 'text', class: 'p-ms-target', value: ms.targetElement || '' })),
          el('label', {}, 'Cor sugerida ', el('input', { type: 'text', class: 'p-ms-color', value: ms.suggestedColor || '#FFD700' })),
          el('label', {}, 'Início (ms) ', el('input', { type: 'number', class: 'p-ms-start', value: String(ms.suggestedStartMs ?? 400), min: '0', step: '100' })),
          el('label', {}, 'Fim (ms) ', el('input', { type: 'number', class: 'p-ms-end', value: String(ms.suggestedEndMs ?? 2800), min: '200', step: '100' })),
          el('label', {}, 'Observação ', el('input', { type: 'text', class: 'p-ms-note', value: ms.note || '' })),
        ),
      );
      box.append(row);
    });
  }

  function renderStage3Controls() {
    const chBox = $('#p-apply-channels-list');
    const preserveBox = $('#p-preserve-items-box');
    const diffOut = $('#p-diff-output');
    chBox.innerHTML = '';
    preserveBox.innerHTML = '';
    if (!planningOverview) {
      diffOut.innerHTML = '';
      return;
    }

    const oldChannels = new Set();
    for (const c of (planningOverview.editorsDiff?.channels || [])) {
      oldChannels.add(c.profileId);
    }
    for (const prof of (planningOverview.allowedProfiles || [])) {
      const pid = prof.id;
      chBox.append(el('label', { class: 'inline-check' },
        el('input', { type: 'checkbox', class: 'p-apply-ch-check', value: pid, checked: '' }),
        el('span', { text: pid }),
      ));
    }

    // Itens ja existentes nos editores que podem ser preservados
    const existingScenes = (currentWork && draft?.scenes) || [];
    const existingCards = (currentWork && cdraft?.cards) || [];
    if (existingScenes.length) {
      const sRow = el('div', { class: 'row', style: 'margin-bottom:6px;' }, el('strong', { text: 'Preservar cenas nos editores: ' }));
      for (const s of existingScenes) {
        sRow.append(el('label', { class: 'inline-check' },
          el('input', { type: 'checkbox', class: 'p-preserve-scene', value: s.id }),
          el('span', { text: s.id }),
        ));
      }
      preserveBox.append(sRow);
    }
    if (existingCards.length) {
      const cRow = el('div', { class: 'row', style: 'margin-bottom:6px;' }, el('strong', { text: 'Preservar cards nos editores: ' }));
      for (const c of existingCards) {
        cRow.append(el('label', { class: 'inline-check' },
          el('input', { type: 'checkbox', class: 'p-preserve-card', value: c.id }),
          el('span', { text: c.id }),
        ));
      }
      preserveBox.append(cRow);
    }
    const chRow = el('div', { class: 'row' }, el('strong', { text: 'Preservar textos de canais existentes: ' }));
    for (const pid of Array.from(oldChannels)) {
      chRow.append(el('label', { class: 'inline-check' },
        el('input', { type: 'checkbox', class: 'p-preserve-channel', value: pid }),
        el('span', { text: pid }),
      ));
    }
    preserveBox.append(chRow);
    renderDiffOutput(planningOverview.editorsDiff);
  }

  function renderDiffOutput(diff) {
    const out = $('#p-diff-output');
    out.innerHTML = '';
    if (!diff) return;
    const grid = el('div', { class: 'planning-analysis-grid' });

    const bCard = el('div', { class: 'planning-card' }, el('h3', { text: 'Briefing editorial' }));
    if (!(diff.briefing?.changes || []).length) {
      bCard.append(el('p', { class: 'muted', text: 'Sem diferença em relação à Ficha Editorial.' }));
    } else {
      const ul = el('ul', { style: 'margin:0 0 0 18px;' });
      for (const ch of diff.briefing.changes) {
        ul.append(el('li', { text: `${ch.label}: "${ch.before || '(vazio)'}" → "${ch.after}"` }));
      }
      bCard.append(ul);
    }

    const vCard = el('div', { class: 'planning-card' }, el('h3', { text: 'Vídeos & Motion' }));
    const vInfo = diff.video || {};
    vCard.append(el('p', {
      text: vInfo.readyToApply
        ? `Pronto para aplicar (${(vInfo.sceneChanges || []).length} cenas, perfis: ${(vInfo.targetProfiles || []).join(', ') || 'padrão'}).`
        : ((vInfo.pendingMediaScenes || []).length
          ? `Pendente de mídia local nas cenas: ${vInfo.pendingMediaScenes.join(', ')}`
          : 'Nenhuma cena pronta para aplicar.'),
    }));
    if ((diff.motion?.keptEffects || []).length || (diff.motion?.removedEffects || []).length) {
      vCard.append(el('p', {
        class: 'muted',
        text: `Motion: mantém contornos em [${(diff.motion?.keptEffects || []).join(', ')}]; remove incompatíveis [${(diff.motion?.removedEffects || []).join(', ')}].`,
      }));
    }

    const cCard = el('div', { class: 'planning-card' }, el('h3', { text: 'Carrosséis' }));
    const cInfo = diff.carousel || {};
    cCard.append(el('p', {
      text: cInfo.readyToApply
        ? `Pronto para aplicar (${(cInfo.cardChanges || []).length} cards, perfil: ${cInfo.targetProfile}).`
        : 'Nenhuma alteração pendente em Carrosséis.',
    }));

    const chCard = el('div', { class: 'planning-card' }, el('h3', { text: 'Canais' }));
    const ulCh = el('ul', { style: 'margin:0 0 0 18px;' });
    for (const ch of (diff.channels || [])) {
      const statusHint = ch.preserved
        ? 'preservado'
        : (ch.changed ? (ch.willRequestChannelReviewOnly ? 'alterado (solicita apenas copy_outdated neste canal, sem re-render MP4)' : 'alterado') : 'sem alteração');
      ulCh.append(el('li', { text: `${ch.profileId}: ${statusHint}` }));
    }
    chCard.append(ulCh);

    grid.append(bCard, vCard, cCard, chCard);
    out.append(grid);
  }

  function renderStagedSuggestionBox() {
    const box = $('#p-staged-box');
    const titleEl = $('#p-staged-title');
    const warnEl = $('#p-staged-warnings');
    const diffEl = $('#p-staged-diff');
    if (!stagedSuggestionState || !stagedSuggestionState.suggestionRecord) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const rec = stagedSuggestionState.suggestionRecord;
    const d = stagedSuggestionState.diffPreview || {};
    titleEl.textContent = `Sugestão validada (${rec.stage} · ${rec.mode}${rec.model ? ' · ' + rec.model : ''}) — pronta para incorporar`;

    warnEl.innerHTML = '';
    if ((stagedSuggestionState.warnings || []).length) {
      warnEl.append(el('div', { class: 'alert-box warn', text: stagedSuggestionState.warnings.join(' | ') }));
    }

    diffEl.innerHTML = '';
    if (rec.stage === 'briefing') {
      const ul = el('ul', { style: 'margin:0 0 0 18px;' });
      for (const ch of (d.changedFields || [])) {
        ul.append(el('li', { text: `${ch.label}: "${ch.before || '(vazio)'}" → "${ch.after}"` }));
      }
      ul.append(el('li', { text: `Perguntas propostas: ${d.questionsCount ?? 0} · Afirmações: ${d.claimsCount ?? 0} · Lacunas: ${d.gapsCount ?? 0}` }));
      diffEl.append(ul);
    } else {
      diffEl.append(el('p', {
        text: `Hooks: ${d.hookOptionsCount ?? 0} (ativo: ${d.selectedHookId || '-'}) · Cenas novas/atualizadas: ${(d.videoScenesAdded || []).length}/${(d.videoScenesUpdated || []).length} · Cards novos/atualizados: ${(d.carouselCardsAdded || []).length}/${(d.carouselCardsUpdated || []).length} · Canais: ${(d.channelsProposed || []).join(', ')}`,
      }));
    }
  }

  function renderHistoryBox() {
    const box = $('#p-history-box');
    box.innerHTML = '';
    const hist = planningOverview?.planning?.suggestionHistory || [];
    if (!hist.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma sugestão importada ou gerada neste trabalho ainda.' }));
      return;
    }
    for (const rec of hist.slice().reverse()) {
      box.append(el('div', { class: 'planning-item' },
        el('div', { class: 'planning-item-head' },
          el('div', {},
            el('strong', { text: `${rec.suggestionId}` }),
            el('span', { class: 'muted', text: ` · ${rec.stage} · ${rec.mode}${rec.model ? ' (' + rec.model + ')' : ''} · ${rec.createdAt || ''}` }),
          ),
          el('button', {
            type: 'button',
            class: 'secondary',
            text: 'Visualizar / Incorporar',
            onclick: () => {
              stagedSuggestionState = {
                suggestionRecord: rec,
                diffPreview: { stage: rec.stage, hookOptionsCount: (rec.suggestion?.hookOptions || []).length },
                warnings: rec.warnings || [],
              };
              renderStagedSuggestionBox();
              $('#p-staged-box').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            },
          }),
        ),
      ));
    }
  }

  function renderLlmConfigPanel() {
    if (!planningOverview) return;
    const cfg = planningOverview.llmConfig || {};
    const ext = planningOverview.imageExtensionPoint || {};
    if ($('#p-image-ext-note') && ext.message) $('#p-image-ext-note').textContent = ext.message;
    if ($('#p-llm-enabled')) $('#p-llm-enabled').checked = Boolean(cfg.enabled);
    if ($('#p-llm-endpoint') && cfg.endpoint) $('#p-llm-endpoint').value = cfg.endpoint;
    if ($('#p-llm-model') && cfg.model) $('#p-llm-model').value = cfg.model;
    if ($('#p-llm-timeout') && cfg.timeoutSec != null) $('#p-llm-timeout').value = String(cfg.timeoutSec);
  }

  function renderPlanningPanel() {
    renderWorkBanner();
    const pl = planningOverview?.planning;
    if ($('#p-media-count')) $('#p-media-count').textContent = String((planningOverview?.workMedia || []).length);

    if (pl) {
      $('#p-idea-text').value = pl.ideaText || '';
      $('#p-b-product').value = pl.briefingExtended?.product || '';
      $('#p-b-audience').value = pl.briefing?.audience || '';
      $('#p-b-objective').value = pl.briefing?.objective || '';
      $('#p-b-core').value = pl.briefing?.coreMessage || '';
      $('#p-b-evidence').value = pl.briefing?.supportEvidence || '';
      $('#p-b-cta').value = pl.briefing?.cta || '';
      $('#p-b-tone').value = pl.briefingExtended?.tone || '';
      $('#p-b-hook').value = pl.briefing?.hook || '';
      $('#p-b-script').value = pl.creative?.scriptSummary || pl.briefing?.scriptSummary || '';
    } else {
      for (const id of ['p-idea-text', 'p-b-product', 'p-b-audience', 'p-b-objective', 'p-b-core', 'p-b-evidence', 'p-b-cta', 'p-b-tone', 'p-b-hook', 'p-b-script']) {
        if ($('#' + id)) $('#' + id).value = '';
      }
    }

    renderAnalysisBoxes();
    renderAllowedProfilesCheckboxes();
    renderQuestionsList();
    renderClaimsList();
    renderHooksList();
    renderScenesList();
    renderCardsList();
    renderPlanningChannelsList();
    renderMotionSuggestionsEditor();
    renderStage3Controls();
    renderStagedSuggestionBox();
    renderHistoryBox();
    renderLlmConfigPanel();
  }

  function syncPlanningFromDOM() {
    if (!planningOverview || !planningOverview.planning) return;
    const pl = planningOverview.planning;
    pl.ideaText = $('#p-idea-text')?.value || '';
    pl.briefing = {
      objective: ($('#p-b-objective')?.value || '').trim(),
      audience: ($('#p-b-audience')?.value || '').trim(),
      coreMessage: ($('#p-b-core')?.value || '').trim(),
      supportEvidence: ($('#p-b-evidence')?.value || '').trim(),
      hook: ($('#p-b-hook')?.value || '').trim(),
      scriptSummary: ($('#p-b-script')?.value || '').trim(),
      cta: ($('#p-b-cta')?.value || '').trim(),
    };
    const recProfiles = [];
    document.querySelectorAll('.p-profile-check:checked').forEach((chk) => recProfiles.push(chk.value));
    pl.briefingExtended = {
      product: ($('#p-b-product')?.value || '').trim(),
      tone: ($('#p-b-tone')?.value || '').trim(),
      recommendedProfiles: recProfiles,
    };

    const qs = [];
    document.querySelectorAll('#p-questions-list [data-q-index]').forEach((row) => {
      qs.push({
        id: row.getAttribute('data-q-id') || undefined,
        dimension: row.querySelector('.p-q-dim')?.value || 'objective',
        question: (row.querySelector('.p-q-text')?.value || '').trim(),
        answer: (row.querySelector('.p-q-answer')?.value || '').trim(),
      });
    });
    if (document.querySelectorAll('#p-questions-list [data-q-index]').length) pl.questions = qs;

    const claims = [];
    document.querySelectorAll('#p-claims-list [data-c-index]').forEach((row) => {
      const statement = (row.querySelector('.p-claim-statement')?.value || '').trim();
      if (!statement) return;
      claims.push({
        id: row.getAttribute('data-c-id') || undefined,
        statement,
        status: row.querySelector('.p-claim-status')?.value || 'pending_validation',
        evidenceMediaId: row.querySelector('.p-claim-evidence-media')?.value || '',
        warning: (row.querySelector('.p-claim-warning')?.value || '').trim(),
        requiresConfirmation: Boolean(row.querySelector('.p-claim-requires-conf')?.checked),
      });
    });
    pl.claims = claims;

    const hooks = [];
    let selectedHookId = pl.creative.selectedHookId || '';
    document.querySelectorAll('#p-hooks-list [data-h-index]').forEach((row) => {
      const text = (row.querySelector('.p-hook-text')?.value || '').trim();
      if (!text) return;
      const radio = row.querySelector('.p-hook-radio');
      const hid = row.getAttribute('data-h-id') || (radio ? radio.value : '');
      if (radio?.checked) selectedHookId = hid;
      hooks.push({
        id: hid,
        text,
        angle: (row.querySelector('.p-hook-angle')?.value || '').trim(),
      });
    });

    const scenes = [];
    document.querySelectorAll('#p-scenes-list [data-s-index]').forEach((row) => {
      scenes.push({
        id: (row.querySelector('.p-scene-id')?.value || '').trim(),
        narrativeFunction: row.querySelector('.p-scene-nf')?.value || 'demonstration',
        durationMs: Number(row.querySelector('.p-scene-duration')?.value || 4000),
        motionIntent: row.querySelector('.p-scene-motion')?.value || 'none',
        mediaId: row.querySelector('.p-scene-media')?.value || '',
        requiredMediaDescriptor: (row.querySelector('.p-scene-desc')?.value || '').trim(),
        titleOverlay: (row.querySelector('.p-scene-title')?.value || '').trim(),
        caption: (row.querySelector('.p-scene-caption')?.value || '').trim(),
        objective: (row.querySelector('.p-scene-objective')?.value || '').trim(),
        narration: (row.querySelector('.p-scene-narration')?.value || '').trim(),
      });
    });

    const cards = [];
    document.querySelectorAll('#p-cards-list [data-card-index]').forEach((row) => {
      cards.push({
        id: (row.querySelector('.p-card-id')?.value || '').trim(),
        role: row.querySelector('.p-card-role')?.value || 'content',
        mediaId: row.querySelector('.p-card-media')?.value || '',
        requiredMediaDescriptor: (row.querySelector('.p-card-desc')?.value || '').trim(),
        title: (row.querySelector('.p-card-title')?.value || '').trim(),
        body: (row.querySelector('.p-card-body')?.value || '').trim(),
      });
    });

    const channelCopies = {};
    document.querySelectorAll('#p-channels-list [data-p-channel-id]').forEach((card) => {
      const pid = card.getAttribute('data-p-channel-id');
      const val = (f) => (card.querySelector(`[data-pch-field="${f}"]`)?.value || '').trim();
      channelCopies[pid] = {
        profileId: pid,
        title: val('title'),
        postText: val('postText'),
        cta: val('cta'),
        destinationUrl: val('destinationUrl'),
        hashtags: val('hashtags'),
      };
    });

    const motionSuggestions = [];
    document.querySelectorAll('#p-motion-suggestions-list [data-ms-index]').forEach((row) => {
      const sceneId = (row.querySelector('.p-ms-scene')?.value || '').trim();
      const targetElement = (row.querySelector('.p-ms-target')?.value || '').trim();
      if (!sceneId || !targetElement) return;
      motionSuggestions.push({
        sceneId,
        targetElement,
        suggestedColor: (row.querySelector('.p-ms-color')?.value || '#FFD700').trim(),
        suggestedStartMs: Number(row.querySelector('.p-ms-start')?.value || 400),
        suggestedEndMs: Number(row.querySelector('.p-ms-end')?.value || 2800),
        note: (row.querySelector('.p-ms-note')?.value || '').trim(),
      });
    });

    pl.creative = {
      ...pl.creative,
      hookOptions: hooks,
      selectedHookId,
      scriptSummary: pl.briefing.scriptSummary,
      videoScenes: scenes,
      carouselCards: cards,
      channelCopies,
      motionSuggestions,
    };
  }

  async function savePlanning(extraOpts) {
    if (!currentWork) { toast('Abra ou crie um trabalho primeiro.'); return null; }
    syncPlanningFromDOM();
    const pl = planningOverview.planning;
    const opts = extraOpts || {};
    const payload = {
      workId: currentWork.id,
      expectedContextFingerprint: planningOverview.fingerprints?.contextFingerprint,
      currentStage: opts.nextStage || pl.currentStage,
      ideaText: pl.ideaText,
      briefing: pl.briefing,
      briefingExtended: pl.briefingExtended,
      questions: pl.questions,
      claims: pl.claims,
      creative: pl.creative,
      markCreativeChecked: Boolean(opts.markCreativeChecked),
    };
    const data = await pRequest('POST', '/api/works/planning/save', payload);
    applyPlanningOverview(data);
    toast('Planejamento salvo no trabalho.');
    return data;
  }

  async function syncFromEditorialBriefing() {
    if (!currentWork) return null;
    const data = await pRequest('POST', '/api/works/planning/save', {
      workId: currentWork.id,
      syncFromEditorialBriefing: true,
    });
    applyPlanningOverview(data);
    toast('Briefing importado da Ficha Editorial.');
    return data;
  }

  async function buildPromptForStage() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    await savePlanning();
    const stage = $('#p-import-stage')?.value || 'briefing';
    const res = await pRequest('POST', '/api/works/planning/prompt', { workId: currentWork.id, stage });
    if ($('#p-prompt-output')) $('#p-prompt-output').value = res.promptText || '';
    toast(`Prompt da etapa "${stage}" gerado.`);
  }

  async function copyPromptToClipboard() {
    const text = $('#p-prompt-output')?.value || '';
    if (!text) { toast('Gere o prompt primeiro.'); return; }
    try {
      await navigator.clipboard.writeText(text);
      toast('Prompt copiado para a área de transferência.');
    } catch {
      $('#p-prompt-output').select();
      toast('Selecione e copie o prompt exibido.');
    }
  }

  async function validateAndImportSuggestion() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    const stage = $('#p-import-stage')?.value || 'briefing';
    const rawText = $('#p-import-json')?.value || '';
    const res = await pRequest('POST', '/api/works/planning/import', {
      workId: currentWork.id,
      stage,
      rawText,
      expectedContextFingerprint: planningOverview?.fingerprints?.contextFingerprint,
    });
    stagedSuggestionState = {
      suggestionRecord: res.suggestionRecord,
      diffPreview: res.diffPreview,
      warnings: res.warnings || [],
    };
    applyPlanningOverview(res.overview);
    toast('Sugestão validada pelo contrato do núcleo! Confira a diferença e clique em Incorporar.');
  }

  function collectLlmConfigInputs() {
    return {
      enabled: Boolean($('#p-llm-enabled')?.checked),
      endpoint: ($('#p-llm-endpoint')?.value || '').trim(),
      model: ($('#p-llm-model')?.value || '').trim(),
      timeoutSec: Number($('#p-llm-timeout')?.value || 15),
    };
  }

  async function saveLlmConfigOnly() {
    const res = await pRequest('POST', '/api/llm/config', collectLlmConfigInputs());
    if (planningOverview) planningOverview.llmConfig = res.llmConfig;
    renderLlmConfigPanel();
    if ($('#p-llm-status')) $('#p-llm-status').textContent = `Configuração salva (${res.llmConfig.enabled ? 'ativado' : 'desativado'} · ${res.llmConfig.model}).`;
    toast('Configuração do modelo local salva.');
  }

  async function generateWithLocalModelUI() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    await savePlanning();
    const stage = $('#p-llm-stage')?.value || 'briefing';
    const llmCfg = collectLlmConfigInputs();
    if ($('#p-llm-status')) $('#p-llm-status').textContent = `Consultando ${llmCfg.model} em ${llmCfg.endpoint}…`;
    const res = await pRequest('POST', '/api/works/planning/generate', {
      workId: currentWork.id,
      stage,
      expectedContextFingerprint: planningOverview?.fingerprints?.contextFingerprint,
      llmConfig: llmCfg,
    });
    stagedSuggestionState = {
      suggestionRecord: res.suggestionRecord,
      diffPreview: res.diffPreview,
      warnings: res.warnings || [],
      llmResponseMeta: res.llmResponseMeta,
    };
    applyPlanningOverview(res.overview);
    if ($('#p-llm-status')) {
      $('#p-llm-status').textContent = `Resposta validada de ${res.llmResponseMeta?.model || llmCfg.model}. Confira a diferença e aceite abaixo.`;
    }
    toast('Sugestão do modelo local validada com sucesso!');
  }

  async function acceptStagedSuggestion() {
    if (!currentWork || !stagedSuggestionState?.suggestionRecord) return;
    const rec = stagedSuggestionState.suggestionRecord;
    const preserveSceneIds = [];
    if ($('#p-accept-preserve-scenes')?.checked) {
      for (const s of (planningOverview?.planning?.creative?.videoScenes || [])) preserveSceneIds.push(s.id);
    }
    const preserveCardIds = [];
    if ($('#p-accept-preserve-cards')?.checked) {
      for (const c of (planningOverview?.planning?.creative?.carouselCards || [])) preserveCardIds.push(c.id);
    }
    const preserveChannelIds = [];
    if ($('#p-accept-preserve-channels')?.checked) {
      for (const pid of Object.keys(planningOverview?.planning?.creative?.channelCopies || {})) preserveChannelIds.push(pid);
    }
    const overview = await pRequest('POST', '/api/works/planning/accept-suggestion', {
      workId: currentWork.id,
      suggestionId: rec.suggestionId,
      expectedContextFingerprint: planningOverview?.fingerprints?.contextFingerprint,
      preserveQuestions: Boolean($('#p-accept-preserve-questions')?.checked),
      preserveHook: Boolean($('#p-accept-preserve-hooks')?.checked),
      preserveBriefingHook: Boolean($('#p-accept-preserve-hooks')?.checked),
      preserveSceneIds,
      preserveCardIds,
      preserveChannelIds,
    });
    stagedSuggestionState = null;
    applyPlanningOverview(overview);
    toast('Sugestão incorporada ao rascunho de planejamento.');
  }

  function collectStage3Selection() {
    const channelsToApply = [];
    document.querySelectorAll('.p-apply-ch-check:checked').forEach((chk) => channelsToApply.push(chk.value));
    const preserveSceneIds = [];
    document.querySelectorAll('.p-preserve-scene:checked').forEach((chk) => preserveSceneIds.push(chk.value));
    const preserveCardIds = [];
    document.querySelectorAll('.p-preserve-card:checked').forEach((chk) => preserveCardIds.push(chk.value));
    const preserveChannelIds = [];
    document.querySelectorAll('.p-preserve-channel:checked').forEach((chk) => preserveChannelIds.push(chk.value));
    return {
      applyBriefing: Boolean($('#p-apply-briefing')?.checked),
      applyVideo: Boolean($('#p-apply-video')?.checked),
      applyCarousel: Boolean($('#p-apply-carousel')?.checked),
      applyMotionSync: Boolean($('#p-apply-motion')?.checked),
      channelsToApply,
      preserveSceneIds,
      preserveCardIds,
      preserveChannelIds,
    };
  }

  async function refreshStage3Diff() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    const sel = collectStage3Selection();
    await savePlanning({ nextStage: 'apply' });
    const res = await pRequest('POST', '/api/works/planning/diff', {
      workId: currentWork.id,
      ...sel,
    });
    renderDiffOutput(res.editorsDiff);
    toast('Diferença com os editores atualizada.');
  }

  async function applyPlanningSelected() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    const sel = collectStage3Selection();
    await savePlanning({ nextStage: 'apply' });
    const fps = planningOverview.fingerprints || {};
    const res = await pRequest('POST', '/api/works/planning/apply', {
      workId: currentWork.id,
      expectedContextFingerprint: fps.contextFingerprint,
      expectedEditorialBriefingSha256: fps.editorialBriefingSha256,
      expectedDraftsSha256: fps.draftsSha256,
      ...sel,
    });
    if (res.workData && typeof _origApplyOpenedWork === 'function') {
      _origApplyOpenedWork(res.workData);
    }
    if (res.overview) {
      applyPlanningOverview(res.overview);
    }
    const out = $('#p-apply-result');
    out.innerHTML = '';
    const app = res.applied || {};
    const cls = (app.video?.status === 'pending_media' || app.carousel?.status === 'pending_media') ? 'alert-box warn' : 'alert-box ok';
    const box = el('div', { class: cls });
    box.append(el('strong', { text: 'Resultado da aplicação aos editores:' }));
    const ul = el('ul', { style: 'margin:6px 0 0 18px;' });
    ul.append(el('li', { text: `Briefing editorial: ${app.briefing?.status || 'skipped'}` }));
    ul.append(el('li', { text: `Vídeos: ${app.video?.status || 'skipped'}${app.video?.message ? ' — ' + app.video.message : ''}` }));
    ul.append(el('li', { text: `Carrosséis: ${app.carousel?.status || 'skipped'}${app.carousel?.message ? ' — ' + app.carousel.message : ''}` }));
    ul.append(el('li', { text: `Motion sync: ${app.motion?.status || 'skipped'} (cenas: ${(app.motion?.sceneIds || []).join(', ') || '-'})` }));
    ul.append(el('li', { text: `Canais atualizados: ${Object.keys(app.channels || {}).join(', ') || 'nenhum'}` }));
    box.append(ul);
    out.append(box);
    toast('Aplicação aos editores concluída!');
  }

  function renderMotionPlanningSuggestions() {
    const box = $('#m-planning-suggestions');
    if (!box) return;
    box.innerHTML = '';
    const sugs = planningOverview?.planning?.creative?.motionSuggestions || [];
    if (!sugs.length) return;
    box.append(el('span', { class: 'muted', text: 'Sugestões do Planejamento (marque a região no canvas antes de gravar): ' }));
    for (const ms of sugs) {
      box.append(el('button', {
        type: 'button',
        class: 'effect-pill',
        text: `${ms.sceneId}: ${ms.targetElement}`,
        title: `${ms.note || ''} (${ms.suggestedColor || '#FFD700'}, ${ms.suggestedStartMs ?? 400}–${ms.suggestedEndMs ?? 2800}ms)`,
        onclick: () => {
          mStandaloneOverride = false;
          mCurrentSceneId = ms.sceneId;
          mImg = null;
          if (typeof afterMPlan === 'function') afterMPlan();
          if (!mEffectFor(ms.sceneId)) {
            if ($('#m-color')) $('#m-color').value = ms.suggestedColor || '#FFD700';
            if ($('#m-start')) $('#m-start').value = String(ms.suggestedStartMs ?? 400);
            if ($('#m-end')) $('#m-end').value = String(ms.suggestedEndMs ?? 2800);
            if ($('#m-region-info')) {
              $('#m-region-info').textContent = `Sugestão do Planejamento para "${ms.sceneId}": destacar "${ms.targetElement}". Arraste o retângulo diretamente sobre a imagem no canvas antes de salvar o MotionPlan.`;
            }
          }
          toast(`Cena "${ms.sceneId}" aberta para marcação no canvas.`);
        },
      }));
    }
  }

  function openMotionFromPlanning() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    mStandaloneOverride = false;
    if (typeof syncDraftFields === 'function') syncDraftFields();
    if (typeof syncMotionFromDraft === 'function') syncMotionFromDraft();
    setMode('motion');
    renderMotionPlanningSuggestions();
  }

  // ---- Hook global setMode e applyOpenedWork ----
  const _origSetMode = typeof setMode === 'function' ? setMode : null;
  const _origApplyOpenedWork = typeof applyOpenedWork === 'function' ? applyOpenedWork : null;

  if (_origSetMode) {
    setMode = function (mode) {
      if (mode === 'planning') {
        _origSetMode('home');
        for (const m of MODES_ALL) {
          const panel = $('#mode-' + m);
          if (panel) panel.hidden = m !== 'planning';
          const btn = $('#mode-' + m + '-btn');
          if (btn) btn.classList.toggle('active', m === 'planning');
        }
        renderPlanningPanel();
        loadPlanningOverview().catch(() => {});
        return;
      }
      const pPanel = $('#mode-planning');
      if (pPanel) pPanel.hidden = true;
      const pBtn = $('#mode-planning-btn');
      if (pBtn) pBtn.classList.remove('active');
      _origSetMode(mode);
      if (mode === 'motion') {
        renderMotionPlanningSuggestions();
      }
    };
  }

  if (_origApplyOpenedWork) {
    applyOpenedWork = function (data) {
      _origApplyOpenedWork(data);
      if ($('#p-apply-result')) $('#p-apply-result').innerHTML = '';
      if (data && data.planning) {
        stagedSuggestionState = null;
        applyPlanningOverview(data.planning);
      } else if (data && data.work) {
        loadPlanningOverview().catch(() => {});
      } else {
        applyPlanningOverview(null);
      }
    };
  }

  function initPlanningUI() {
    $('#mode-planning-btn')?.addEventListener('click', () => setMode('planning'));
    $('#p-btn-refresh')?.addEventListener('click', () => loadPlanningOverview().catch((e) => toast(e.message)));
    $('#p-btn-rescan-media')?.addEventListener('click', () => loadPlanningOverview().catch((e) => toast('Mídias atualizadas: ' + e.message)));
    $('#p-btn-save')?.addEventListener('click', () => savePlanning().catch(() => {}));
    $('#p-btn-save-stage1')?.addEventListener('click', () => savePlanning({ nextStage: 'briefing' }).catch(() => {}));
    $('#p-btn-go-stage2')?.addEventListener('click', () => {
      savePlanning({ nextStage: 'creative' })
        .then(() => $('#p-stage2-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
        .catch(() => {});
    });
    $('#p-btn-save-stage2')?.addEventListener('click', () => savePlanning({ nextStage: 'creative', markCreativeChecked: true }).catch(() => {}));
    $('#p-btn-mark-checked')?.addEventListener('click', () => savePlanning({ markCreativeChecked: true }).catch(() => {}));
    $('#p-btn-go-stage3')?.addEventListener('click', () => {
      savePlanning({ nextStage: 'apply', markCreativeChecked: true })
        .then(() => $('#p-stage3-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
        .catch(() => {});
    });

    $('#p-stage-btn-briefing')?.addEventListener('click', () => {
      savePlanning({ nextStage: 'briefing' }).catch(() => {});
      $('#p-stage1-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    $('#p-stage-btn-creative')?.addEventListener('click', () => {
      savePlanning({ nextStage: 'creative' }).catch(() => {});
      $('#p-stage2-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    $('#p-stage-btn-apply')?.addEventListener('click', () => {
      savePlanning({ nextStage: 'apply' }).catch(() => {});
      $('#p-stage3-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    document.querySelectorAll('input[name="p-fill-mode"]').forEach((r) => {
      r.addEventListener('change', () => { if (r.checked) updateFillModeUI(r.value); });
    });

    $('#p-btn-build-prompt')?.addEventListener('click', () => buildPromptForStage().catch(() => {}));
    $('#p-btn-copy-prompt')?.addEventListener('click', () => copyPromptToClipboard().catch(() => {}));
    $('#p-btn-validate-import')?.addEventListener('click', () => validateAndImportSuggestion().catch(() => {}));
    $('#p-btn-save-llm')?.addEventListener('click', () => saveLlmConfigOnly().catch(() => {}));
    $('#p-btn-generate-llm')?.addEventListener('click', () => generateWithLocalModelUI().catch(() => {}));
    $('#p-btn-accept-staged')?.addEventListener('click', () => acceptStagedSuggestion().catch(() => {}));
    $('#p-btn-discard-staged')?.addEventListener('click', () => {
      stagedSuggestionState = null;
      renderStagedSuggestionBox();
    });

    $('#p-btn-add-question')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      planningOverview.planning.questions.push({
        id: 'q-extra-' + (planningOverview.planning.questions.length + 1),
        dimension: 'objective',
        question: 'Qual detalhe extra ajuda a fechar esta etapa?',
        suggestedAnswer: '',
        answer: '',
      });
      renderQuestionsList();
    });

    $('#p-btn-add-claim')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      planningOverview.planning.claims.push({
        id: 'claim-' + (planningOverview.planning.claims.length + 1),
        statement: 'Nova afirmação para validar',
        status: 'pending_validation',
        requiresConfirmation: true,
        evidenceMediaId: '',
        warning: '',
      });
      renderClaimsList();
    });

    $('#p-btn-add-hook')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      const idx = planningOverview.planning.creative.hookOptions.length + 1;
      const hid = 'hook-' + idx;
      planningOverview.planning.creative.hookOptions.push({ id: hid, text: `Opção de abertura ${idx}`, angle: 'prático' });
      if (!planningOverview.planning.creative.selectedHookId) {
        planningOverview.planning.creative.selectedHookId = hid;
      }
      renderHooksList();
    });

    $('#p-btn-add-scene')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      const idx = planningOverview.planning.creative.videoScenes.length + 1;
      planningOverview.planning.creative.videoScenes.push({
        id: 'cena-' + idx,
        objective: '',
        narrativeFunction: 'demonstration',
        durationMs: 4000,
        titleOverlay: `Cena ${idx}`,
        caption: `Legenda curta da cena ${idx}`,
        narration: `Narração externa da cena ${idx}.`,
        requiredMediaDescriptor: 'Captura ou mídia local desta cena',
        mediaId: '',
        motionIntent: 'none',
      });
      renderScenesList();
    });

    $('#p-btn-add-card')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      const idx = planningOverview.planning.creative.carouselCards.length + 1;
      planningOverview.planning.creative.carouselCards.push({
        id: 'card-' + idx,
        role: idx === 1 ? 'cover' : 'content',
        title: `Card ${idx}`,
        body: 'Ponto direto deste card',
        requiredMediaDescriptor: '',
        mediaId: '',
      });
      renderCardsList();
    });

    $('#p-btn-add-motion-sug')?.addEventListener('click', () => {
      if (!planningOverview) return;
      syncPlanningFromDOM();
      const firstScene = planningOverview.planning.creative.videoScenes[0]?.id || 'cena-1';
      planningOverview.planning.creative.motionSuggestions.push({
        sceneId: firstScene,
        targetElement: 'Bloco ou botão principal da tela',
        suggestedColor: '#FFD700',
        suggestedStartMs: 400,
        suggestedEndMs: 2800,
        note: 'Desenhar região no canvas Motion',
      });
      renderMotionSuggestionsEditor();
    });

    $('#p-btn-diff')?.addEventListener('click', () => refreshStage3Diff().catch(() => {}));
    $('#p-btn-apply')?.addEventListener('click', () => applyPlanningSelected().catch(() => {}));
    $('#p-btn-open-video')?.addEventListener('click', () => setMode('video'));
    $('#p-btn-open-carousel')?.addEventListener('click', () => setMode('carousel'));
    $('#p-btn-open-motion')?.addEventListener('click', () => openMotionFromPlanning());
    $('#p-btn-open-review')?.addEventListener('click', () => setMode('review'));

    updateFillModeUI('manual');
    renderPlanningPanel();
  }

  window.StudioPlanningBridge = {
    save: () => savePlanning(),
    refresh: () => loadPlanningOverview(),
    getOverview: () => planningOverview,
  };

  initPlanningUI();
})();
