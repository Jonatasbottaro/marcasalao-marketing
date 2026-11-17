# Proposta de Autorização — Execução Real de TEMPORAL-02 em Produção

> **Objetivo:** Delimitar escopo, componentes, riscos, evidências exigidas e critérios de ratificação para levar a validação de Composition (`validate-composition`) do ambiente local (já integrado e validado) para execução real em produção com Worker persistente, servidor Temporal remoto e namespace de produção.

---

## 1. Contexto e Estado Atual

### 1.1 O que já está integrado na `main` (escopo estritamente local)

| Fatia | Commit / Merge | Status | Evidência |
|-------|----------------|--------|-----------|
| **TEMPORAL-02-01** — Fronteira pública mínima da `platform` | `f202377` | ✅ Integrado | 315 testes, CI Ubuntu/Windows Node 22/24 |
| **TEMPORAL-02-02** — Contrato de entrada + preflight local | `29b4078` | ✅ Integrado | 17 testes, limites 64/256/384 KiB, política sensível |
| **TEMPORAL-02-03** — Activity real `validateCompositionActivity` | `db84270` | ✅ Integrado + ratificado | 8 testes, consome `marcasalao-marketing-platform@0.1.0` |
| **Fatia Workflow** — `validateCompositionWorkflow`, resultado, classificador, Retry Policy | `f584210` | ✅ Integrado + ratificado (11/11/2026) | 17 testes, 162 totais, repetibilidade 7/7 |
| **Execução local completa** — Cliente, Worker, CLI, replay formal, gate Elephant–Goldfish | `5376890` | ✅ Integrado (12/11/2026) | 198 testes, `createLocal`, replay fixture versionado |

### 1.2 O que permanece **bloqueado** (não autorizado)

- Worker de produção dedicado à composição
- Servidor Temporal remoto (Temporal Cloud ou self-hosted)
- Namespace de produção
- `contentHash` e canonicalização de entrada
- Cliente Temporal de validação no código da aplicação (`workflow.start` real)
- Deploy (CI/CD, infraestrutura, secrets, observabilidade)
- TEMPORAL-04 (combinação OutputPlan/BeatPlan, prévia, exportação, renderização)
- Mídia, fornecedores, publicação, campanha real

### 1.3 Precedentes de governança

- **R002** (piloto técnico local de vídeo): reprodução limpa, inspeção FFprobe, prova transacional, hashes, documentação no mesmo marco — autorizado para branch, merge na main exigiu autorização separada
- **Execução local TEMPORAL-02**: mesma abordagem — implementar, testar, documentar, CI, gate Elephant–Goldfish, **depois** autorização para merge
- **Ratificação da fatia Workflow** (11/11/2026): escopo estrito, não autoriza fatia posterior

---

## 2. Escopo da Proposta

### 2.1 Incluído nesta autorização (produção de `validate-composition`)

| Componente | Descrição | Estado atual |
|------------|-----------|--------------|
| **Worker de produção** | Serviço persistente, registrado no namespace de produção, Task Queue `composition-validation-v1`, health checks, graceful shutdown, métricas | ❌ Não existe |
| **Servidor Temporal remoto** | Temporal Cloud (preferencial) ou self-hosted com mTLS, namespace `production`, retenção de history configurada | ❌ Não existe |
| **Namespace de produção** | Isolado de `default` (local), políticas de retenção, visibilidade, RBAC | ❌ Não existe |
| **Cliente de aplicação** | `startCompositionValidation` / `executeCompositionValidation` integrados ao fluxo real (ex.: API, job agendado, trigger manual), com preflight obrigatório | ⚠️ Existe como CLI local, não como cliente de app |
| **`contentHash`** | Canonicalização JSON determinística (SHA-256) dos documentos `project` + `composition` para idempotência real e deduplicação | ❌ Não implementado |
| **Deploy & Infraestrutura** | Containerização (Docker), CI/CD (GitHub Actions ou equivalente), secrets management, variáveis de ambiente por ambiente | ❌ Não existe |
| **Observabilidade produção** | Logs estruturados (JSON), métricas (Prometheus/OpenTelemetry), tracing (Temporal built-in + custom), alertas (falha, timeout, colisão, latência) | ⚠️ Mínima (apenas logs CLI) |
| **Segurança produção** | mTLS cliente-servidor, certificados rotacionados, RBAC no Temporal, secrets no Vault/Key Vault, sem credenciais em código | ❌ Não configurado |
| **Disaster Recovery** | Multi-region Temporal (se Cloud), backup de namespace, runbook de failover, RPO/RTO definidos | ❌ Não definido |

### 2.2 Fora de escopo (requer autorização separada futura)

- TEMPORAL-04 (OutputPlan, BeatPlan, prévia, exportação, renderização)
- Novas Activities/Workflows além de `validate-composition`
- Integração com fornecedores de mídia, IA, renderização
- Campanhas reais, conteúdo editorial, publicação

---

## 3. Componentes Técnicos a Implementar

### 3.1 Worker de Produção (`orchestration/temporal/`)

```typescript
// Novo entrypoint: src/worker/production-worker.ts
// - Worker.create() com connection persistente (não createLocal)
// - Namespace configurável via env (TEMPORAL_NAMESPACE=production)
// - Task Queue: composition-validation-v1
// - Health endpoint HTTP (/health, /ready)
// - Métricas Prometheus (/metrics)
// - Graceful shutdown com SIGTERM (já tem lifecycle, adaptar)
// - Registro de worker identity para observabilidade
```

### 3.2 Cliente de Aplicação

```typescript
// Reutilizar: src/client/composition-validation-start.ts
// - startCompositionValidation / executeCompositionValidation já prontos
// - Preflight obrigatório já implementado
// - Adicionar: retry de conexão com backoff, circuit breaker opcional
// - Integrar no fluxo real (ex.: API route, job scheduler, CLI de produção)
```

### 3.3 `contentHash` — Canonicalização JSON

```typescript
// Novo módulo: src/content-hash.ts
// - canonicalize(obj): string — JSON com chaves ordenadas, sem espaços, UTF-8
// - contentHash(project, composition): string — SHA-256(canonicalize(project) + canonicalize(composition))
// - Usado no cliente para compor Workflow ID: composition-validation-<requestId>-<contentHash[0:8]>
// - Validado na Activity: recomputar e comparar (idempotência real)
// - Testes: paridade com corpus TEMPORAL-02, round-trip, determinismo cross-platform
```

### 3.4 Deploy & Infraestrutura

| Item | Tecnologia sugerida | Responsabilidade |
|------|---------------------|------------------|
| Container | Docker (multi-stage, distroless/base) | Empacotar Worker + CLI |
| Orquestração | Kubernetes (AKS/EKS/GKE) ou Container Apps | Deploy, scaling, health |
| CI/CD | GitHub Actions (workflow dedicado) | Build, test, security scan, deploy |
| Secrets | Azure Key Vault / HashiCorp Vault / GitHub Environments | Certificados mTLS, API keys |
| Config | Variáveis de ambiente + ConfigMap | Namespace, address, task queue, timeouts |
| DNS/Ingress | Interno (ClusterIP) ou privado | Worker não exposto publicamente |

### 3.5 Observabilidade

| Sinal | Fonte | Alvo |
|-------|-------|------|
| `workflow_started_total` | Cliente (após start bem-sucedido) | Counter |
| `workflow_completed_total{status="valid\|invalid\|failed"}` | Cliente (após result) | Counter |
| `workflow_duration_seconds` | Cliente (start→result) | Histogram |
| `activity_duration_seconds` | Worker (Activity) | Histogram |
| `worker_health` | Worker (/health) | Gauge (1/0) |
| `temporal_connection_errors_total` | Cliente/Worker | Counter |
| Logs JSON | Todos os componentes | Loki/Elastic/CloudWatch |
| Traces | OpenTelemetry SDK + Temporal propagação | Tempo/Jaeger |

### 3.6 Segurança

- **mTLS**: Certificados gerados/rotacionados via Temporal Cloud ou `tctl` (self-hosted)
- **Namespace isolation**: `production` separado de `default`/`staging`
- **RBAC**: Roles mínimas para Worker (poll task queue), Cliente (start workflow), Operador (read history)
- **Secrets**: Zero no código, zero no container image, injetados em runtime
- **Network**: Worker só acessa Temporal gRPC (porta 7233/443), sem egresso público

---

## 4. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **History com dados sensíveis** | Média | Alto | Preflight obrigatório (já implementado), limites de payload, documentos técnicos apenas, `contentHash` evita reenvio |
| **Worker indisponível** | Baixa | Alto | Múltiplas réplicas (HPA), health checks, alerta de worker down, runbook de restart |
| **Temporal server indisponível** | Baixa | Crítico | Temporal Cloud SLA 99.99%, multi-region, namespace failover, circuit breaker no cliente |
| **Colisão de Workflow ID em produção** | Baixa | Médio | `contentHash` no ID, `REJECT_DUPLICATE` + `FAIL`, monitoramento de `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT` |
| **Timeout `StartToCloseTimeout` em produção** | Média | Médio | Timeout 5s (ratificado), alerta se > 2s, investigar latência Worker↔Server |
| **Vazamento de credenciais no container/logs** | Baixa | Crítico | Secrets apenas em runtime, logs sanitizados (já implementado), scanner de secrets no CI |
| **Drift de schema `CompositionValidationWorkflowInput`** | Baixa | Alto | Testes de contrato versionados, breaking change = nova `schemaVersion`, migração planejada |
| **Custo Temporal Cloud inesperado** | Média | Médio | Orçamento mensal, alerta de uso, otimização de payload (limites já definidos) |

---

## 5. Evidências Exigidas para Ratificação

### 5.1 Critérios Técnicos (obrigatórios)

| # | Critério | Como comprovar |
|---|----------|----------------|
| 1 | **Worker de produção sobe e registra na Task Queue** | Logs: `worker de validacao de composition na task queue composition-validation-v1 namespace production contra <address>` |
| 2 | **Cliente de aplicação inicia Workflow remoto** | `executeCompositionValidation` com `TEMPORAL_ADDRESS` remoto, `TEMPORAL_NAMESPACE=production`, exit 0/1/3/4/5 conforme resultado |
| 3 | **`contentHash` implementado e validado** | Testes unitários: determinismo, cross-platform, paridade com corpus; integração: Workflow ID inclui hash, Activity valida |
| 4 | **Deploy automatizado e reproduzível** | GitHub Actions workflow: build → test → security scan → deploy staging → smoke test → deploy production (manual approval) |
| 5 | **Observabilidade funcional** | Métricas expostas em `/metrics`, logs JSON no agregador, traces propagados, dashboard com latência p50/p95/p99, taxa de erro |
| 6 | **Segurança configurada** | mTLS ativo (verificar handshake), secrets não em imagem, RBAC aplicado, scanner de secrets no CI passa |
| 7 | **Replay formal em produção** | `npm run composition:replay` contra history de produção (sanitizada) passa; gate de não-determinismo passa |
| 8 | **Gate Elephant–Goldfish de produção executado** | Revisão adversarial + simplicidade sobre código de produção, registro em `docs/TEMPORAL-02-PRODUCTION-ELEPHANT-GOLDFISH.md` |
| 9 | **CI verde em Ubuntu + Windows** | Pipeline dedicado (`.github/workflows/temporal-production-validation.yml`) com matrix Node 22/24 |
| 10 | **Runbook de incidentes documentado** | `docs/runbooks/temporal-composition-validation.md`: worker down, server down, colisão, timeout, deploy rollback |

### 5.2 Critérios de Governança (obrigatórios)

| # | Critério | Como comprovar |
|---|----------|----------------|
| 11 | **Autorização explícita do titular** | Registro em `docs/contexto/ESTADO-ATUAL.md` e `PROXIMOS-PASSOS.md` com data e escopo |
| 12 | **Escopo delimitado e assinado** | Este documento aprovado sem alterações de escopo posterior sem nova autorização |
| 13 | **PRD TEMPORAL-02 não precisa ser "aprovado" globalmente** | A ratificação da fatia Workflow (11/11/2026) + esta autorização de produção cobrem o passo real `validate-composition` |
| 14 | **Nenhuma combinação com OutputPlan/BeatPlan/TEMPORAL-04** | Varredura estática: `platform/` sem `@temporalio`, `orchestration/temporal/` sem import de OutputPlan/BeatPlan |
| 15 | **Rollback testado** | Deploy staging → falha intencional → rollback automático → verificação de estado anterior |

---

## 6. Plano de Implementação (Fases)

### Fase 1 — Fundação (2-3 semanas)
- [ ] `contentHash` canonicalização + testes
- [ ] Worker de produção entrypoint + health/metrics
- [ ] Dockerfile multi-stage (Worker + CLI)
- [ ] GitHub Actions workflow de build/test/security

### Fase 2 — Infraestrutura (2-3 semanas)
- [ ] Provisionar Temporal Cloud (ou self-hosted staging)
- [ ] Namespace `production` + `staging`
- [ ] Certificados mTLS + secrets no Vault
- [ ] Deploy staging via CI/CD
- [ ] Smoke tests automatizados contra staging

### Fase 3 — Observabilidade & Segurança (1-2 semanas)
- [ ] Métricas Prometheus + dashboards Grafana
- [ ] Logs JSON → Loki/Elastic
- [ ] Traces OpenTelemetry → Tempo/Jaeger
- [ ] Alertas: worker down, error rate > 1%, p99 latency > 10s
- [ ] Scanner de secrets no CI (gitleaks/trufflehog)
- [ ] Pen test leve / revisão de segurança

### Fase 4 — Validação & Ratificação (1 semana)
- [ ] Execução end-to-end em staging: valid, invalid, collision, timeout
- [ ] Replay formal contra history de staging
- [ ] Gate Elephant–Goldfish de produção
- [ ] Documentação de runbooks
- [ ] Apresentação de evidências ao titular para ratificação

### Fase 5 — Produção (após ratificação)
- [ ] Deploy production (manual approval no CI/CD)
- [ ] Monitoramento ativo 48h
- [ ] Handoff para operação
- [ ] Atualização `ESTADO-ATUAL.md` com commit/merge de produção

---

## 7. Estimativa de Esforço

| Fase | Esforço (pessoa-semanas) | Dependências |
|------|--------------------------|--------------|
| 1. Fundação | 2-3 | Nenhuma (código existente) |
| 2. Infraestrutura | 2-3 | Acesso Temporal Cloud / AKS, Vault |
| 3. Observabilidade & Segurança | 1-2 | Fase 2 concluída |
| 4. Validação & Ratificação | 1 | Fases 1-3 concluídas |
| **Total** | **6-9** | — |

> **Nota:** Estimativa qualitativa. Não inclui tempo de aprovisionamento de nuvem, aquisição de Temporal Cloud, ou revisões de segurança corporativa.

---

## 8. Critérios de "Não Iniciar"

Não iniciar implementação se:

- [ ] Temporal Cloud / self-hosted não estiver provisionado e acessível
- [ ] Vault / Key Vault não estiver configurado para secrets
- [ ] CI/CD não tiver permissão para deploy no cluster alvo
- [ ] Orçamento de custo Temporal Cloud não estiver aprovado
- [ ] Runbook de incidentes não tiver dono definido (on-call)

---

## 9. Autorização Solicitada

| Item | Solicitado | Decisão |
|------|------------|---------|
| Implementar Worker de produção, `contentHash`, Docker, CI/CD | ✅ Sim / Não | [ ] |
| Provisionar Temporal Cloud (ou self-hosted) + namespace production | ✅ Sim / Não | [ ] |
| Configurar observabilidade (métricas, logs, traces, alertas) | ✅ Sim / Não | [ ] |
| Configurar segurança (mTLS, RBAC, secrets, scanner) | ✅ Sim / Não | [ ] |
| Executar gate Elephant–Goldfish de produção | ✅ Sim / Não | [ ] |
| Deploy em produção após ratificação das evidências | ✅ Sim / Não | [ ] |
| Orçamento estimado (Temporal Cloud + infra) | A definir | [ ] |

---

## 10. Próximos Passos Imediatos (após autorização)

1. **Registrar autorização** em `docs/contexto/ESTADO-ATUAL.md` com data, escopo e commit base
2. **Criar branch técnica** `codex/temporal-02-production` a partir de `origin/main`
3. **Iniciar Fase 1** — `contentHash` + Worker produção + Docker
4. **Agendar revisão semanal** de progresso com titular
5. **Preparar gate Elephant–Goldfish** para Fase 4

---

## 11. Referências

- [ESTADO-ATUAL.md](../contexto/ESTADO-ATUAL.md) — seções TEMPORAL-02, TEMPORAL-02-03, Fatia Workflow, Execução local
- [PROXIMOS-PASSOS.md](../contexto/PROXIMOS-PASSOS.md) — item 6: "Preparar a proposta de autorização para execução real em produção"
- [TEMPORAL-02-validacao-de-composition.md](./TEMPORAL-02-validacao-de-composition.md) — PRD original (seções 7, 13-23, 27, 32)
- [orchestration/temporal/README.md](../../orchestration/temporal/README.md) — seções TEMPORAL-02-02, TEMPORAL-02-03, Fatia Workflow, Execução local, Gate Elephant–Goldfish
- [docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md](../../orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md) — gate da execução local (precedente)
- [AGENTS.md](../../AGENTS.md) — regras de armazenamento, Git, handoff, bloqueios

---

**Documento preparado em:** 2026-11-17  
**Base Git:** `origin/main` (conferir `git rev-parse origin/main` no momento da autorização)  
**Autor:** Agente técnico — revisão e decisão do titular requerida antes de qualquer implementação