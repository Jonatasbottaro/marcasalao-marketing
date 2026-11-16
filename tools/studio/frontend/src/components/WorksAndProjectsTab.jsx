import React, { useCallback, useEffect, useState } from 'react';
import {
  Badge,
  Banner,
  Button,
  Card,
  CheckboxInput,
  EmptyState,
  Heading,
  Spinner,
  Stack,
  Table,
  Text,
  TextInput,
  pixel,
  proportional,
} from '@astryxdesign/core';
import { apiGet, apiPost, getStudioBridge } from '../api.js';
import {
  DuplicateWorkDialog,
  SaveAsTemplateDialog,
  TemplateCreateDialog,
} from './TemplateDialogs.jsx';

const DEFAULT_PROJECT_PROFILES = new Set([
  'instagram-reels-video',
  'facebook-reels-video',
  'youtube-shorts',
  'instagram-feed-image-square',
]);

function renderDeliveryStatus(okCount, lastStatus) {
  if (lastStatus === 'failed' && !okCount) {
    return <Badge variant="error" label="falhou" />;
  }
  if (lastStatus === 'failed' && okCount) {
    return (
      <Stack direction="horizontal" gap={1} wrap>
        <Badge variant="success" label="válido" />
        <Badge variant="error" label="tentativa falhou" />
      </Stack>
    );
  }
  if (lastStatus === 'interrupted') {
    return (
      <Stack direction="horizontal" gap={1} wrap>
        {okCount ? <Badge variant="success" label="válido" /> : null}
        <Badge variant="warning" label="interrompida" />
      </Stack>
    );
  }
  if (okCount) {
    return (
      <Badge
        variant="success"
        label={typeof okCount === 'number' ? `${okCount} perfil(is)` : 'pronto'}
      />
    );
  }
  return <Badge variant="neutral" label="sem entrega" />;
}

export function WorksAndProjectsTab() {
  const [works, setWorks] = useState([]);
  const [worksLoading, setWorksLoading] = useState(true);
  const [worksError, setWorksError] = useState('');

  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState('');

  const [profiles, setProfiles] = useState([]);
  const [selectedWorks, setSelectedWorks] = useState(() => new Set());

  // Demonstracao guiada
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState('');

  // Criar novo trabalho
  const [workName, setWorkName] = useState('');
  const [workId, setWorkId] = useState('');
  const [workProject, setWorkProject] = useState('');
  const [workTemplate, setWorkTemplate] = useState('marca-salao');
  const [createWorkBusy, setCreateWorkBusy] = useState(false);
  const [createWorkError, setCreateWorkError] = useState('');

  // Cadastrar novo projeto
  const [projName, setProjName] = useState('');
  const [projId, setProjId] = useState('');
  const [projLocale, setProjLocale] = useState('pt-BR');
  const [projTz, setProjTz] = useState('America/Sao_Paulo');
  const [projTheme, setProjTheme] = useState('');
  const [projAssetRoot, setProjAssetRoot] = useState('');
  const [projProfiles, setProjProfiles] = useState(() => new Set(DEFAULT_PROJECT_PROFILES));
  const [polBriefing, setPolBriefing] = useState(true);
  const [polScript, setPolScript] = useState(true);
  const [polPii, setPolPii] = useState(true);
  const [polEvidence, setPolEvidence] = useState(true);
  const [createProjBusy, setCreateProjBusy] = useState(false);
  const [createProjFeedback, setCreateProjFeedback] = useState(null);

  // Dialogos
  const [templateCreateOpen, setTemplateCreateOpen] = useState(false);
  const [saveModelWorkId, setSaveModelWorkId] = useState(null);
  const [duplicateWorkId, setDuplicateWorkId] = useState(null);

  const loadWorks = useCallback(async () => {
    setWorksLoading(true);
    setWorksError('');
    try {
      const data = await apiGet('/api/works');
      setWorks(data.works || []);
    } catch (err) {
      setWorksError(err.message);
    } finally {
      setWorksLoading(false);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    setProjectsError('');
    try {
      const data = await apiGet('/api/projects');
      const list = data.projects || [];
      setProjects(list);
      setWorkProject((prev) => prev || list[0]?.path || '');
    } catch (err) {
      setProjectsError(err.message);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  const loadProfiles = useCallback(async () => {
    try {
      const data = await apiGet('/api/profiles');
      setProfiles(data.listing?.profiles || []);
    } catch {
      // erro nao bloqueia listagem principal
    }
  }, []);

  useEffect(() => {
    loadWorks();
    loadProjects();
    loadProfiles();
  }, [loadWorks, loadProjects, loadProfiles]);

  useEffect(() => {
    window.__studioAstryxRefresh = () => {
      loadWorks();
      loadProjects();
    };
    return () => {
      delete window.__studioAstryxRefresh;
    };
  }, [loadWorks, loadProjects]);

  function notifyToast(msg) {
    const bridge = getStudioBridge();
    bridge?.toast?.(msg);
  }

  async function handleOpenWork(id) {
    try {
      const data = await apiGet(`/api/works/open?id=${encodeURIComponent(id)}`);
      const bridge = getStudioBridge();
      bridge?.applyOpenedWork?.(data);
      bridge?.toast?.(`Trabalho retomado: ${data.work.id}`);
      bridge?.setMode?.('video');
    } catch (err) {
      notifyToast(err.message);
    }
  }

  async function handleGuidedDemo(brand) {
    setDemoError('');
    setDemoBusy(true);
    try {
      const data = await apiPost('/api/works/demo', { brand });
      const bridge = getStudioBridge();
      bridge?.applyOpenedWork?.(data);
      bridge?.toast?.(`Demonstração guiada pronta: ${data.work.id}`);
      bridge?.setMode?.('video');
    } catch (err) {
      setDemoError(err.message);
      notifyToast(err.message);
    } finally {
      setDemoBusy(false);
    }
  }

  async function handleRefreshReadiness() {
    const bridge = getStudioBridge();
    if (bridge?.checkReadiness) {
      await bridge.checkReadiness();
      notifyToast('Ambiente reverificado.');
    }
  }

  async function handleCreateWork(e) {
    e.preventDefault();
    setCreateWorkError('');
    setCreateWorkBusy(true);
    try {
      const id = workId.trim();
      const name = workName.trim() || id;
      const data = await apiPost('/api/works/create', {
        id,
        name,
        project: workProject,
        template: workTemplate,
      });
      const bridge = getStudioBridge();
      bridge?.applyOpenedWork?.(data);
      bridge?.toast?.(`Trabalho criado e aberto: ${data.work.id}`);
      bridge?.setMode?.('video');
    } catch (err) {
      setCreateWorkError(err.message);
      notifyToast(err.message);
    } finally {
      setCreateWorkBusy(false);
    }
  }

  async function handleCreateProject(e) {
    e.preventDefault();
    setCreateProjFeedback(null);
    setCreateProjBusy(true);
    const id = projId.trim();
    const name = projName.trim();
    try {
      const data = await apiPost('/api/projects/create', {
        schemaVersion: 1,
        id,
        name,
        locale: projLocale.trim() || 'pt-BR',
        timezone: projTz.trim() || 'America/Sao_Paulo',
        brandTheme: projTheme.trim() || id,
        assetRoot: projAssetRoot.trim() || `.workspace/studio/projects/${id}/assets`,
        contentPolicies: {
          requireApprovedBriefing: polBriefing,
          requireApprovedScript: polScript,
          prohibitPersonalData: polPii,
          requireFunctionalEvidence: polEvidence,
        },
        outputProfiles: Array.from(projProfiles),
      });
      await loadProjects();
      const bridge = getStudioBridge();
      bridge?.loadProjects?.();
      setWorkProject(data.path);
      setCreateProjFeedback({
        status: 'success',
        message: `Projeto cadastrado e validado pelo núcleo: ${data.project.id} (${data.path})`,
      });
      notifyToast(`Projeto cadastrado: ${data.project.id}`);
    } catch (err) {
      setCreateProjFeedback({
        status: 'error',
        message: `Erro ao validar/cadastrar projeto: ${err.message}`,
      });
      notifyToast(err.message);
    } finally {
      setCreateProjBusy(false);
    }
  }

  function toggleWorkSelection(id, checked) {
    setSelectedWorks((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleAllWorks(checked) {
    if (!checked) {
      setSelectedWorks(new Set());
      return;
    }
    setSelectedWorks(new Set(works.map((w) => w.id)));
  }

  function handleOpenBatchExport() {
    const bridge = getStudioBridge();
    if (bridge?.openBatchExportModal) {
      bridge.openBatchExportModal(Array.from(selectedWorks)).catch((err) => notifyToast(err.message));
    }
  }

  function toggleProjProfile(profileId, checked) {
    setProjProfiles((prev) => {
      const next = new Set(prev);
      if (checked) next.add(profileId);
      else next.delete(profileId);
      return next;
    });
  }

  const allWorksSelected = works.length > 0 && works.every((w) => selectedWorks.has(w.id));

  const worksColumns = [
    {
      key: '_select',
      width: pixel(44),
      header: (
        <CheckboxInput
          id="works-select-all"
          label="Selecionar todos"
          isLabelHidden
          checked={allWorksSelected}
          onChange={(checked) => toggleAllWorks(checked)}
        />
      ),
      renderCell: (w) => (
        <CheckboxInput
          label={`Selecionar ${w.id}`}
          isLabelHidden
          checked={selectedWorks.has(w.id)}
          onChange={(checked) => toggleWorkSelection(w.id, checked)}
        />
      ),
    },
    { key: 'id', header: 'ID', width: proportional(1, { minWidth: 120 }) },
    { key: 'name', header: 'Trabalho', width: proportional(1.3, { minWidth: 140 }) },
    {
      key: 'project',
      header: 'Projeto',
      width: proportional(0.9, { minWidth: 100 }),
      renderCell: (w) => w.projectId || w.project,
    },
    {
      key: 'video',
      header: 'Vídeo',
      width: proportional(0.9, { minWidth: 100 }),
      renderCell: (w) => renderDeliveryStatus(w.summary?.videoValidCount, w.summary?.videoLastStatus),
    },
    {
      key: 'carousel',
      header: 'Carrossel',
      width: proportional(0.9, { minWidth: 100 }),
      renderCell: (w) => renderDeliveryStatus(w.summary?.carouselValid, w.summary?.carouselLastStatus),
    },
    {
      key: 'motion',
      header: 'Motion',
      width: proportional(0.9, { minWidth: 100 }),
      renderCell: (w) => renderDeliveryStatus(w.summary?.motionValidCount, w.summary?.motionLastStatus),
    },
    {
      key: 'updatedAt',
      header: 'Atualizado',
      width: proportional(1, { minWidth: 130 }),
      renderCell: (w) => (w.updatedAt || '').replace('T', ' ').replace('Z', ''),
    },
    {
      key: 'actions',
      header: 'Ações',
      width: pixel(310),
      renderCell: (w) => (
        <div className="astryx-actions-row">
          <Button
            variant="primary"
            size="sm"
            label="Reabrir"
            onClick={() => handleOpenWork(w.id)}
          />
          <Button
            variant="secondary"
            size="sm"
            label="Salvar como modelo"
            onClick={() => setSaveModelWorkId(w.id)}
          />
          <Button
            variant="secondary"
            size="sm"
            label="Duplicar como rascunho"
            onClick={() => setDuplicateWorkId(w.id)}
          />
        </div>
      ),
    },
  ];

  const projectsColumns = [
    { key: 'id', header: 'ID', width: proportional(1, { minWidth: 120 }) },
    { key: 'name', header: 'Nome', width: proportional(1.2, { minWidth: 140 }) },
    {
      key: 'source',
      header: 'Origem',
      width: pixel(110),
      renderCell: (p) => (
        <Badge
          variant={p.source === 'registered' ? 'success' : 'neutral'}
          label={p.sourceLabel || p.source || 'exemplo'}
        />
      ),
    },
    { key: 'locale', header: 'Locale', width: pixel(90) },
    {
      key: 'outputProfiles',
      header: 'Destinos permitidos',
      width: proportional(1.8, { minWidth: 200 }),
      renderCell: (p) => (p.outputProfiles || []).join(', '),
    },
  ];

  const workIdPreview = workId.trim() || '<id-do-trabalho>';

  return (
    <div className="astryx-home-pilot" data-testid="astryx-home-pilot">
      {/* 1. Demonstracao guiada */}
      <Card id="sec-demo" padding={4}>
        <Stack direction="vertical" gap={3}>
          <Heading level={2}>Primeira execução e demonstração guiada</Heading>
          <Text size="sm" color="secondary">
            Crie com 1 clique um trabalho completo usando exemplos fictícios versionados para testar Vídeo vertical, Carrossel quadrado e Motion no navegador, sem digitar caminhos.
          </Text>
          <div className="astryx-actions-row">
            <Button
              id="btn-demo-marca-salao"
              variant="primary"
              label={demoBusy ? 'Preparando…' : 'Demonstração guiada — Marca Salão'}
              onClick={() => handleGuidedDemo('marca-salao')}
              isDisabled={demoBusy}
            />
            <Button
              id="btn-demo-multitrack"
              variant="secondary"
              label="Demonstração guiada — Multitrack Hub"
              onClick={() => handleGuidedDemo('multitrack-hub')}
              isDisabled={demoBusy}
            />
            <Button
              id="btn-refresh-readiness"
              variant="secondary"
              label="Reverificar ambiente"
              onClick={handleRefreshReadiness}
            />
          </div>
          {demoError ? (
            <Banner status="error" title="Erro na demonstração guiada" description={demoError} collapsible={false} />
          ) : null}
        </Stack>
      </Card>

      {/* 2. Trabalhos recentes */}
      <Card id="sec-works-list" padding={4}>
        <Stack direction="vertical" gap={3}>
          <div className="astryx-section-head">
            <Heading level={2}>Trabalhos recentes (retomada)</Heading>
            <div className="astryx-actions-row">
              <Text id="works-batch-count" size="sm" color="secondary">
                {selectedWorks.size} selecionado(s)
              </Text>
              <Button
                id="btn-open-template-create"
                variant="secondary"
                label="Criar a partir de modelo"
                onClick={() => setTemplateCreateOpen(true)}
              />
              <Button
                id="btn-open-batch-export"
                variant="primary"
                label="Exportar em lote"
                onClick={handleOpenBatchExport}
              />
            </div>
          </div>

          <Text size="sm" color="secondary">
            Feche o painel e reabra qualquer trabalho depois mantendo rascunhos, mídias, últimas tentativas e entregas válidas.
          </Text>

          {worksLoading ? (
            <Stack direction="horizontal" gap={2} vAlign="center">
              <Spinner size="sm" />
              <Text size="sm" color="secondary">Carregando trabalhos recentes…</Text>
            </Stack>
          ) : worksError ? (
            <Banner
              status="error"
              title="Não foi possível carregar os trabalhos"
              description={worksError}
              collapsible={false}
              actions={<Button variant="secondary" size="sm" label="Tentar novamente" onClick={loadWorks} />}
            />
          ) : !works.length ? (
            <EmptyState
              title="Nenhum trabalho criado ainda"
              description="Use a demonstração guiada acima ou crie um trabalho no formulário abaixo."
              isCompact
            />
          ) : (
            <div className="astryx-table-scroll">
              <Table
                id="works-table"
                data={works}
                columns={worksColumns}
                idKey="id"
                density="compact"
                dividers="rows"
                hasHover
                textOverflow="wrap"
              />
            </div>
          )}
        </Stack>
      </Card>

      {/* 3. Criar novo trabalho */}
      <Card id="sec-work-create" padding={4}>
        <form onSubmit={handleCreateWork}>
          <Stack direction="vertical" gap={3}>
            <Heading level={2}>Criar novo trabalho</Heading>
            <div className="astryx-form-grid">
              <TextInput
                id="work-name"
                label="Nome do trabalho"
                placeholder="Ex.: Campanha Demonstrativa Abril"
                value={workName}
                onChange={setWorkName}
              />
              <TextInput
                id="work-id"
                label="ID do trabalho (kebab-case)"
                placeholder="campanha-demonstrativa-abril"
                value={workId}
                onChange={setWorkId}
                isRequired
              />
              <label className="astryx-select-field">
                <span className="astryx-select-label">Projeto</span>
                <select
                  id="work-project"
                  className="astryx-native-select"
                  value={workProject}
                  onChange={(e) => setWorkProject(e.target.value)}
                >
                  <option value="">— selecione —</option>
                  {projects.map((p) => (
                    <option key={p.path} value={p.path}>
                      [{p.source === 'registered' ? 'Cadastrado' : 'Exemplo'}] {p.id} — {p.name || ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="astryx-select-field">
                <span className="astryx-select-label">Modelo inicial</span>
                <select
                  id="work-template"
                  className="astryx-native-select"
                  value={workTemplate}
                  onChange={(e) => setWorkTemplate(e.target.value)}
                >
                  <option value="marca-salao">Modelo fictício Marca Salão (3 módulos prontos)</option>
                  <option value="multitrack-hub">Modelo fictício Multitrack Hub (3 módulos prontos)</option>
                  <option value="blank">Trabalho em branco com estrutura e mídia inicial</option>
                </select>
              </label>
            </div>
            <Text id="work-paths-preview" size="sm" color="secondary">
              Caminhos automáticos em .workspace/studio/works/{workIdPreview}/ (rascunhos/, media/ compartilhada e deliveries/).
            </Text>
            <div className="astryx-actions-row">
              <Button
                id="btn-create-work"
                type="submit"
                variant="primary"
                label={createWorkBusy ? 'Criando trabalho…' : 'Criar e abrir trabalho'}
                isDisabled={createWorkBusy}
              />
            </div>
            {createWorkError ? (
              <Banner status="error" title="Erro ao criar trabalho" description={createWorkError} collapsible={false} />
            ) : null}
          </Stack>
        </form>
      </Card>

      {/* 4. Projetos (ProjectManifest v1) */}
      <Card id="sec-projects-register" padding={4}>
        <Stack direction="vertical" gap={3}>
          <Heading level={2}>Projetos (ProjectManifest v1)</Heading>
          <Text size="sm" color="secondary">
            Cadastre um projeto válido sem editar JSON (validado pelo núcleo da platform) ou use os exemplos versionados.
          </Text>

          {projectsLoading ? (
            <Stack direction="horizontal" gap={2} vAlign="center">
              <Spinner size="sm" />
              <Text size="sm" color="secondary">Carregando projetos…</Text>
            </Stack>
          ) : projectsError ? (
            <Banner
              status="error"
              title="Não foi possível carregar os projetos"
              description={projectsError}
              collapsible={false}
            />
          ) : (
            <div className="astryx-table-scroll">
              <Table
                id="projects-table"
                data={projects}
                columns={projectsColumns}
                idKey="path"
                density="compact"
                dividers="rows"
                hasHover
                textOverflow="wrap"
              />
            </div>
          )}

          <form onSubmit={handleCreateProject}>
            <fieldset className="astryx-fieldset" id="project-form-fieldset">
              <legend>Cadastrar novo projeto</legend>
              <div className="astryx-form-grid">
                <TextInput
                  id="proj-name"
                  label="Nome do projeto"
                  placeholder="Estúdio Aurora"
                  value={projName}
                  onChange={setProjName}
                />
                <TextInput
                  id="proj-id"
                  label="ID (kebab-case)"
                  placeholder="estudio-aurora"
                  value={projId}
                  onChange={setProjId}
                />
                <TextInput
                  id="proj-locale"
                  label="Locale"
                  value={projLocale}
                  onChange={setProjLocale}
                />
                <TextInput
                  id="proj-tz"
                  label="Timezone"
                  value={projTz}
                  onChange={setProjTz}
                />
                <TextInput
                  id="proj-theme"
                  label="Tema da marca (brandTheme)"
                  placeholder="estudio-aurora"
                  value={projTheme}
                  onChange={setProjTheme}
                />
                <TextInput
                  id="proj-asset-root"
                  label="Raiz de assets (assetRoot)"
                  placeholder=".workspace/studio/projects/estudio-aurora/assets"
                  value={projAssetRoot}
                  onChange={setProjAssetRoot}
                />
              </div>

              <div>
                <Text size="sm" weight="medium">Destinos permitidos (allowlist)</Text>
                <div id="proj-profiles-boxes" className="astryx-checks-grid" style={{ marginTop: '6px' }}>
                  {profiles.map((p) => {
                    const mods = (p.compatibleModules || []).join('/') || 'sem render local';
                    const label = `${p.id} (${p.aspectRatio} ${p.width}×${p.height} — ${mods})`;
                    return (
                      <CheckboxInput
                        key={p.id}
                        label={label}
                        checked={projProfiles.has(p.id)}
                        onChange={(checked) => toggleProjProfile(p.id, checked)}
                      />
                    );
                  })}
                </div>
              </div>

              <div>
                <Text size="sm" weight="medium">Políticas editoriais</Text>
                <div className="astryx-checks-grid" style={{ marginTop: '6px' }}>
                  <CheckboxInput
                    id="proj-pol-briefing"
                    label="Exigir briefing aprovado"
                    checked={polBriefing}
                    onChange={setPolBriefing}
                  />
                  <CheckboxInput
                    id="proj-pol-script"
                    label="Exigir roteiro aprovado"
                    checked={polScript}
                    onChange={setPolScript}
                  />
                  <CheckboxInput
                    id="proj-pol-pii"
                    label="Proibir dados pessoais"
                    checked={polPii}
                    onChange={setPolPii}
                  />
                  <CheckboxInput
                    id="proj-pol-evidence"
                    label="Exigir evidência funcional"
                    checked={polEvidence}
                    onChange={setPolEvidence}
                  />
                </div>
              </div>

              <div className="astryx-actions-row">
                <Button
                  id="btn-create-project"
                  type="submit"
                  variant="primary"
                  label={createProjBusy ? 'Validando…' : 'Validar e cadastrar projeto'}
                  isDisabled={createProjBusy}
                />
              </div>

              {createProjFeedback ? (
                <Banner
                  status={createProjFeedback.status}
                  title={createProjFeedback.status === 'success' ? 'Projeto validado' : 'Erro de validação'}
                  description={createProjFeedback.message}
                  collapsible={false}
                />
              ) : null}
            </fieldset>
          </form>
        </Stack>
      </Card>

      {/* Dialogos */}
      <TemplateCreateDialog
        isOpen={templateCreateOpen}
        onClose={() => setTemplateCreateOpen(false)}
        onOpenCreatedWork={handleOpenWork}
      />
      <SaveAsTemplateDialog
        workId={saveModelWorkId}
        isOpen={Boolean(saveModelWorkId)}
        onClose={() => setSaveModelWorkId(null)}
        onSaved={(res) => notifyToast(`Modelo ${res.template.id} salvo (${res.revisionId}).`)}
      />
      <DuplicateWorkDialog
        workId={duplicateWorkId}
        isOpen={Boolean(duplicateWorkId)}
        onClose={() => setDuplicateWorkId(null)}
        onDuplicated={(res) => {
          notifyToast(`Trabalho duplicado: ${res.work.id}`);
          loadWorks();
        }}
      />
    </div>
  );
}
