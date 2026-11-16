import React, { useEffect, useState } from 'react';
import {
  Badge,
  Banner,
  Button,
  Dialog,
  DialogHeader,
  Heading,
  Spinner,
  Stack,
  Text,
  TextInput,
} from '@astryxdesign/core';
import { apiGet, apiPost } from '../api.js';

export function SaveAsTemplateDialog({ workId, isOpen, onClose, onSaved }) {
  const [templates, setTemplates] = useState([]);
  const [name, setName] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [label, setLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setName('');
    setTemplateId('');
    setLabel('');
    setError('');
    setLoading(true);
    apiGet('/api/templates')
      .then((res) => setTemplates(res.templates || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isOpen, workId]);

  async function handleSave(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const res = await apiPost('/api/templates/save', {
        workId,
        name: name.trim(),
        templateId: templateId || undefined,
        label: label.trim() || undefined,
      });
      onSaved?.(res);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      purpose="form"
      width={520}
    >
      <DialogHeader
        title={`Salvar como modelo — ${workId || ''}`}
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      />
      <form onSubmit={handleSave} className="astryx-dialog-body">
        <Text size="sm" color="secondary">
          Captura a versão salva do trabalho: cortes, destinos, enquadramentos, estilo, Motion, ficha editorial e mídias com origem, licença e SHA-256. A revisão é imutável.
        </Text>
        {loading ? (
          <Stack direction="horizontal" gap={2} vAlign="center">
            <Spinner size="sm" />
            <Text size="sm" color="secondary">Carregando modelos existentes…</Text>
          </Stack>
        ) : null}
        <TextInput
          id="tpl-save-name"
          label="Nome do modelo"
          placeholder="Ex.: Agenda semanal"
          value={name}
          onChange={setName}
        />
        <label className="astryx-select-field">
          <span className="astryx-select-label">Modelo existente (opcional)</span>
          <select
            id="tpl-save-target"
            className="astryx-native-select"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
          >
            <option value="">Novo modelo</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.id}) — nova revisão
              </option>
            ))}
          </select>
        </label>
        <TextInput
          id="tpl-save-label"
          label="Rótulo da revisão (opcional)"
          placeholder="Ex.: Revisão inicial"
          value={label}
          onChange={setLabel}
        />
        {error ? <Banner status="error" title="Erro ao salvar modelo" description={error} collapsible={false} /> : null}
        <div className="astryx-actions-row">
          <Button
            id="btn-tpl-save-confirm"
            type="submit"
            variant="primary"
            label={saving ? 'Salvando…' : 'Salvar modelo'}
            isDisabled={saving}
          />
          <Button
            type="button"
            variant="secondary"
            label="Cancelar"
            onClick={onClose}
          />
        </div>
      </form>
    </Dialog>
  );
}

export function DuplicateWorkDialog({ workId, isOpen, onClose, onDuplicated }) {
  const [newId, setNewId] = useState('');
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen || !workId) return;
    setNewId(`${workId}-copia`);
    setName('');
    setError('');
  }, [isOpen, workId]);

  async function handleDuplicate(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const res = await apiPost('/api/works/duplicate', {
        workId,
        newId: newId.trim(),
        name: name.trim() || undefined,
      });
      onDuplicated?.(res);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      purpose="form"
      width={480}
    >
      <DialogHeader
        title={`Duplicar como rascunho — ${workId || ''}`}
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      />
      <form onSubmit={handleDuplicate} className="astryx-dialog-body">
        <Text size="sm" color="secondary">
          Cria um trabalho novo a partir da versão salva, sem exigir modelo permanente. O novo trabalho começa com ficha própria, revisão em aberto e entregas vazias.
        </Text>
        <TextInput
          id="tpl-dup-id"
          label="Novo ID (kebab-case)"
          value={newId}
          onChange={setNewId}
          isRequired
        />
        <TextInput
          id="tpl-dup-name"
          label="Nome do novo trabalho (opcional)"
          value={name}
          onChange={setName}
        />
        {error ? <Banner status="error" title="Erro ao duplicar" description={error} collapsible={false} /> : null}
        <div className="astryx-actions-row">
          <Button
            id="btn-tpl-dup-confirm"
            type="submit"
            variant="primary"
            label={saving ? 'Duplicando…' : 'Duplicar trabalho'}
            isDisabled={saving}
          />
          <Button
            type="button"
            variant="secondary"
            label="Cancelar"
            onClick={onClose}
          />
        </div>
      </form>
    </Dialog>
  );
}

export function TemplateCreateDialog({ isOpen, onClose, onOpenCreatedWork }) {
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState('');
  const [revisionId, setRevisionId] = useState('');
  const [rows, setRows] = useState([{ id: '', name: '', title: '', hook: '', cta: '' }]);
  const [planResult, setPlanResult] = useState(null);
  const [createResults, setCreateResults] = useState(null);
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setPlanResult(null);
    setCreateResults(null);
    setError('');
    setRows([{ id: '', name: '', title: '', hook: '', cta: '' }]);
    setIdempotencyKey(`tpl-ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
    setLoading(true);
    apiGet('/api/templates')
      .then((data) => {
        const list = data.templates || [];
        setTemplates(list);
        if (list.length > 0) {
          const first = list[0];
          const revs = (first.revisions || []).slice().reverse();
          setTemplateId(first.id);
          setRevisionId(revs[0]?.revisionId || '');
        } else {
          setTemplateId('');
          setRevisionId('');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isOpen]);

  const activeTemplate = templates.find((t) => t.id === templateId) || null;
  const revisions = activeTemplate ? (activeTemplate.revisions || []).slice().reverse() : [];

  function handleTemplateChange(nextTplId) {
    setTemplateId(nextTplId);
    const tpl = templates.find((t) => t.id === nextTplId);
    const revs = tpl ? (tpl.revisions || []).slice().reverse() : [];
    setRevisionId(revs[0]?.revisionId || '');
    setPlanResult(null);
    setCreateResults(null);
  }

  function updateRow(index, key, value) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [key]: value } : r)));
    setPlanResult(null);
    setCreateResults(null);
  }

  function addRow() {
    setRows((prev) => [...prev, { id: '', name: '', title: '', hook: '', cta: '' }]);
    setPlanResult(null);
    setCreateResults(null);
  }

  function removeRow(index) {
    setRows((prev) => prev.filter((_, i) => i !== index));
    setPlanResult(null);
    setCreateResults(null);
  }

  async function handlePlan() {
    setError('');
    setCreateResults(null);
    setBusy(true);
    try {
      const res = await apiPost('/api/templates/plan', {
        templateId,
        revisionId,
        rows,
      });
      setPlanResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const plans = planResult?.plans || [];
  const allPlansOk =
    Boolean(planResult) &&
    plans.length > 0 &&
    plans.every((p) => p.ok && !(p.conflicts || []).length && !(p.conditions || []).length);

  async function handleConfirm() {
    setError('');
    setBusy(true);
    try {
      const res = await apiPost('/api/templates/create', {
        templateId,
        revisionId,
        rows,
        idempotencyKey,
      });
      setCreateResults(res.creations || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      purpose="form"
      width={720}
    >
      <DialogHeader
        title="Criar a partir de modelo"
        subtitle="Selecione um modelo, revise as alterações na prévia e confirme a criação."
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      />
      <div className="astryx-dialog-body">
        {loading ? (
          <Stack direction="horizontal" gap={2} vAlign="center">
            <Spinner size="sm" />
            <Text size="sm" color="secondary">Carregando modelos salvos…</Text>
          </Stack>
        ) : !templates.length ? (
          <Banner
            status="warning"
            title="Nenhum modelo salvo"
            description="Nenhum modelo salvo ainda. Use 'Salvar como modelo' em um trabalho da lista."
            collapsible={false}
          />
        ) : (
          <>
            <div className="astryx-form-grid">
              <label className="astryx-select-field">
                <span className="astryx-select-label">Modelo</span>
                <select
                  id="tpl-create-template"
                  className="astryx-native-select"
                  value={templateId}
                  onChange={(e) => handleTemplateChange(e.target.value)}
                >
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.id})
                    </option>
                  ))}
                </select>
              </label>

              <label className="astryx-select-field">
                <span className="astryx-select-label">Revisão</span>
                <select
                  id="tpl-create-revision"
                  className="astryx-native-select"
                  value={revisionId}
                  onChange={(e) => {
                    setRevisionId(e.target.value);
                    setPlanResult(null);
                    setCreateResults(null);
                  }}
                >
                  {revisions.map((rev) => (
                    <option key={rev.revisionId} value={rev.revisionId}>
                      {rev.revisionId} — {rev.label || 'sem rótulo'} ({rev.createdAt || ''})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div id="tpl-create-rows">
              <Stack direction="vertical" gap={3}>
                {rows.map((row, idx) => (
                  <div key={idx} className="astryx-variation-card" data-tpl-row={String(idx)}>
                    <div className="astryx-section-head">
                      <Heading level={4}>Variação {idx + 1}</Heading>
                      {rows.length > 1 ? (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          label="Remover linha"
                          onClick={() => removeRow(idx)}
                        />
                      ) : null}
                    </div>
                    <div className="astryx-form-grid">
                      <TextInput
                        label="Novo ID (kebab-case)"
                        placeholder="ex.: agenda-semana-42"
                        value={row.id}
                        onChange={(v) => updateRow(idx, 'id', v)}
                      />
                      <TextInput
                        label="Nome do trabalho"
                        placeholder="herda do modelo"
                        value={row.name}
                        onChange={(v) => updateRow(idx, 'name', v)}
                      />
                      <TextInput
                        label="Título da peça"
                        placeholder="herda do modelo"
                        value={row.title}
                        onChange={(v) => updateRow(idx, 'title', v)}
                      />
                      <TextInput
                        label="Gancho da ficha"
                        placeholder="herda do modelo"
                        value={row.hook}
                        onChange={(v) => updateRow(idx, 'hook', v)}
                      />
                      <TextInput
                        label="CTA da ficha"
                        placeholder="herda do modelo"
                        value={row.cta}
                        onChange={(v) => updateRow(idx, 'cta', v)}
                      />
                    </div>
                  </div>
                ))}
              </Stack>
            </div>

            <div className="astryx-actions-row">
              <Button
                type="button"
                variant="secondary"
                label="+ Adicionar variação"
                onClick={addRow}
                isDisabled={busy}
              />
              <Button
                id="btn-tpl-create-plan"
                type="button"
                variant="secondary"
                label={busy ? 'Calculando prévia…' : 'Prévia do plano'}
                onClick={handlePlan}
                isDisabled={busy}
              />
              <Button
                id="btn-tpl-create-confirm"
                type="button"
                variant="primary"
                label="Confirmar criação"
                onClick={handleConfirm}
                isDisabled={busy || !allPlansOk}
              />
              <Button
                type="button"
                variant="secondary"
                label="Fechar"
                onClick={onClose}
              />
            </div>

            {error ? (
              <Banner status="error" title="Falha na operação de modelo" description={error} collapsible={false} />
            ) : null}

            {planResult ? (
              <div id="tpl-create-plan">
                <Stack direction="vertical" gap={2}>
                  {(planResult.profileAdjustments || []).length > 0 ? (
                    <Banner
                      status="warning"
                      title="Perfis que exigem ajuste"
                      description={planResult.profileAdjustments
                        .map((a) => `${a.profileId} (${a.modality}): ${a.reason}`)
                        .join('; ')}
                      collapsible={false}
                    />
                  ) : null}
                  {plans.map((plan) => {
                    const changes = plan.changes || {};
                    const summary = Object.entries(changes)
                      .map(([k, c]) => {
                        const val = c.effective ?? '';
                        return c.changed ? `${k}: "${c.inherited ?? ''}" → "${val}"` : `${k}: herdado ("${val}")`;
                      })
                      .join(' · ');
                    const issues = [...(plan.conflicts || []), ...(plan.conditions || [])];
                    return (
                      <div
                        key={plan.row}
                        className="astryx-variation-card"
                        data-tpl-plan-row={String(plan.row)}
                      >
                        <div className="astryx-actions-row">
                          <Badge
                            variant={plan.ok && !issues.length ? 'success' : 'error'}
                            label={plan.ok && !issues.length ? 'pronta' : 'bloqueada'}
                          />
                          <Text weight="semibold">{plan.id || '(sem id)'}</Text>
                        </div>
                        {summary ? (
                          <Text size="sm" color="secondary">{summary}</Text>
                        ) : null}
                        {issues.map((c, idx) => (
                          <Banner
                            key={idx}
                            status="error"
                            title={c.code}
                            description={c.message}
                            collapsible={false}
                          />
                        ))}
                      </div>
                    );
                  })}
                </Stack>
              </div>
            ) : null}

            {createResults ? (
              <div id="tpl-create-results">
                <Stack direction="vertical" gap={2}>
                  {createResults.map((c) => (
                    <div
                      key={c.row}
                      className="astryx-variation-card"
                      data-tpl-result-row={String(c.row)}
                    >
                      <div className="astryx-section-head">
                        <div className="astryx-actions-row">
                          <Badge
                            variant={c.status === 'created' ? 'success' : 'error'}
                            label={c.status === 'created' ? 'criado' : 'falhou'}
                          />
                          <Text weight="semibold">
                            {c.id || '(sem id)'} {c.name ? `— ${c.name}` : ''}
                          </Text>
                        </div>
                        {c.status === 'created' ? (
                          <Button
                            type="button"
                            variant="primary"
                            size="sm"
                            label="Abrir trabalho"
                            onClick={() => {
                              onClose();
                              onOpenCreatedWork?.(c.id);
                            }}
                          />
                        ) : null}
                      </div>
                      {c.status !== 'created' && c.error ? (
                        <Banner status="error" title="Erro ao criar variação" description={c.error} collapsible={false} />
                      ) : null}
                    </div>
                  ))}
                </Stack>
              </div>
            ) : null}
          </>
        )}
      </div>
    </Dialog>
  );
}
