/* Biblioteca de midia por trabalho: aba Midias, pedidos visuais e comparacao de candidatos. */

(function () {
  let mediaOverview = null;
  let mediaLoadSeq = 0;
  let dialogState = null;

  // Helper variadico local (o el global de app.js usa assinatura (tag, attrs, children[])).
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === undefined || v === null || v === false) continue;
        if (k === 'text') node.textContent = String(v);
        else if (k === 'class') node.className = String(v);
        else if (k === 'checked') { node.checked = true; node.setAttribute('checked', ''); }
        else if (k === 'disabled') { node.disabled = Boolean(v); if (v) node.setAttribute('disabled', ''); }
        else if (k === 'value') { node.setAttribute('value', String(v)); if (tag !== 'textarea') node.value = String(v); }
        else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
        else if (v === true) node.setAttribute(k, '');
        else node.setAttribute(k, String(v));
      }
    }
    const appendItem = (item) => {
      if (item === undefined || item === null || item === false || item === '') return;
      if (Array.isArray(item)) { for (const sub of item) appendItem(sub); return; }
      node.append(item);
    };
    for (const child of children) appendItem(child);
    return node;
  }

  const MODES_ALL = ['home', 'planning', 'video', 'carousel', 'motion', 'media', 'review'];
  const ORIGIN_LABELS = {
    'imported-manual': 'Importação manual',
    'imported-recording': 'Gravação importada',
    'external-tool': 'Ferramenta externa (importada)',
    'generated-simulator': 'Ilustração gerada — simulador',
    'generated-google-gemini': 'Ilustração gerada — Google Gemini',
    'generated-google-gemini-video': 'Clipe gerado por API — Google Gemini',
    'synthetic-demo': 'Fictícia de demonstração',
    'studio-work': 'Arquivo do trabalho',
    'screenshot': 'Captura / evidência funcional',
  };

  function originLabel(origin) {
    return ORIGIN_LABELS[origin] || origin || 'origem não declarada';
  }

  function thumbUrl(assetId, versionId) {
    if (!currentWork) return '';
    return `/library-media?work=${encodeURIComponent(currentWork.id)}&asset=${encodeURIComponent(assetId)}&version=${encodeURIComponent(versionId)}`;
  }

  function mdShowError(err) {
    const box = $('#md-error-box');
    if (!box) return;
    box.hidden = false;
    box.textContent = err && err.message ? err.message : String(err);
  }

  function mdClearError() {
    const box = $('#md-error-box');
    if (box) { box.hidden = true; box.textContent = ''; }
  }

  function mdFeedback(message, kind) {
    const box = $('#md-feedback');
    if (!box) return;
    box.innerHTML = '';
    box.append(el('div', { class: 'alert-box ' + (kind || 'ok'), text: message }));
  }

  async function loadMediaOverview() {
    const seq = ++mediaLoadSeq;
    if (!currentWork) {
      mediaOverview = null;
      renderMediaPanel();
      return null;
    }
    const data = await api('/api/works/media-library?id=' + encodeURIComponent(currentWork.id));
    if (seq === mediaLoadSeq) {
      mediaOverview = data;
      renderMediaPanel();
    }
    return data;
  }

  function versionById(asset, versionId) {
    return (asset.versions || []).find((v) => v.versionId === versionId) || null;
  }

  function renderProviders() {
    const box = $('#md-providers');
    if (!box) return;
    box.innerHTML = '';
    for (const p of (mediaOverview && mediaOverview.providers) || []) {
      box.append(el('span', {
        class: 'badge ' + (p.available ? 'ok' : 'warn'),
        text: `${p.label}: ${p.available ? 'disponível' : 'indisponível'}${p.model ? ' · ' + p.model : ''}${p.connectionName ? ' · conexão ' + p.connectionName : ''}`,
        title: p.message || '',
      }));
    }
  }

  function renderAssetsGrid() {
    const box = $('#md-assets-grid');
    if (!box) return;
    box.innerHTML = '';
    const assets = (mediaOverview && mediaOverview.mediaLibrary && mediaOverview.mediaLibrary.assets) || [];
    if (!assets.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhuma mídia cadastrada ainda. Importe uma imagem autorizada ou cadastre um arquivo existente.' }));
      return;
    }
    for (const asset of assets) {
      const selected = asset.selectedVersion || versionById(asset, asset.selectedVersionId);
      const card = el('div', { class: 'media-card', 'data-asset-id': asset.id });
      const versionSel = el('select', { class: 'md-version-select' },
        ...(asset.versions || []).map((v) => el('option', {
          value: v.versionId,
          text: `${v.versionId} · ${v.width || '?'}×${v.height || '?'} · ${originLabel(v.origin)}${v.simulated ? ' · SIMULADA' : ''}`,
        })),
      );
      if (selected) versionSel.value = selected.versionId;
      const consumers = asset.consumers || [];
      const consumerText = consumers.length
        ? [...new Set(consumers.map((c) => `${c.modality}:${c.targetId}`))].join(', ')
        : 'sem vínculo ainda';
      card.append(
        el('div', { class: 'media-card-head' },
          el('strong', { text: asset.id }),
          el('span', { class: 'badge muted', text: asset.category || 'other' }),
          selected && selected.simulated ? el('span', { class: 'badge warn', text: 'SIMULADA' }) : null,
        ),
        selected && !selected.missing
          ? (selected.kind === 'video'
            ? el('video', { class: 'media-thumb', src: thumbUrl(asset.id, selected.versionId), muted: true, preload: 'metadata', controls: true })
            : el('img', { class: 'media-thumb', src: thumbUrl(asset.id, selected.versionId), alt: asset.name || asset.id, loading: 'lazy' }))
          : el('div', { class: 'badge err', text: 'arquivo ausente' }),
        el('p', { class: 'muted', text: asset.name || '' }),
        selected ? el('p', { class: 'timeline', text: `${selected.width}×${selected.height} · ${selected.bytes} bytes · ${selected.format || ''}${selected.kind === 'video' ? ` · ${selected.durationSeconds}s · ${selected.codec || ''}` : ''} · sha256 ${(selected.sha256 || '').slice(0, 12)}…` }) : null,
        selected ? el('p', { class: 'muted', text: `Origem: ${originLabel(selected.origin)} · Licença: ${selected.license || 'pending'}` }) : null,
        el('p', { class: 'muted', text: `Peças vinculadas: ${consumerText}` }),
        el('label', {}, 'Versão exibida ', versionSel),
        el('div', { class: 'row' },
          el('button', {
            type: 'button', class: 'secondary', text: 'Usar como referência',
            onclick: () => {
              $('#md-anchor-asset').value = asset.id;
              fillAnchorVersions(asset.id);
              $('#md-anchor-version').value = versionSel.value;
              $('#md-anchor-title').focus();
              $('#md-anchor-title').scrollIntoView({ behavior: 'smooth', block: 'center' });
            },
          }),
          el('button', {
            type: 'button', class: 'secondary', text: 'Atualizar versão em todas as peças',
            disabled: consumers.length ? null : 'disabled',
            title: consumers.length ? 'Atualiza os vínculos de todas as peças consumidoras (mídia compartilhada)' : 'Nenhuma peça vinculada a esta mídia',
            onclick: () => updateSharedVersion(asset.id, versionSel.value).catch((e) => mdShowError(e)),
          }),
        ),
        el('details', {},
          el('summary', { text: `Histórico de versões (${(asset.versions || []).length})` }),
          el('div', {}, ...(asset.versions || []).map((v) => el('p', {
            class: 'muted',
            text: `${v.versionId} · ${v.createdAt || ''} · ${originLabel(v.origin)}${v.simulated ? ' · SIMULADA' : ''} · sha256 ${(v.sha256 || '').slice(0, 12)}…${v.requestId ? ' · pedido ' + v.requestId : ''}`,
          }))),
        ),
      );
      box.append(card);
    }
  }

  async function updateSharedVersion(assetId, versionId) {
    if (!currentWork) return;
    const asset = ((mediaOverview || {}).mediaLibrary || {}).assets.find((a) => a.id === assetId);
    const consumers = (asset && asset.consumers) || [];
    const list = [...new Set(consumers.map((c) => `${c.modality}:${c.targetId}`))].join(', ');
    if (!window.confirm(`Atualizar a versão de "${assetId}" em todas as peças vinculadas (${list})? As peças afetadas pedirão nova revisão.`)) return;
    const data = await post('/api/works/media/select', {
      workId: currentWork.id,
      assetId, versionId,
      updateLinkedTargets: true,
      expectedLibraryFingerprint: mediaOverview && mediaOverview.libraryFingerprint,
    });
    mediaOverview = data.overview;
    renderMediaPanel();
    mdFeedback(`Versão ${versionId} aplicada a: ${data.targets.map((t) => t.targetKind + ':' + t.targetId).join(', ')}. Peças afetadas pedirão nova revisão.`);
    await openWork(currentWork.id);
    if (window.StudioPlanningBridge) window.StudioPlanningBridge.refresh().catch(() => {});
  }

  function fillAnchorVersions(assetId) {
    const sel = $('#md-anchor-version');
    if (!sel) return;
    sel.innerHTML = '';
    const asset = (((mediaOverview || {}).mediaLibrary || {}).assets || []).find((a) => a.id === assetId);
    for (const v of (asset && asset.versions) || []) {
      sel.append(el('option', { value: v.versionId, text: `${v.versionId} · ${originLabel(v.origin)}` }));
    }
    if (asset && asset.selectedVersionId) sel.value = asset.selectedVersionId;
  }

  function renderAnchorControls() {
    const assetSel = $('#md-anchor-asset');
    if (!assetSel) return;
    const prev = assetSel.value;
    assetSel.innerHTML = '';
    const assets = ((mediaOverview || {}).mediaLibrary || {}).assets || [];
    for (const a of assets) assetSel.append(el('option', { value: a.id, text: a.id }));
    if (prev && assets.some((a) => a.id === prev)) assetSel.value = prev;
    fillAnchorVersions(assetSel.value);

    const list = $('#md-anchors-list');
    list.innerHTML = '';
    const anchors = ((mediaOverview || {}).mediaLibrary || {}).anchors || [];
    if (!anchors.length) {
      list.append(el('p', { class: 'muted', text: 'Nenhuma referência visual cadastrada.' }));
      return;
    }
    for (const record of anchors) {
      const a = record.anchor;
      list.append(el('div', { class: 'review-card', 'data-anchor-id': a.id },
        el('div', { class: 'review-card-head' },
          el('strong', { text: a.title }),
          el('span', { class: 'badge muted', text: a.id }),
        ),
        el('div', { class: 'row' },
          el('img', { class: 'media-thumb small', src: thumbUrl(a.reference.mediaId, a.reference.versionId), alt: a.title, loading: 'lazy' }),
          el('div', {},
            el('p', { text: a.direction }),
            el('p', { class: 'muted', text: `Referência: ${a.reference.mediaId} @ ${a.reference.versionId} · sha256 ${a.reference.sha256.slice(0, 12)}…` }),
            (a.mustInclude || []).length ? el('p', { class: 'muted', text: 'Precisa aparecer: ' + a.mustInclude.join('; ') }) : null,
            (a.mustAvoid || []).length ? el('p', { class: 'muted', text: 'Evitar: ' + a.mustAvoid.join('; ') }) : null,
          ),
        ),
      ));
    }
  }

  function renderRegisterSelect() {
    const sel = $('#md-register-select');
    if (!sel) return;
    sel.innerHTML = '';
    const files = (mediaOverview && mediaOverview.unregisteredFiles) || [];
    if (!files.length) {
      sel.append(el('option', { value: '', text: '— nenhum arquivo pendente de cadastro —' }));
    } else {
      for (const f of files) sel.append(el('option', { value: f.path, text: `${f.name} (${f.bytes} bytes)` }));
    }
    const assetSel = $('#md-import-asset');
    if (assetSel) {
      const prev = assetSel.value;
      assetSel.innerHTML = '';
      assetSel.append(el('option', { value: '', text: '— criar nova mídia —' }));
      for (const a of ((mediaOverview || {}).mediaLibrary || {}).assets || []) {
        assetSel.append(el('option', { value: a.id, text: a.id }));
      }
      if (prev) assetSel.value = prev;
    }
  }

  function candidateCard(reqEntry, cand, asset) {
    const version = asset ? versionById(asset, cand.versionId) : null;
    const card = el('div', { class: 'media-card candidate' + (cand.stale ? ' stale' : ''), 'data-candidate-id': cand.candidateId });
    card.append(
      el('div', { class: 'media-card-head' },
        el('strong', { text: cand.provider === 'manual' ? 'Importada' : cand.provider }),
        cand.stale ? el('span', { class: 'badge warn', text: 'Contexto anterior' }) : el('span', { class: 'badge ok', text: 'Contexto atual' }),
        reqEntry.selectedCandidateId === cand.candidateId ? el('span', { class: 'badge ok', text: 'Selecionada' }) : null,
      ),
      version && !version.missing
        ? el('img', { class: 'media-thumb', src: thumbUrl(cand.assetId, cand.versionId), alt: cand.candidateId, loading: 'lazy' })
        : el('div', { class: 'badge err', text: 'arquivo ausente' }),
      el('p', { class: 'muted', text: `${cand.model || 'manual'} · ${cand.createdAt || ''}` }),
      version ? el('p', { class: 'timeline', text: `${version.width}×${version.height} · sha256 ${(version.sha256 || '').slice(0, 12)}…` }) : null,
      version ? el('p', { class: 'muted', text: `Origem: ${originLabel(version.origin)}${version.simulated ? ' (material simulado)' : ''}` }) : null,
      el('button', {
        type: 'button', text: 'Selecionar esta versão',
        onclick: () => selectCandidate(reqEntry, cand).catch((e) => dialogError(e)),
      }),
    );
    return card;
  }

  function renderRequestsList() {
    const box = $('#md-requests-list');
    if (!box) return;
    box.innerHTML = '';
    const requests = ((mediaOverview || {}).mediaLibrary || {}).requests || [];
    if (!requests.length) {
      box.append(el('p', { class: 'muted', text: 'Nenhum pedido visual ainda. Abra o Planejamento e use "Preparar imagem" em uma cena ou card.' }));
      return;
    }
    const assets = ((mediaOverview || {}).mediaLibrary || {}).assets || [];
    for (const entry of requests) {
      const req = entry.request;
      const card = el('div', { class: 'review-card', 'data-request-id': req.id });
      const strip = el('div', { class: 'media-grid' });
      for (const cand of entry.candidates || []) {
        strip.append(candidateCard(entry, cand, assets.find((a) => a.id === cand.assetId)));
      }
      card.append(
        el('div', { class: 'review-card-head' },
          el('strong', { text: `${req.target.kind === 'video_scene' ? 'Cena' : 'Card'} ${req.target.id}` }),
          el('span', { class: 'badge muted', text: req.id }),
          el('span', { class: 'badge ' + (entry.status === 'failed' ? 'err' : entry.status === 'completed' ? 'ok' : 'warn'), text: entry.status }),
          entry.contextOutdated ? el('span', { class: 'badge warn', text: 'Referência/contexto alterado' }) : null,
        ),
        el('p', { class: 'muted', text: `Perfil ${req.profileId} · ${req.aspectRatio} · ${req.geometry.width}×${req.geometry.height}` }),
        el('p', { text: req.prompt }),
        (entry.attempts || []).length
          ? el('details', {},
              el('summary', { text: `Tentativas (${entry.attempts.length})` }),
              el('div', {}, ...entry.attempts.map((t) => el('p', {
                class: t.status === 'failed' ? 'alert-box err' : 'muted',
                text: `${t.at} · ${t.provider} · ${t.status}${t.error ? ' — ' + t.error : ''}`,
              }))),
            )
          : null,
        strip,
        el('div', { class: 'row' },
          el('button', { type: 'button', class: 'secondary', text: 'Abrir pedido', onclick: () => openRequest(req.target.kind, req.target.id, req.id).catch((e) => mdShowError(e)) }),
        ),
      );
      box.append(card);
    }
  }

  function renderMediaPanel() {
    const hasWork = Boolean(currentWork);
    if ($('#md-no-work-alert')) $('#md-no-work-alert').hidden = hasWork;
    if ($('#md-work-content')) $('#md-work-content').hidden = !hasWork;
    if (!hasWork) return;
    renderProviders();
    renderAssetsGrid();
    renderAnchorControls();
    renderRegisterSelect();
    renderRequestsList();
    renderVideoPanel();
  }

  // ---- dialogo de pedido visual (Preparar imagem) ----

  function dialogError(err) {
    if (!dialogState) return;
    const box = dialogState.errorBox;
    if (box) {
      box.hidden = false;
      box.textContent = err && err.message ? err.message : String(err);
    }
  }

  function closeDialog() {
    const root = $('#media-dialog-root');
    if (root) root.innerHTML = '';
    dialogState = null;
  }

  async function openRequest(targetKind, targetId, requestId) {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    if (window.StudioPlanningBridge) {
      await window.StudioPlanningBridge.save();
    }
    const [lib, planning] = await Promise.all([
      api('/api/works/media-library?id=' + encodeURIComponent(currentWork.id)),
      api('/api/works/planning?id=' + encodeURIComponent(currentWork.id)),
    ]);
    mediaOverview = lib;
    const requests = (lib.mediaLibrary || {}).requests || [];
    const entry = requestId
      ? requests.find((r) => r.request.id === requestId)
      : [...requests].reverse().find((r) => r.request.target.kind === targetKind && r.request.target.id === targetId);
    const creative = planning.planning.creative;
    const item = targetKind === 'video_scene'
      ? (creative.videoScenes || []).find((s) => s.id === targetId)
      : (creative.carouselCards || []).find((c) => c.id === targetId);
    if (!item) { toast('Cena/card não encontrado no Planejamento. Salve o roteiro antes de preparar a imagem.'); return; }
    showDialog(targetKind, targetId, item, entry, planning, lib);
  }

  function showDialog(targetKind, targetId, item, entry, planning, lib) {
    const root = $('#media-dialog-root');
    root.innerHTML = '';
    const overlay = el('div', { class: 'media-dialog-overlay' });
    const dialog = el('div', { class: 'media-dialog', role: 'dialog', 'aria-modal': 'true' });
    const errorBox = el('div', { class: 'alert-box err', hidden: 'hidden' });
    const body = el('div', { class: 'media-dialog-body' });
    dialog.append(
      el('div', { class: 'media-dialog-head' },
        el('h2', { text: `Preparar imagem — ${targetKind === 'video_scene' ? 'cena' : 'card'} ${targetId}` }),
        el('button', { type: 'button', class: 'secondary', text: 'Fechar', onclick: closeDialog }),
      ),
      errorBox,
      body,
    );
    overlay.append(dialog);
    overlay.addEventListener('click', (ev) => { if (ev.target === overlay) closeDialog(); });
    root.append(overlay);
    dialogState = { targetKind, targetId, item, entry, planning, lib, errorBox, body, dialog };
    renderDialogBody();
  }

  function renderDialogBody() {
    const st = dialogState;
    if (!st) return;
    const { body, entry, planning, lib } = st;
    body.innerHTML = '';
    const req = entry ? entry.request : null;
    const descriptor = st.item.requiredMediaDescriptor || '';
    const allowed = (planning.allowedProfiles || []).filter((p) => st.targetKind === 'video_scene' ? p.localExportVideo : p.localExportCarousel);
    const anchors = (lib.mediaLibrary || {}).anchors || [];

    const promptArea = el('textarea', { rows: '4', class: 'md-req-prompt', placeholder: 'Descrição visual que será enviada ao provedor' });
    promptArea.value = req ? req.prompt : (descriptor || st.item.objective || st.item.title || '');
    const purposeInput = el('input', { type: 'text', class: 'md-req-purpose', value: req ? req.purpose : (st.item.objective || st.item.title || `Imagem para ${st.targetId}`) });
    const framingInput = el('input', { type: 'text', class: 'md-req-framing', value: req ? req.framing : 'Plano médio, elemento centralizado' });
    const profileSel = el('select', { class: 'md-req-profile' }, ...allowed.map((p) => el('option', { value: p.id, text: `${p.id} (${p.aspectRatio})` })));
    if (req) profileSel.value = req.profileId;
    const anchorSel = el('select', { class: 'md-req-anchor' },
      el('option', { value: '', text: '— sem referência visual —' }),
      ...anchors.map((a) => el('option', { value: a.anchor.id, text: `${a.anchor.title} (${a.anchor.id})` })),
    );
    if (req && req.anchor) anchorSel.value = req.anchor.anchorId;
    const sendCheck = el('input', { type: 'checkbox', class: 'md-req-send-anchor' });
    if (req && req.anchor && req.anchor.sendToProvider) sendCheck.checked = true;
    const framingNote = el('p', { class: 'muted md-req-framing-note' });
    profileSel.addEventListener('change', () => updateFramingNote());
    function updateFramingNote() {
      const pid = profileSel.value;
      const prof = (planning.allowedProfiles || []).find((p) => p.id === pid);
      const framing = entry ? entry.framing : null;
      const mw = framing && framing.mediaWidth;
      const mh = framing && framing.mediaHeight;
      if (!prof) { framingNote.textContent = ''; return; }
      let text = `Destino ${pid}: quadro ${prof.width}×${prof.height} (${prof.aspectRatio}). `;
      if (mw && mh) {
        const fit = Math.min(prof.width / mw, prof.height / mh);
        const dw = mw * fit, dh = mh * fit;
        const bands = dw < prof.width - 1 ? 'bandas verticais (pillarbox)' : (dh < prof.height - 1 ? 'bandas horizontais (letterbox)' : 'sem bandas');
        text += `Mídia atual ${mw}×${mh} será enquadrada com preservação de proporção (fit + pad centralizado): ${bands}. `;
        text += 'Reaproveite a versão existente ou prepare um candidato para o novo quadro; o contexto do pedido será atualizado.';
      } else {
        text += 'Nenhuma mídia selecionada ainda para este alvo.';
      }
      framingNote.textContent = text;
    }
    updateFramingNote();

    body.append(
      el('p', { class: 'muted', text: `Descritor da peça: ${descriptor || '(vazio)'}` }),
      el('p', { class: 'muted', text: 'Títulos, legendas e CTA continuam nos campos editáveis da peça; aqui fica apenas o pedido visual.' }),
      el('label', {}, 'Prompt editável ', promptArea),
      el('div', { class: 'row' },
        el('label', {}, 'Finalidade ', purposeInput),
        el('label', {}, 'Enquadramento ', framingInput),
        el('label', {}, 'Perfil (proporção) ', profileSel),
      ),
      framingNote,
      el('div', { class: 'row' },
        el('label', {}, 'Referência visual ', anchorSel),
        el('label', { class: 'row' }, sendCheck, ' Enviar referência ao provedor'),
      ),
      el('div', { class: 'row' },
        el('button', { type: 'button', text: req ? 'Salvar alterações do pedido' : 'Criar pedido visual', onclick: () => saveRequestFromDialog().catch(dialogError) }),
        req ? el('button', { type: 'button', class: 'secondary', text: 'Copiar pedido', onclick: () => copyProviderText().catch(dialogError) }) : null,
      ),
    );

    if (!req) {
      body.append(el('p', { class: 'muted', text: 'Crie o pedido para ver o texto exato que será enviado, importar uma opção ou gerar candidatos.' }));
      return;
    }

    const preview = el('pre', { class: 'artifact-viewer md-provider-preview', text: entry.providerTextPreview || '' });
    const fileInput = el('input', { type: 'file', accept: '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp', class: 'md-req-file' });
    const providers = lib.providers || [];
    const gemini = providers.find((p) => p.providerId === 'google-gemini');
    const actions = el('div', { class: 'row' },
      el('button', { type: 'button', class: 'secondary', text: 'Importar opção (manual)', onclick: () => importCandidate(fileInput).catch(dialogError) }),
      el('button', { type: 'button', class: 'secondary', text: 'Gerar com simulador', onclick: () => generateCandidate('simulator').catch(dialogError) }),
      el('button', {
        type: 'button', class: 'secondary',
        text: gemini && gemini.available ? 'Gerar com Google Gemini' : 'Google Gemini (sem chave)',
        disabled: gemini && gemini.available ? null : 'disabled',
        title: gemini ? gemini.message : '',
        onclick: () => generateCandidate('google-gemini').catch(dialogError),
      }),
      fileInput,
    );
    body.append(
      el('h3', { text: 'Texto que será enviado ao provedor' }),
      preview,
      actions,
      el('p', { class: 'muted', text: 'Uma chamada por ação confirmada. Após timeout ou falha, o estado fica registrado e você decide se tenta novamente.' }),
    );

    const assets = (lib.mediaLibrary || {}).assets || [];
    const strip = el('div', { class: 'media-grid' });
    for (const cand of entry.candidates || []) {
      strip.append(candidateCard(entry, cand, assets.find((a) => a.id === cand.assetId)));
    }
    body.append(
      el('h3', { text: `Candidatos (${(entry.candidates || []).length})` }),
      (entry.candidates || []).length ? strip : el('p', { class: 'muted', text: 'Nenhum candidato ainda: importe uma opção ou gere com o simulador.' }),
    );
    if ((entry.candidates || []).some((c) => c.stale)) {
      body.append(el('div', { class: 'alert-box warn', text: 'Há candidatos produzidos com a versão anterior do pedido ou da referência (marcados como "Contexto anterior"). Gere ou importe novamente antes de selecionar, se quiser o contexto atual.' }));
    }
    if ((entry.attempts || []).length) {
      body.append(el('details', {},
        el('summary', { text: `Histórico de tentativas (${entry.attempts.length})` }),
        el('div', {}, ...entry.attempts.map((t) => el('p', {
          class: t.status === 'failed' ? 'alert-box err' : 'muted',
          text: `${t.at} · ${t.provider} · ${t.status}${t.error ? ' — ' + t.error : ''}`,
        }))),
      ));
    }
    const applyBox = el('div', { class: 'md-apply-box' });
    body.append(applyBox);
    dialogState.applyBox = applyBox;
  }

  async function refreshDialog() {
    const st = dialogState;
    if (!st) return;
    const lib = await api('/api/works/media-library?id=' + encodeURIComponent(currentWork.id));
    mediaOverview = lib;
    st.lib = lib;
    st.entry = (lib.mediaLibrary || {}).requests.find((r) => r.request.id === (st.entry ? st.entry.request.id : '')) || st.entry;
    renderDialogBody();
    renderMediaPanel();
  }

  async function saveRequestFromDialog() {
    const st = dialogState;
    const prompt = st.body.querySelector('.md-req-prompt').value.trim();
    const purpose = st.body.querySelector('.md-req-purpose').value.trim();
    const framing = st.body.querySelector('.md-req-framing').value.trim();
    const profileId = st.body.querySelector('.md-req-profile').value;
    const anchorId = st.body.querySelector('.md-req-anchor').value;
    const sendAnchorToProvider = st.body.querySelector('.md-req-send-anchor').checked;
    let data;
    if (st.entry) {
      data = await post('/api/works/media/request/update', {
        workId: currentWork.id,
        requestId: st.entry.request.id,
        prompt, purpose, framing, profileId, anchorId, sendAnchorToProvider,
        expectedLibraryFingerprint: st.lib.libraryFingerprint,
      });
    } else {
      data = await post('/api/works/media/request/create', {
        workId: currentWork.id,
        targetKind: st.targetKind, targetId: st.targetId,
        prompt, purpose, framing, profileId, anchorId, sendAnchorToProvider,
        expectedLibraryFingerprint: st.lib.libraryFingerprint,
      });
    }
    st.lib = data.overview;
    mediaOverview = data.overview;
    st.entry = (data.overview.mediaLibrary || {}).requests.find((r) => r.request.id === data.requestId);
    renderDialogBody();
    renderMediaPanel();
    toast('Pedido visual salvo.');
  }

  async function copyProviderText() {
    const st = dialogState;
    const text = st.entry.providerTextPreview || st.entry.request.prompt;
    try {
      await navigator.clipboard.writeText(text);
      toast('Pedido copiado. Gere na ferramenta autorizada e importe o arquivo resultante.');
    } catch {
      toast('Não foi possível copiar automaticamente; selecione o texto exibido.');
    }
  }

  function readFileBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || '');
        const idx = result.indexOf(',');
        resolve(idx >= 0 ? result.slice(idx + 1) : result);
      };
      reader.onerror = () => reject(new Error('Falha ao ler o arquivo selecionado.'));
      reader.readAsDataURL(file);
    });
  }

  async function importCandidate(fileInput) {
    const st = dialogState;
    const file = fileInput.files && fileInput.files[0];
    if (!file) { throw new Error('Escolha o arquivo de imagem resultante antes de importar.'); }
    const dataBase64 = await readFileBase64(file);
    const data = await post('/api/works/media/import', {
      workId: currentWork.id,
      requestId: st.entry.request.id,
      dataBase64, fileName: file.name,
      origin: 'imported-manual',
      license: 'pending',
      expectedLibraryFingerprint: st.lib.libraryFingerprint,
    });
    st.lib = data.overview;
    mediaOverview = data.overview;
    await refreshDialog();
    toast('Opção importada como candidato do pedido.');
  }

  async function generateCandidate(provider) {
    const st = dialogState;
    const preview = st.entry.providerTextPreview || st.entry.request.prompt;
    const anchorNote = st.entry.request.anchor && st.entry.request.anchor.sendToProvider
      ? `\nReferência visual ${st.entry.request.anchor.anchorId} (versão ${st.entry.request.anchor.versionId}) será enviada junto.`
      : '\nNenhuma referência será enviada ao provedor.';
    if (!window.confirm(`Confirmar UMA chamada ao provedor "${provider}" com o material abaixo?\n\n${preview}${anchorNote}`)) return;
    const data = await post('/api/works/media/generate', {
      workId: currentWork.id,
      requestId: st.entry.request.id,
      provider, confirm: true,
      expectedLibraryFingerprint: st.lib.libraryFingerprint,
    });
    st.lib = data.overview;
    mediaOverview = data.overview;
    await refreshDialog();
    toast(`Candidato gerado (${provider}). Compare e selecione uma versão.`);
  }

  async function selectCandidate(reqEntry, cand) {
    const st = dialogState;
    const data = await post('/api/works/media/select', {
      workId: currentWork.id,
      assetId: cand.assetId, versionId: cand.versionId,
      requestId: reqEntry.request.id, candidateId: cand.candidateId,
      expectedLibraryFingerprint: (st ? st.lib : mediaOverview).libraryFingerprint,
    });
    mediaOverview = data.overview;
    if (st) st.lib = data.overview;
    const viaPlanning = (data.targets || []).some((t) => t.viaPlanning);
    if (viaPlanning) {
      if (!dialogState) {
        await openRequest(reqEntry.request.target.kind, reqEntry.request.target.id, reqEntry.request.id);
      }
      await showApplyPreview(reqEntry, data);
    } else {
      toast('Versão selecionada e vínculo gravado no rascunho.');
      await openWork(currentWork.id);
      if (window.StudioPlanningBridge) window.StudioPlanningBridge.refresh().catch(() => {});
      await refreshDialog();
    }
  }

  async function showApplyPreview(reqEntry, selectData) {
    const st = dialogState;
    const box = st ? st.applyBox : null;
    const diffData = await post('/api/works/planning/diff', { workId: currentWork.id });
    const diff = diffData.editorsDiff;
    const isVideo = reqEntry.request.target.kind === 'video_scene';
    const section = isVideo ? diff.video : diff.carousel;
    const changes = isVideo ? (section.sceneChanges || []) : (section.cardChanges || []);
    const summary = changes.filter((c) => c.action !== 'unchanged').map((c) => `${c.sceneId || c.cardId}: ${c.action}`).join(', ') || 'nenhuma mudança detectada';
    const applyPayload = {
      workId: currentWork.id,
    };
    const planning = st ? st.planning : null;
    if (isVideo) {
      applyPayload.applyVideo = true;
      applyPayload.preserveCardIds = ((planning || {}).planning || { creative: {} }).creative.carouselCards?.map((c) => c.id) || [];
    } else {
      applyPayload.applyCarousel = true;
      applyPayload.preserveSceneIds = ((planning || {}).planning || { creative: {} }).creative.videoScenes?.map((s) => s.id) || [];
    }
    const content = el('div', { class: 'alert-box warn' },
      el('p', { text: `Prévia de diferenças (${isVideo ? 'Vídeo' : 'Carrossel'}): ${summary}` }),
      el('p', { class: 'muted', text: 'A seleção será gravada no rascunho pelos campos atuais (mediaId + media). Apenas a peça afetada pedirá nova revisão.' }),
      el('button', {
        type: 'button', text: 'Confirmar aplicação ao editor',
        onclick: async () => {
          try {
            const applied = await post('/api/works/planning/apply', applyPayload);
            const status = isVideo ? applied.applied.video.status : applied.applied.carousel.status;
            if (status !== 'applied') {
              throw new Error((isVideo ? applied.applied.video.message : applied.applied.carousel.message) || 'Aplicação não concluída.');
            }
            toast('Versão aplicada ao editor pela prévia de diferenças.');
            await openWork(currentWork.id);
            if (window.StudioPlanningBridge) window.StudioPlanningBridge.refresh().catch(() => {});
            await refreshDialog();
          } catch (err) { dialogError(err); }
        },
      }),
    );
    if (box) {
      box.innerHTML = '';
      box.append(content);
      box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  // ---- importacao e cadastro na aba Midias ----

  async function importFromPanel() {
    if (!currentWork) return;
    mdClearError();
    const fileInput = $('#md-import-file');
    const file = fileInput.files && fileInput.files[0];
    if (!file) { mdShowError(new Error('Escolha um arquivo de imagem para importar.')); return; }
    const dataBase64 = await readFileBase64(file);
    const origin = $('#md-import-origin').value;
    const tool = $('#md-import-tool').value.trim();
    const data = await post('/api/works/media/import', {
      workId: currentWork.id,
      dataBase64, fileName: file.name,
      origin,
      assetId: $('#md-import-asset').value || undefined,
      originDetail: tool ? { tool } : undefined,
      license: $('#md-import-license').value.trim() || 'pending',
      expectedLibraryFingerprint: mediaOverview && mediaOverview.libraryFingerprint,
    });
    mediaOverview = data.overview;
    renderMediaPanel();
    fileInput.value = '';
    mdFeedback(`Imagem importada: ${data.assetId} @ ${data.versionId} (origem: ${originLabel(origin)}).`);
  }

  async function registerFromPanel() {
    if (!currentWork) return;
    mdClearError();
    const path = $('#md-register-select').value;
    if (!path) { mdShowError(new Error('Nenhum arquivo pendente de cadastro na pasta de mídia.')); return; }
    const data = await post('/api/works/media/register', {
      workId: currentWork.id, path,
      origin: 'studio-work', license: 'pending',
      expectedLibraryFingerprint: mediaOverview && mediaOverview.libraryFingerprint,
    });
    mediaOverview = data.overview;
    renderMediaPanel();
    mdFeedback(`Arquivo cadastrado sem cópia: ${data.assetId} @ ${data.versionId}.`);
  }

  async function saveAnchorFromPanel() {
    if (!currentWork) return;
    mdClearError();
    const splitList = (text) => text.split(';').map((t) => t.trim()).filter(Boolean);
    const data = await post('/api/works/media/anchor', {
      workId: currentWork.id,
      title: $('#md-anchor-title').value.trim(),
      assetId: $('#md-anchor-asset').value,
      versionId: $('#md-anchor-version').value,
      direction: $('#md-anchor-direction').value.trim(),
      mustInclude: splitList($('#md-anchor-include').value),
      mustAvoid: splitList($('#md-anchor-avoid').value),
      expectedLibraryFingerprint: mediaOverview && mediaOverview.libraryFingerprint,
    });
    mediaOverview = data.overview;
    renderMediaPanel();
    mdFeedback(`Referência visual salva: ${data.anchorId}. Use-a nos pedidos visuais das cenas e cards.`);
  }

  // ---- clipes por API (texto para video, Gemini Omni Flash) ----

  let videoData = null;
  let videoLoadSeq = 0;
  let videoPollTimer = null;

  function stopVideoPoll() {
    if (videoPollTimer) { clearTimeout(videoPollTimer); videoPollTimer = null; }
  }

  function scheduleVideoPoll() {
    stopVideoPoll();
    const anyProcessing = ((videoData && videoData.requests) || []).some((r) => r.status === 'processing');
    const panel = $('#mode-media');
    if (!anyProcessing || !panel || panel.hidden) return;
    videoPollTimer = setTimeout(() => { loadVideoRequests().catch(() => {}); }, 3000);
  }

  async function loadVideoRequests() {
    const seq = ++videoLoadSeq;
    if (!currentWork) { videoData = null; renderVideoPanel(); return null; }
    const data = await api('/api/works/video-requests?id=' + encodeURIComponent(currentWork.id));
    if (seq === videoLoadSeq) {
      videoData = data;
      renderVideoPanel();
      scheduleVideoPoll();
    }
    return data;
  }

  function videoStatusBadge(status) {
    const labels = (videoData && videoData.options && videoData.options.statusLabels) || {};
    const cls = status === 'ready' || status === 'imported' ? 'ok'
      : status === 'failed' ? 'err'
      : status === 'processing' ? 'ok' : 'warn';
    return el('span', { class: 'badge ' + cls, text: labels[status] || status });
  }

  function renderVideoPanel() {
    const connBox = $('#md-video-conn');
    const listBox = $('#md-video-requests');
    if (!connBox || !listBox) return;
    connBox.innerHTML = '';
    listBox.innerHTML = '';
    if (!currentWork) return;
    const conn = videoData && videoData.videoConnection;
    if (conn) {
      connBox.append(el('span', {
        class: 'badge ok',
        text: `Conexão de vídeo: ${conn.connectionName} (${conn.connectionId}) · modelo ${conn.model}`,
      }));
    } else {
      connBox.append(el('span', {
        class: 'badge warn',
        text: 'Nenhuma conexão de vídeo selecionada para o projeto — configure na aba Conexões (a mesma conexão Google pode atender imagem e vídeo).',
      }));
    }
    const requests = (videoData && videoData.requests) || [];
    if (!requests.length) {
      listBox.append(el('p', { class: 'muted', text: 'Nenhum pedido de clipe ainda. Use "Gerar clipe" para descrever o vídeo e confirmar o envio ao fornecedor.' }));
      return;
    }
    for (const r of requests) {
      const card = el('div', { class: 'media-card', 'data-video-request-id': r.id, style: 'margin-bottom:10px;' });
      const lastAttempt = (r.attempts || [])[r.attempts.length - 1] || null;
      card.append(...[
        el('div', { class: 'row', style: 'justify-content: space-between; align-items:center;' }, [
          el('strong', { text: r.id }),
          videoStatusBadge(r.status),
        ]),
        el('div', { class: 'muted', text: `${r.model} · conexão ${r.connectionName || r.connectionId} · ${r.params.durationSeconds}s · ${r.params.aspectRatio} · ${r.params.resolution}` }),
        el('div', { text: r.prompt.length > 220 ? r.prompt.slice(0, 220) + '…' : r.prompt }),
        r.remoteInteractionId ? el('div', { class: 'muted', text: `ID remoto: ${r.remoteInteractionId}${r.remoteFileId ? ' · arquivo ' + r.remoteFileId : ''}` }) : null,
        lastAttempt && lastAttempt.error ? el('div', { class: 'alert-box ' + (r.status === 'failed' ? 'err' : 'warn'), text: `${lastAttempt.code || ''} ${lastAttempt.error}`.trim() }) : null,
        r.status === 'imported' && r.imported ? el('div', { class: 'muted', text: `Biblioteca: mídia ${r.imported.assetId} · versão ${r.imported.versionId} (selecione na cena pela aba Vídeos)` }) : null,
        r.status === 'ready' && r.result ? el('div', { class: 'muted', text: `Resultado recebido: ${(r.result.bytes / (1024 * 1024)).toFixed(2)} MiB · SHA-256 ${r.result.sha256.slice(0, 16)}…` }) : null,
      ].filter(Boolean));
      const actions = el('div', { class: 'row', style: 'margin-top:6px;' });
      if (r.status === 'awaiting') {
        actions.append(el('button', { text: 'Confirmar envio', onclick: () => openVideoConfirmDialog(r, false).catch(mdShowError) }));
      }
      if (r.status === 'processing' || (r.status === 'uncertain' && r.remoteInteractionId)) {
        actions.append(el('button', {
          class: 'secondary', text: 'Acompanhar',
          onclick: async () => {
            try {
              await post('/api/works/video-requests/check', { workId: currentWork.id, requestId: r.id });
              await loadVideoRequests();
            } catch (e) { mdShowError(e); }
          },
        }));
      }
      if (r.status === 'ready') {
        actions.append(el('button', {
          text: 'Importar na Biblioteca',
          onclick: async () => {
            try {
              const data = await post('/api/works/video-requests/import', { workId: currentWork.id, requestId: r.id });
              if (data.overview) { mediaOverview = data.overview; renderMediaPanel(); }
              await loadVideoRequests();
              mdFeedback(data.deduplicated
                ? `Clipe já importado: mesma versão ${data.versionId} recuperada.`
                : `Clipe importado sem áudio: mídia ${data.assetId}, versão ${data.versionId}. Disponível para seleção nas cenas.`);
            } catch (e) { mdShowError(e); }
          },
        }));
      }
      if (r.status === 'failed' || r.status === 'uncertain') {
        actions.append(el('button', { class: 'warn-btn', text: 'Reenviar (nova submissão)', onclick: () => openVideoConfirmDialog(r, true).catch(mdShowError) }));
      }
      card.append(actions);
      listBox.append(card);
    }
  }

  function closeVideoDialog() {
    const root = $('#media-dialog-root');
    if (root) root.innerHTML = '';
  }

  function videoNoticeBoxes(notices) {
    return [
      el('div', { class: 'alert-box warn', text: notices.retention }),
      el('div', { class: 'alert-box warn', text: notices.billing }),
      el('div', { class: 'alert-box ok', text: notices.audio }),
    ];
  }

  async function openVideoGenerateDialog() {
    if (!currentWork) { toast('Abra um trabalho primeiro.'); return; }
    if (!videoData) await loadVideoRequests();
    const opts = (videoData && videoData.options) || null;
    if (!opts) { mdShowError(new Error('não foi possível carregar as opções de geração')); return; }
    const conn = videoData.videoConnection;
    const root = $('#media-dialog-root');
    root.innerHTML = '';
    const overlay = el('div', { class: 'media-dialog-overlay' });
    const dialog = el('div', { class: 'media-dialog', id: 'md-video-dialog' });
    const promptInput = el('textarea', { rows: 5, placeholder: 'Descreva o clipe: cena, movimento de câmera, luz e clima (uma cena contínua funciona melhor).' });
    const durationSel = el('select', {}, ...opts.durations.map((d) => el('option', { value: String(d), text: `${d} segundos`, selected: d === opts.durationDefault })));
    const aspectSel = el('select', {}, ...opts.aspectRatios.map((a) => el('option', { value: a, text: a, selected: a === opts.aspectDefault })));
    const resolutionSel = el('select', {}, ...opts.resolutions.map((r) => el('option', { value: r, text: r, selected: r === opts.resolutionDefault })));
    const modelInput = el('input', { type: 'text', value: (conn && conn.model) || opts.model, placeholder: opts.model });
    const fb = el('div', {});
    dialog.append(
      el('div', { class: 'row', style: 'justify-content: space-between;' }, [
        el('h3', { text: 'Gerar clipe por API — texto para vídeo', style: 'margin:0;' }),
        el('button', { class: 'secondary', text: 'Fechar', onclick: closeVideoDialog }),
      ]),
      conn
        ? el('p', { class: 'muted', text: `Conexão do projeto: ${conn.connectionName} (${conn.connectionId}). A chave é resolvida no backend no momento da chamada.` })
        : el('div', { class: 'alert-box err', text: 'Nenhuma conexão de vídeo selecionada para este projeto. Configure na aba Conexões antes de gerar.' }),
      el('label', {}, ['Descrição do clipe', promptInput]),
      el('div', { class: 'row' }, [
        el('label', {}, ['Duração', durationSel]),
        el('label', {}, ['Proporção', aspectSel]),
        el('label', {}, ['Resolução', resolutionSel]),
      ]),
      el('label', {}, ['Modelo', modelInput]),
      fb,
      el('button', {
        id: 'md-video-review-btn',
        text: 'Revisar e confirmar envio',
        disabled: !conn,
        onclick: async () => {
          fb.innerHTML = '';
          try {
            const data = await post('/api/works/video-requests/create', {
              workId: currentWork.id,
              prompt: promptInput.value,
              durationSeconds: Number(durationSel.value),
              aspectRatio: aspectSel.value,
              resolution: resolutionSel.value,
              model: modelInput.value.trim() || undefined,
            });
            closeVideoDialog();
            await loadVideoRequests();
            showVideoConfirm(data.request, data.confirmation, false);
          } catch (e) {
            fb.append(el('div', { class: 'alert-box err', text: e.message }));
          }
        },
      }),
    );
    overlay.append(dialog);
    overlay.addEventListener('click', (ev) => { if (ev.target === overlay) closeVideoDialog(); });
    root.append(overlay);
  }

  async function openVideoConfirmDialog(request, resubmit) {
    if (!videoData) await loadVideoRequests();
    const notices = (videoData && videoData.options && videoData.options.notices) || {};
    const confirmation = {
      connectionId: request.connectionId,
      connectionName: request.connectionName,
      model: request.model,
      prompt: request.prompt,
      params: request.params,
      notices,
    };
    showVideoConfirm(request, confirmation, resubmit);
  }

  function showVideoConfirm(request, confirmation, resubmit) {
    const root = $('#media-dialog-root');
    root.innerHTML = '';
    const overlay = el('div', { class: 'media-dialog-overlay' });
    const dialog = el('div', { class: 'media-dialog', id: 'md-video-confirm-dialog' });
    const fb = el('div', {});
    const params = confirmation.params || {};
    dialog.append(...[
      el('div', { class: 'row', style: 'justify-content: space-between;' }, [
        el('h3', { text: resubmit ? 'Confirmar NOVA submissão ao fornecedor' : 'Confirmar envio ao fornecedor', style: 'margin:0;' }),
        el('button', { class: 'secondary', text: 'Fechar', onclick: closeVideoDialog }),
      ]),
      resubmit ? el('div', { class: 'alert-box warn', text: 'O pedido anterior falhou ou ficou incerto. Reenviar cria uma nova tentativa e pode gerar nova cobrança; o histórico anterior é preservado.' }) : null,
      el('p', {}, [
        el('strong', { text: 'Conexão: ' }), el('span', { text: `${confirmation.connectionName} (${confirmation.connectionId})` }),
      ]),
      el('p', {}, [el('strong', { text: 'Modelo: ' }), el('span', { text: confirmation.model })]),
      el('p', {}, [el('strong', { text: 'Parâmetros: ' }), el('span', { text: `${params.durationSeconds}s · ${params.aspectRatio} · ${params.resolution}` })]),
      el('p', { class: 'muted', text: 'Texto que será enviado:' }),
      el('div', { class: 'alert-box ok', text: confirmation.prompt }),
      ...videoNoticeBoxes(confirmation.notices || {}),
      fb,
      el('button', {
        id: 'md-video-confirm-btn',
        text: resubmit ? 'Reenviar ao Google' : 'Confirmar envio ao Google',
        onclick: async () => {
          fb.innerHTML = '';
          try {
            const body = { workId: currentWork.id, requestId: request.id, confirm: true };
            if (resubmit) body.resubmit = true;
            const data = await post('/api/works/video-requests/submit', body);
            closeVideoDialog();
            await loadVideoRequests();
            mdFeedback(data.deduplicated
              ? `Pedido ${request.id} já estava em andamento; nenhuma nova submissão foi feita.`
              : `Pedido ${request.id} enviado ao fornecedor. Acompanhe o processamento abaixo.`);
          } catch (e) {
            fb.append(el('div', { class: 'alert-box err', text: e.message }));
          }
        },
      }),
    ].filter(Boolean));
    overlay.append(dialog);
    overlay.addEventListener('click', (ev) => { if (ev.target === overlay) closeVideoDialog(); });
    root.append(overlay);
  }

  // ---- hooks globais (mesmo padrao de planning.js) ----

  const _prevSetMode = typeof setMode === 'function' ? setMode : null;
  const _prevApplyOpenedWork = typeof applyOpenedWork === 'function' ? applyOpenedWork : null;

  if (_prevSetMode) {
    setMode = function (mode) {
      if (mode === 'media') {
        _prevSetMode('home');
        for (const m of MODES_ALL) {
          const panel = $('#mode-' + m);
          if (panel) panel.hidden = m !== 'media';
          const btn = $('#mode-' + m + '-btn');
          if (btn) btn.classList.toggle('active', m === 'media');
        }
        renderMediaPanel();
        loadMediaOverview().catch((e) => mdShowError(e));
        loadVideoRequests().catch((e) => mdShowError(e));
        return;
      }
      stopVideoPoll();
      const panel = $('#mode-media');
      if (panel) panel.hidden = true;
      const btn = $('#mode-media-btn');
      if (btn) btn.classList.remove('active');
      _prevSetMode(mode);
    };
  }

  if (_prevApplyOpenedWork) {
    applyOpenedWork = function (data) {
      _prevApplyOpenedWork(data);
      const assetSel = $('#md-import-asset');
      if (assetSel) assetSel.value = '';
      if (data && data.mediaLibrary) {
        mediaOverview = data.mediaLibrary;
        renderMediaPanel();
      }
      videoData = null;
      loadVideoRequests().catch(() => {});
    };
  }

  function initMediaUI() {
    $('#mode-media-btn')?.addEventListener('click', () => setMode('media'));
    $('#md-btn-refresh')?.addEventListener('click', () => loadMediaOverview().catch(mdShowError));
    $('#md-btn-import')?.addEventListener('click', () => importFromPanel().catch(mdShowError));
    $('#md-btn-register')?.addEventListener('click', () => registerFromPanel().catch(mdShowError));
    $('#md-btn-anchor-save')?.addEventListener('click', () => saveAnchorFromPanel().catch(mdShowError));
    $('#md-anchor-asset')?.addEventListener('change', (ev) => fillAnchorVersions(ev.target.value));
    $('#md-btn-video-generate')?.addEventListener('click', () => openVideoGenerateDialog().catch(mdShowError));
    renderMediaPanel();
  }

  window.StudioMedia = {
    openRequest,
    refresh: loadMediaOverview,
    closeDialog,
  };

  initMediaUI();
})();