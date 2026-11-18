import React, { useEffect, useRef, useState } from 'react';
import {
  Badge,
  Banner,
  Button,
  Card,
  Heading,
  Spinner,
  Stack,
  Text,
} from '@astryxdesign/core';
import { apiGet, apiPost, getStudioBridge } from '../api.js';

function reviewStatusVariant(status, readyForPackage) {
  if (readyForPackage || status === 'approved') return 'success';
  if (status === 'changes_requested' || status === 'unavailable') return 'error';
  if (
    status === 'draft_outdated' ||
    status === 'copy_outdated' ||
    status === 'unlinked' ||
    status === 'reexported_pending' ||
    status === 'pending_review'
  ) {
    return 'warning';
  }
  return 'neutral';
}

function buildInitialSelection(review) {
  const next = {};
  for (const p of review?.pieces || []) {
    next[`piece:${p.modality}:${p.profileId}`] = Boolean(p.readyForPackage);
  }
  for (const ch of review?.channels || []) {
    next[`channel:${ch.profileId}`] = Boolean(ch.readyForPackage);
  }
  return next;
}

function readInitialSnapshot() {
  if (typeof window !== 'undefined' && window.__studioReviewPackageState) {
    return window.__studioReviewPackageState;
  }
  return { workId: null, review: null, packageDelivery: null };
}

export function ReviewPackagePanel() {
  const [snapshot, setSnapshot] = useState(readInitialSnapshot);
  const [selectedMap, setSelectedMap] = useState(() =>
    buildInitialSelection(readInitialSnapshot().review),
  );
  const [submitting, setSubmitting] = useState(false);
  const [statusNotice, setStatusNotice] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  const activeWorkIdRef = useRef(snapshot.workId || null);
  const requestSeqRef = useRef(0);
  const inFlightRef = useRef(false);
  const prevReadyRef = useRef({});
  const pkgIdRef = useRef(snapshot.packageDelivery?.lastValidDelivery?.packageId || null);
  const verifySeqRef = useRef(0);
  const verifyInFlightRef = useRef(false);

  useEffect(() => {
    function handleSync(event) {
      const detail = event?.detail || { workId: null, review: null, packageDelivery: null };
      const prevWorkId = activeWorkIdRef.current;
      const nextWorkId = detail.workId || null;
      const workChanged = prevWorkId !== nextWorkId;

      const nextPkgId = detail.packageDelivery?.lastValidDelivery?.packageId || null;
      const pkgChanged = nextPkgId !== pkgIdRef.current;
      activeWorkIdRef.current = nextWorkId;
      setSnapshot(detail);
      pkgIdRef.current = nextPkgId;

      if (workChanged) {
        requestSeqRef.current += 1;
        verifySeqRef.current += 1;
        inFlightRef.current = false;
        verifyInFlightRef.current = false;
        setSubmitting(false);
        setVerifying(false);
        setStatusNotice(null);
        setVerifyResult(null);
        const nextMap = buildInitialSelection(detail.review);
        prevReadyRef.current = { ...nextMap };
        setSelectedMap(nextMap);
        return;
      }

      // Novo pacote no mesmo trabalho (atualizacao externa) invalida a verificacao anterior.
      if (pkgChanged) {
        verifySeqRef.current += 1;
        verifyInFlightRef.current = false;
        setVerifying(false);
        setVerifyResult(null);
      }

      const nextReady = buildInitialSelection(detail.review);
      const prevReadySnapshot = prevReadyRef.current;
      prevReadyRef.current = { ...nextReady };
      setSelectedMap((prev) => {
        const merged = {};
        for (const [key, ready] of Object.entries(nextReady)) {
          const hadPrev = Object.prototype.hasOwnProperty.call(prev, key);
          const readyChanged = prevReadySnapshot[key] !== ready;
          merged[key] = !hadPrev || readyChanged ? ready : prev[key];
        }
        return merged;
      });
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('studio:review-package-sync', handleSync);
      if (window.__studioReviewPackageState) {
        handleSync({ detail: window.__studioReviewPackageState });
      }
      return () => window.removeEventListener('studio:review-package-sync', handleSync);
    }
    return undefined;
  }, []);

  const workId = snapshot.workId || null;
  const review = snapshot.review || null;
  const pkg = snapshot.packageDelivery || null;
  const pieces = review?.pieces || [];
  const channels = review?.channels || [];

  function toggleItem(key, checked) {
    setSelectedMap((prev) => ({
      ...prev,
      [key]: checked,
    }));
  }

  async function handleBuildPackage() {
    if (!workId || inFlightRef.current) return;

    const reqWorkId = workId;
    const reqSeq = ++requestSeqRef.current;
    inFlightRef.current = true;
    setSubmitting(true);
    setStatusNotice(null);

    const selectedPieces = pieces
      .filter((p) => Boolean(selectedMap[`piece:${p.modality}:${p.profileId}`]))
      .map((p) => ({
        modality: p.modality,
        profileId: p.profileId,
        expectedVersionId: p.deliveryVersionId || null,
        expectedDraftFingerprint: p.currentDraftFingerprint || null,
      }));

    const selectedChannels = channels
      .filter((ch) => Boolean(selectedMap[`channel:${ch.profileId}`]))
      .map((ch) => ({
        profileId: ch.profileId,
        expectedCopySha256: ch.copySha256 || null,
      }));

    try {
      const data = await apiPost('/api/works/package', {
        workId: reqWorkId,
        pieces: selectedPieces,
        channels: selectedChannels,
      });
      if (activeWorkIdRef.current !== reqWorkId || requestSeqRef.current !== reqSeq) {
        return;
      }
      setVerifyResult(null);
      setStatusNotice({
        status: 'success',
        title: 'Pacote ZIP gerado',
        description: 'Pacote ZIP de entrega gerado, validado e promovido atomicamente.',
      });
      getStudioBridge()?.applyReviewPackageResult?.(reqWorkId, data);
      getStudioBridge()?.toast?.('Pacote ZIP de entrega pronto para download.');
    } catch (err) {
      if (activeWorkIdRef.current !== reqWorkId || requestSeqRef.current !== reqSeq) {
        return;
      }
      const isConflict = err?.status === 409;
      setStatusNotice({
        status: 'error',
        title: isConflict ? 'Conflito de versão (HTTP 409)' : 'Empacotamento bloqueado',
        description: err?.message || 'Falha ao gerar ZIP.',
      });
      await getStudioBridge()?.refreshReviewOverview?.(reqWorkId)?.catch?.(() => {});
      getStudioBridge()?.toast?.(err?.message || 'Falha ao gerar ZIP');
    } finally {
      if (activeWorkIdRef.current === reqWorkId && requestSeqRef.current === reqSeq) {
        inFlightRef.current = false;
        setSubmitting(false);
      }
    }
  }

  async function handleVerifyPackage() {
    if (!workId || !pkg?.available || verifyInFlightRef.current) return;

    const reqWorkId = workId;
    const reqPackageId = pkg?.lastValidDelivery?.packageId || null;
    const reqSeq = ++verifySeqRef.current;
    verifyInFlightRef.current = true;
    setVerifying(true);
    setVerifyResult(null);

    try {
      const data = await apiGet(`/api/works/package/verify?id=${encodeURIComponent(reqWorkId)}`);
      if (activeWorkIdRef.current !== reqWorkId || verifySeqRef.current !== reqSeq) {
        return;
      }
      if (pkgIdRef.current !== reqPackageId) {
        return;
      }
      setVerifyResult(data.verification || data);
    } catch (err) {
      if (activeWorkIdRef.current !== reqWorkId || verifySeqRef.current !== reqSeq) {
        return;
      }
      if (pkgIdRef.current !== reqPackageId) {
        return;
      }
      setVerifyResult({
        ok: false,
        summary: err?.message || 'Falha ao verificar pacote ZIP.',
        errors: [{ message: err?.message || 'Falha ao verificar pacote ZIP.' }],
      });
    } finally {
      if (activeWorkIdRef.current === reqWorkId && verifySeqRef.current === reqSeq) {
        verifyInFlightRef.current = false;
        setVerifying(false);
      }
    }
  }

  return (
    <div className="astryx-review-package-pilot" data-testid="astryx-review-package-pilot">
      <Card id="r-package-section" padding={4}>
        <Stack direction="vertical" gap={3}>
          <Heading level={2}>4. Montar e baixar pacote ZIP de entrega</Heading>
          <Text size="sm" color="secondary">
            Apenas peças e textos por canal explicitamente aprovados para entrega local são aceitos no ZIP final. Vídeo e Motion do mesmo destino são gravados em pastas separadas.
          </Text>

          <div id="r-package-checklist">
            <Stack direction="vertical" gap={2}>
              {pieces.map((p) => {
                const key = `piece:${p.modality}:${p.profileId}`;
                const checked = Boolean(selectedMap[key]);
                return (
                  <div key={key} className="astryx-checklist-row">
                    <label className="astryx-inline-check">
                      <input
                        type="checkbox"
                        data-pkg-type="piece"
                        data-modality={p.modality}
                        data-profile={p.profileId}
                        data-expected-version={p.deliveryVersionId || ''}
                        data-expected-draft={p.currentDraftFingerprint || ''}
                        checked={checked}
                        disabled={submitting}
                        onChange={(e) => toggleItem(key, e.target.checked)}
                      />
                      <span>
                        [{p.modalityLabel}] {p.profileId}
                      </span>
                    </label>
                    <div className="astryx-checklist-meta">
                      <Badge
                        variant={reviewStatusVariant(p.status, p.readyForPackage)}
                        label={p.readyForPackage ? 'Pronto' : p.statusLabel}
                      />
                      <Text size="sm" color="secondary">
                        {p.readyReason}
                      </Text>
                    </div>
                  </div>
                );
              })}

              {channels.map((ch) => {
                const key = `channel:${ch.profileId}`;
                const checked = Boolean(selectedMap[key]);
                return (
                  <div key={key} className="astryx-checklist-row">
                    <label className="astryx-inline-check">
                      <input
                        type="checkbox"
                        data-pkg-type="channel"
                        data-profile={ch.profileId}
                        data-expected-copy={ch.copySha256 || ''}
                        checked={checked}
                        disabled={submitting}
                        onChange={(e) => toggleItem(key, e.target.checked)}
                      />
                      <span>[Texto de canal] {ch.profileId}</span>
                    </label>
                    <div className="astryx-checklist-meta">
                      <Badge
                        variant={reviewStatusVariant(ch.status, ch.readyForPackage)}
                        label={ch.readyForPackage ? 'Pronto' : ch.statusLabel}
                      />
                      <Text size="sm" color="secondary">
                        {ch.readyReason}
                      </Text>
                    </div>
                  </div>
                );
              })}
            </Stack>
          </div>

          <div className="astryx-actions-row">
            <Button
              id="btn-r-build-package"
              variant="primary"
              label={submitting ? 'Empacotando ZIP…' : 'Gerar ZIP de entrega'}
              onClick={handleBuildPackage}
              isDisabled={submitting || !workId}
            />
            {submitting ? <Spinner size="sm" /> : null}
          </div>

          <div id="r-package-status">
            {submitting ? (
              <Banner
                status="info"
                title="Empacotamento em andamento"
                description="Validando integridade e empacotando ZIP…"
                collapsible={false}
              />
            ) : statusNotice ? (
              <Banner
                status={statusNotice.status}
                title={statusNotice.title}
                description={statusNotice.description}
                collapsible={false}
              />
            ) : null}
          </div>

          <div id="r-package-result">
            <Stack direction="vertical" gap={3}>
              {pkg?.lastAttempt?.status === 'failed' ? (
                <Banner
                  status="error"
                  title="Última tentativa de empacotamento ZIP falhou"
                  description={`${pkg.lastAttempt.error || 'erro'}. O último pacote ZIP válido (quando existente) foi preservado.`}
                  collapsible={false}
                />
              ) : null}

              {pkg?.available && pkg?.lastValidDelivery ? (
                <div className="astryx-variation-card">
                  <div className="astryx-section-head">
                    <Text weight="semibold">
                      Pacote ZIP promovido: {pkg.lastValidDelivery.packageId}
                    </Text>
                    <Badge variant="success" label="ZIP íntegro" />
                  </div>
                  <Text size="sm" color="secondary" className="astryx-package-meta">
                    {pkg.lastValidDelivery.zipBytes} bytes · SHA-256 {pkg.lastValidDelivery.zipSha256} · Modalidades:{' '}
                    {(pkg.lastValidDelivery.modalities || []).join(', ') || 'apenas textos'} · Destinos:{' '}
                    {(pkg.lastValidDelivery.profiles || []).join(', ')}
                  </Text>
                  <a
                    id="btn-r-download-zip"
                    className="astryx-queue-link"
                    href={pkg.downloadUrl}
                    download={`${workId || 'entrega'}-${pkg.lastValidDelivery.packageId}.zip`}
                  >
                    Baixar ZIP de entrega ({pkg.lastValidDelivery.packageId}.zip)
                  </a>
                  <div id="r-package-verify">
                    <div className="astryx-actions-row">
                      <Button
                        id="btn-r-verify-package"
                        variant="secondary"
                        label={verifying ? 'Verificando ZIP…' : 'Verificar pacote ZIP'}
                        onClick={handleVerifyPackage}
                        isDisabled={verifying || !pkg?.available}
                      />
                      {verifying ? <Spinner size="sm" /> : null}
                    </div>
                    {verifyResult ? (
                      <div id="r-package-verify-result" className="astryx-verify-result">
                        <Banner
                          status={verifyResult.ok ? 'success' : 'error'}
                          title={verifyResult.ok ? 'Verificação técnica do pacote ZIP' : 'Pacote ZIP não passou na verificação'}
                          description={verifyResult.summary || (verifyResult.ok ? 'Pacote íntegro.' : 'Falha na verificação.')}
                          collapsible={false}
                        />
                        {verifyResult.ok ? (
                          <Text size="sm" color="secondary">
                            {verifyResult.packageId} · {verifyResult.files?.length || 0} arquivo(s) · peças: {verifyResult.pieces?.length || 0} · canais: {verifyResult.channels?.length || 0}
                          </Text>
                        ) : verifyResult.errors?.[0] ? (
                          <Text size="sm" color="secondary">
                            Primeiro problema: {verifyResult.errors[0].message}
                            {verifyResult.errors[0].file ? ` (${verifyResult.errors[0].file})` : ''}
                          </Text>
                        ) : null}
                        {verifyResult.limitations?.length ? (
                          <Text size="sm" color="secondary">
                            Limitações: {verifyResult.limitations.join(' · ')}
                          </Text>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  <pre className="astryx-package-manifest">
                    {JSON.stringify(pkg.manifest?.files || [], null, 2)}
                  </pre>
                </div>
              ) : pkg?.lastValidDelivery && !pkg?.available ? (
                <Banner
                  status="error"
                  title="Pacote ZIP anterior indisponível"
                  description={pkg.zipError || 'erro de integridade'}
                  collapsible={false}
                />
              ) : (
                <Text size="sm" color="secondary">
                  Nenhum pacote ZIP de entrega gerado ainda neste trabalho.
                </Text>
              )}
            </Stack>
          </div>
        </Stack>
      </Card>
    </div>
  );
}
