import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  Heading,
  Spinner,
  Stack,
  Text,
} from '@astryxdesign/core';
import { apiGet, apiPost, getStudioBridge } from '../api.js';

function getQueueStatusMeta(status) {
  switch (status) {
    case 'queued':
      return { variant: 'neutral', label: 'Na fila' };
    case 'running':
      return { variant: 'info', label: 'Em execução' };
    case 'completed':
      return { variant: 'success', label: 'Concluído' };
    case 'failed':
      return { variant: 'error', label: 'Falhou' };
    case 'interrupted':
      return { variant: 'warning', label: 'Interrompido' };
    case 'cancelled':
      return { variant: 'neutral', label: 'Cancelado' };
    default:
      return { variant: 'neutral', label: status || 'desconhecido' };
  }
}

export function ProductionQueueTab() {
  const [statusFilter, setStatusFilter] = useState('');
  const [workFilter, setWorkFilter] = useState('');
  const [workOptions, setWorkOptions] = useState([]);

  const [counts, setCounts] = useState({});
  const [batches, setBatches] = useState([]);
  const [items, setItems] = useState([]);

  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [busyItemId, setBusyItemId] = useState(null);
  const [retryFeedback, setRetryFeedback] = useState({});

  const requestSeqRef = useRef(0);
  const pollTimerRef = useRef(null);
  const filtersRef = useRef({ statusFilter: '', workFilter: '' });

  useEffect(() => {
    filtersRef.current = { statusFilter, workFilter };
  }, [statusFilter, workFilter]);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const fetchQueue = useCallback(async (nextStatus, nextWork) => {
    const targetStatus = nextStatus !== undefined ? nextStatus : filtersRef.current.statusFilter;
    const targetWork = nextWork !== undefined ? nextWork : filtersRef.current.workFilter;

    clearPollTimer();
    const seq = ++requestSeqRef.current;
    setRefreshing(true);
    setError('');

    try {
      const params = new URLSearchParams();
      if (targetStatus) params.set('status', targetStatus);
      if (targetWork) params.set('workId', targetWork);
      const qs = params.toString() ? `?${params.toString()}` : '';

      const filteredPromise = apiGet(`/api/queue${qs}`);
      const allPromise = qs ? apiGet('/api/queue') : filteredPromise;
      const [data, allData] = await Promise.all([filteredPromise, allPromise]);

      // Descarta respostas atrasadas de filtros/chamadas anteriores
      if (seq !== requestSeqRef.current) return;

      const nextCounts = data.counts || {};
      const pendingCount = (nextCounts.queued || 0) + (nextCounts.running || 0);
      getStudioBridge()?.updateQueueNavBadge?.(pendingCount);

      const seenWorks = new Set();
      for (const it of allData.items || []) {
        if (it.workId) seenWorks.add(it.workId);
      }
      const sortedWorks = Array.from(seenWorks).sort();
      setWorkOptions(sortedWorks);
      if (targetWork && !seenWorks.has(targetWork)) {
        setWorkFilter('');
      }

      setCounts(nextCounts);
      setBatches(data.batches || []);
      setItems(data.items || []);

      if (pendingCount > 0) {
        pollTimerRef.current = setTimeout(() => {
          fetchQueue().catch(() => {});
        }, 1500);
      }
    } catch (err) {
      if (seq !== requestSeqRef.current) return;
      setError(err?.message || 'Não foi possível consultar a fila.');
    } finally {
      if (seq === requestSeqRef.current) {
        setInitialLoading(false);
        setRefreshing(false);
      }
    }
  }, [clearPollTimer]);

  useEffect(() => {
    fetchQueue('', '');
    return () => {
      clearPollTimer();
    };
  }, [fetchQueue, clearPollTimer]);

  useEffect(() => {
    window.__studioAstryxQueueRefresh = () => {
      fetchQueue();
    };
    return () => {
      delete window.__studioAstryxQueueRefresh;
    };
  }, [fetchQueue]);

  function handleStatusChange(nextStatus) {
    setStatusFilter(nextStatus);
    fetchQueue(nextStatus, workFilter);
  }

  function handleWorkChange(nextWork) {
    setWorkFilter(nextWork);
    fetchQueue(statusFilter, nextWork);
  }

  async function handleCancelItem(itemId) {
    setBusyItemId(itemId);
    try {
      await apiPost('/api/queue/cancel', { itemId });
      getStudioBridge()?.toast?.('Item cancelado na fila.');
      await fetchQueue();
    } catch (err) {
      getStudioBridge()?.toast?.(err.message);
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleRetryItem(itemId, useCurrent = false) {
    setBusyItemId(itemId);
    setRetryFeedback((prev) => {
      const next = { ...prev };
      delete next[itemId];
      return next;
    });
    try {
      await apiPost('/api/queue/retry', { itemId, useCurrent });
      getStudioBridge()?.toast?.(
        useCurrent
          ? 'Item reenfileirado com a versão atual.'
          : 'Nova tentativa enfileirada com o snapshot anterior.',
      );
      await fetchQueue();
    } catch (err) {
      if (err?.payload?.canUseCurrent) {
        setRetryFeedback((prev) => ({
          ...prev,
          [itemId]: { message: err.message, canUseCurrent: true },
        }));
      } else {
        getStudioBridge()?.toast?.(err.message);
      }
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleOpenReview(workId) {
    try {
      await getStudioBridge()?.openQueueWorkReview?.(workId);
    } catch (err) {
      getStudioBridge()?.toast?.(err.message);
    }
  }

  const countLabels = [
    ['Total', counts.total || 0],
    ['Na fila', counts.queued || 0],
    ['Em execução', counts.running || 0],
    ['Concluídos', counts.completed || 0],
    ['Falhos', counts.failed || 0],
    ['Interrompidos', counts.interrupted || 0],
    ['Cancelados', counts.cancelled || 0],
  ];

  return (
    <div className="astryx-queue-pilot" data-testid="astryx-queue-pilot">
      {/* 1. Visao geral, contadores e filtros */}
      <Card id="sec-queue-overview" padding={4}>
        <Stack direction="vertical" gap={3}>
          <div className="astryx-section-head">
            <Heading level={2}>Fila de Produção em Lote</Heading>
            <div className="astryx-actions-row">
              {refreshing && !initialLoading ? (
                <Spinner size="sm" />
              ) : null}
              <Button
                id="btn-q-refresh"
                variant="secondary"
                label="Atualizar fila"
                onClick={() => fetchQueue()}
              />
            </div>
          </div>

          <Text size="sm" color="secondary">
            A fila persiste localmente em SQLite e continua executando em série no servidor local mesmo após fechar o navegador.
          </Text>

          <div id="queue-counts-bar" className="astryx-queue-counts">
            {countLabels.map(([label, value]) => (
              <div key={label} className="astryx-queue-count-pill">
                <span style={{ color: 'var(--color-text-secondary, #9aa0a6)' }}>{label}: </span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          <div className="astryx-form-grid">
            <label className="astryx-select-field">
              <span className="astryx-select-label">Filtrar por estado</span>
              <select
                id="q-filter-status"
                className="astryx-native-select"
                value={statusFilter}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                <option value="">Todos os estados</option>
                <option value="queued">Na fila</option>
                <option value="running">Em execução</option>
                <option value="completed">Concluídos</option>
                <option value="failed">Falhos</option>
                <option value="interrupted">Interrompidos</option>
                <option value="cancelled">Cancelados</option>
              </select>
            </label>

            <label className="astryx-select-field">
              <span className="astryx-select-label">Filtrar por trabalho</span>
              <select
                id="q-filter-work"
                className="astryx-native-select"
                value={workFilter}
                onChange={(e) => handleWorkChange(e.target.value)}
              >
                <option value="">Todos os trabalhos</option>
                {workOptions.map((wid) => (
                  <option key={wid} value={wid}>
                    {wid}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error ? (
            <Banner
              status="error"
              title="Erro ao consultar a fila de produção"
              description={error}
              collapsible={false}
              actions={
                <Button
                  variant="secondary"
                  size="sm"
                  label="Tentar novamente"
                  onClick={() => fetchQueue()}
                />
              }
            />
          ) : null}
        </Stack>
      </Card>

      {/* 2. Lotes registrados */}
      <Card id="sec-queue-batches" padding={4}>
        <Stack direction="vertical" gap={3}>
          <Heading level={2}>Lotes registrados</Heading>
          {initialLoading ? (
            <Stack direction="horizontal" gap={2} vAlign="center">
              <Spinner size="sm" />
              <Text size="sm" color="secondary">Carregando lotes da fila…</Text>
            </Stack>
          ) : !batches.length ? (
            <EmptyState
              title="Nenhum lote enfileirado ainda"
              description="Selecione trabalhos em Trabalhos & Projetos e use Exportar em lote para iniciar."
              isCompact
            />
          ) : (
            <div id="q-batches-list">
              <Stack direction="vertical" gap={2}>
                {batches.map((b) => {
                  const bc = b.counts || {};
                  const st = getQueueStatusMeta(b.batchStatus);
                  return (
                    <div key={b.batchId} className="astryx-variation-card" data-batch-id={b.batchId}>
                      <div className="astryx-section-head">
                        <div className="astryx-actions-row">
                          <Text weight="semibold">{b.label || b.batchId}</Text>
                          <Text size="sm" color="secondary">({b.batchId})</Text>
                        </div>
                        <Badge variant={st.variant} label={st.label} />
                      </div>
                      <Text size="sm" color="secondary">
                        Total {bc.total || 0} · Na fila {bc.queued || 0} · Em execução {bc.running || 0} · Concluídos {bc.completed || 0} · Falhos {bc.failed || 0} · Interrompidos {bc.interrupted || 0} · Cancelados {bc.cancelled || 0}
                      </Text>
                      <a
                        className="astryx-queue-link"
                        href={`/api/queue/batch/summary?id=${encodeURIComponent(b.batchId)}`}
                        download={`${b.batchId}-summary.json`}
                      >
                        Baixar resumo JSON do lote
                      </a>
                    </div>
                  );
                })}
              </Stack>
            </div>
          )}
        </Stack>
      </Card>

      {/* 3. Pecas da fila */}
      <Card id="sec-queue-items" padding={4}>
        <Stack direction="vertical" gap={3}>
          <Heading level={2}>Peças da fila</Heading>
          {initialLoading ? (
            <Stack direction="horizontal" gap={2} vAlign="center">
              <Spinner size="sm" />
              <Text size="sm" color="secondary">Carregando peças da fila…</Text>
            </Stack>
          ) : !items.length ? (
            <EmptyState
              title="Nenhuma peça corresponde aos filtros atuais"
              description="Ajuste os filtros acima ou atualize a fila após enfileirar novas peças."
              isCompact
            />
          ) : (
            <div id="q-items-list">
              <Stack direction="vertical" gap={2}>
                {items.map((it) => {
                  const st = getQueueStatusMeta(it.status);
                  const fb = retryFeedback[it.itemId];
                  const isBusy = busyItemId === it.itemId;
                  return (
                    <div
                      key={it.itemId}
                      className="astryx-variation-card"
                      data-queue-item-id={it.itemId}
                    >
                      <div className="astryx-section-head">
                        <div className="astryx-actions-row">
                          <Badge variant="neutral" label={it.modalityLabel || it.modality} />
                          <Text weight="semibold">{it.workTitle}</Text>
                          <Text size="sm" color="secondary">
                            ({it.workId} · {it.profileId})
                          </Text>
                        </div>
                        <Badge variant={st.variant} label={st.label} />
                      </div>

                      <Text size="sm" color="secondary">
                        Lote {it.batchId} · Tentativas: {(it.attempts || []).length}
                        {it.deliveryVersionId ? ` · Entrega: ${it.deliveryVersionId}` : ''}
                      </Text>

                      {it.errorMessage ? (
                        <Banner
                          status={it.status === 'cancelled' ? 'warning' : 'error'}
                          title={it.status === 'cancelled' ? 'Cancelado' : 'Falha na execução'}
                          description={it.errorMessage}
                          collapsible={false}
                        />
                      ) : null}

                      {fb ? (
                        <div className="q-item-retry-feedback">
                          <Banner
                            status="warning"
                            title="Snapshot anterior indisponível"
                            description={fb.message}
                            collapsible={false}
                            endContent={
                              fb.canUseCurrent ? (
                                <Button
                                  className="q-btn-retry-current"
                                  variant="primary"
                                  size="sm"
                                  label="Enfileirar versão atual"
                                  onClick={() => handleRetryItem(it.itemId, true)}
                                  isDisabled={isBusy}
                                />
                              ) : null
                            }
                          />
                        </div>
                      ) : null}

                      <div className="astryx-actions-row">
                        {it.status === 'queued' ? (
                          <Button
                            className="q-btn-cancel"
                            variant="secondary"
                            size="sm"
                            label="Cancelar"
                            onClick={() => handleCancelItem(it.itemId)}
                            isDisabled={isBusy}
                          />
                        ) : null}

                        {it.status === 'failed' || it.status === 'interrupted' ? (
                          <>
                            <Button
                              className="q-btn-retry"
                              variant="secondary"
                              size="sm"
                              label="Tentar novamente"
                              onClick={() => handleRetryItem(it.itemId, false)}
                              isDisabled={isBusy}
                            />
                            {it.canUseCurrent && !(fb && fb.canUseCurrent) ? (
                              <Button
                                className="q-btn-retry-current"
                                variant="primary"
                                size="sm"
                                label="Enfileirar versão atual"
                                onClick={() => handleRetryItem(it.itemId, true)}
                                isDisabled={isBusy}
                              />
                            ) : null}
                          </>
                        ) : null}

                        <Button
                          className="q-btn-open-review"
                          variant="primary"
                          size="sm"
                          label="Abrir revisão"
                          onClick={() => handleOpenReview(it.workId)}
                        />
                      </div>
                    </div>
                  );
                })}
              </Stack>
            </div>
          )}
        </Stack>
      </Card>
    </div>
  );
}
