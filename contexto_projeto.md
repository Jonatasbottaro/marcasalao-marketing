# contexto_projeto.md — Devlog acumulativo — Marca Salão Content Factory

> **Classificação (22/11/2026): devlog histórico.** A seção 1 abaixo reflete a base
> `babfc60` (21/11/2026) e está **desatualizada** quanto a gates (hoje 9), domínios (hoje 8)
> e HEAD da main. O estado vigente vive em
> [docs/contexto/ESTADO-ATUAL.md](docs/contexto/ESTADO-ATUAL.md); este arquivo permanece
> como registro acumulativo de sessões, consolidado por `tools/devlog_sync.py`. Entradas
> anteriores não são apagadas nem reescritas retroativamente.

> Este arquivo é um devlog permanente. **Nunca apagar entradas anteriores.**
> Novas sessões adicionam entradas ao final da seção "Histórico de sessões".
> O topo (seção 1) é sempre atualizado para refletir o estado atual.

---

## 1. Estado atual (atualizado em 2026-11-21)

| Item | Valor |
|------|-------|
| Raiz oficial | `<RAIZ>`, o checkout principal retornado por `git rev-parse --show-toplevel` |
| Último commit técnico validado na main | `babfc60` — merge híbrido do comparativo Hook A/B (teste z de duas proporções), com `release_check.py` **7/7 gates**, `editorial_qa --strict` 14 campanhas sem problemas e suíte canônica de 396 testes (2 falhas apenas pelo efeito colateral dos masters em `.workspace/archives/`, resolvidas pela restauração). Último CI verde confirmado no GitHub Actions: `9a800d1` ([run 44904714554](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/44904714554)); o CI dos commits posteriores ainda não foi conferido nesta estação (sem `gh` instalado). |
| Branch de trabalho ativa | `main`, **sincronizada com `origin/main` em `babfc60`**. Etapa 7 (`899d36b`, `19e74c0`, `227e939`) e os checkpoints WIP (`4ce5566`, `cce0d8c`) já foram enviados ao remoto. |
| Worktrees de outros agentes | preservadas — ver seção 3 |
| Fase atual | Etapa 8 em andamento — comparativo Hook A/B híbrido com significância estatística integrado à main; 5 tenants / 14 campanhas e calendário de 7 semanas |
| Status das 5 tarefas | Fase 1, Etapa 1, Etapa 2, Etapa 3, Etapa 4, Etapa 5 e Etapa 6 (Etapa 5: Agentes 1, 2, 3, 4, 5, 6, 7, 8, 9 + Etapa 6: Agentes 1, 2, 3, 4, 5, 6, 7, 8) concluídas — ver seções 2 e 7 |
---

## 2. Fase 1 — Resumo de execução (2026-11-18)

### Tarefa 1 — Auditoria de identidade visual ("Meu Salão" vs "Marca Salão")

**Resultado: Substituições seguras realizadas em materiais editoriais e de legendas; divergências de interface externa documentadas.**

**1. Substituições seguras realizadas (camada editorial/legendas):**
- `04-legendas/instagram_captions.md`: "Acesse o Dashboard do Meu Salão" → "Acesse o Dashboard do Marca Salão"
- `04-legendas/legendas_cards.md`: "**Acesse o Dashboard do Meu Salão**" → "**Acesse o Dashboard do Marca Salão**"
- `04-legendas/roteiro_0802_cadastro_profissional.md`: "No Meu Salão..." e "Meu Salão: Mais visibilidade..." → padronizado para "Marca Salão"
- `04-legendas/roteiro_demo_link_agendamento.md`: "Conheça o Meu Salão..." e ícone do app → padronizado para "Marca Salão"
- `04-legendas/roteiro_demo_link_agendamento.srt`: Cues 1 e 6 padronizados para "Marca Salão"

**2. Ocorrências preservadas intencionalmente:**
- `00-briefings/campanhas/NS-001/briefing.md` e `VALIDACAO-EXECUCAO-2026-11-05.md`: registros de divergência conhecida e dados técnicos de teste (`Meu Salão E2E`) — mantidos como registro histórico e técnico.
- `01-insta-stories/06_meu_salao.png` e referências em README: nome físico do arquivo de captura existente em disco.
- "Facebook Meu salão": nome oficial da Página no Facebook (ativo nas redes).
- Interface de produto: o sistema externo (`Jonatasbottaro/Salao02`) renderiza "Meu Salão" na sidebar e título. **Não está neste repositório para ser alterado aqui.**

**Conclusão da auditoria:**
- A camada de legendas e narrações agora está 100% padronizada em **Marca Salão**.
- **Ponto de atenção para o titular:** confirmar, antes das capturas finais, se a interface do produto (Salao02) receberá atualização de marca ou se as capturas finais serão tratadas com overlay de tela.

---

### Tarefa 2 — Fixture editorial dedicada

**Resultado: Criada em `docs/fixtures/fixture-editorial-marca-salao.json`.**

- Nome do estabelecimento: **Marca Salão**
- Profissionais: Camila Rocha, Rafael Mendes, Juliana Costa, Lucas Alves
- Serviços com durações e preços BRL realistas: Corte Feminino (60 min / R$ 85), Escova Modelada (45 min / R$ 65), Hidratação Profunda (50 min / R$ 110), Manicure e Pedicure (90 min / R$ 70), Barba e Corte Masculino (45 min / R$ 75)
- Agenda para 2026-11-18: 9 atendimentos distribuídos ao longo do dia com status Confirmado/Aguardando/Concluído
- Separação de rotas respeitada: dados de `/gestor/agenda` separados de dados de `/booking/[salonId]`
- Sem fluxo de pagamento simulado
- Sem dados genéricos de teste (lorem ipsum, user1, test)
- **NÃO é fixture de testes técnicos E2E** — não substituir `tools/r002/agenda-ficticia.pilot.json` nem qualquer outro arquivo usado pelo CI

---

### Tarefa 3 — Rastreio UTM

**Resultado: Criado `docs/rastreio-utm.md`.**

- Padrão definido: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`
- Campanhas mapeadas: `ns-001` (Organização e visibilidade da agenda), `ns-002` (Agendamento online no Marca Salão)
- Exemplos prontos para Instagram Reels, Stories e Facebook Feed
- Ferramenta de analytics: **PENDENTE** — preencher antes da primeira publicação com link rastreado
- Regra: enquanto PENDENTE, não declarar links UTM como ativos nos registros de campanha

---

### Tarefa 4 — Conformidade dos roteiros NS-001 e NS-002

#### NS-001 — Organização e visibilidade da agenda
**Versão revisada:** 0.3 — data 2026-11-05 — Status: rascunho

| Guardrail | Status | Evidência no roteiro |
|-----------|--------|---------------------|
| Sem promessas de automação (WhatsApp/SMS/e-mail, lembretes, confirmações automáticas) | ✅ CONFORME | Seção 1 do roteiro: "Este roteiro não promete... mensagens automáticas, lembretes automáticos ou confirmações automáticas." |
| Separação de rotas: `/gestor/agenda` = visualização/status manual | ✅ CONFORME | Seção 3 e notas das cenas: capacidades fora da rota gestora explicitamente excluídas |
| Escopo NS-002: sem telas de pagamento | N/A | Escopo NS-001 não inclui pagamento — não aplicável |
| Padrão de vídeo: 1080×1920, 30fps, sem áudio, com suporte a legendas e .srt | ✅ CONFORME | Formato definido no cabeçalho e confirmado pelo WORKFLOW.md |
| Sem promessas de redução de faltas / aumento de faturamento | ✅ CONFORME | Seção 1: "não prometer... redução de faltas, prevenção de no-show, aumento de ocupação, aumento de faturamento" |

**Resultado NS-001: CONFORME com todos os guardrails. Nenhuma correção necessária.**

#### NS-002 — Agendamento online no Marca Salão
**Versão revisada:** 0.1 — data 2026-11-16 — Status: rascunho

| Guardrail | Status | Evidência no roteiro |
|-----------|--------|---------------------|
| Sem promessas de automação (WhatsApp/SMS/e-mail, lembretes, confirmações automáticas) | ✅ CONFORME | Seção 1: "Não prometer: pagamento como benefício, mensagens ou confirmações automáticas, lembretes..." |
| Separação de rotas: `/gestor/agenda` = visualização/status; `/booking/[salonId]` = horários | ✅ CONFORME | Roteiro identifica explicitamente cada rota por cena (cena 2 → `/booking/[salonId]`; cena 5 → `/gestor/agenda`) |
| Escopo NS-002: sem telas ou fluxos de pagamento simulado | ✅ CONFORME | Cena 3 — nota: "Sem tela de pagamento. Não citar pagamento, não exibir cobrança" |
| Padrão de vídeo: 1080×1920, 30fps, sem áudio, com suporte a legendas e .srt | ✅ CONFORME | Seção 4: "vertical 9:16, 1080 × 1920, 30 fps, sem áudio. Legendas visíveis e sincronizadas; .srt e texto de narração separado" |
| Sem promessas de redução de faltas / aumento de faturamento | ✅ CONFORME | Seção 1 e briefing: "Não prometer... redução de faltas, ocupação garantida ou aumento de faturamento" |

**Resultado NS-002: CONFORME com todos os guardrails. Nenhuma correção necessária.**

#### Stories-001 (NS-002)
| Guardrail | Status | Nota |
|-----------|--------|------|
| Sem pagamento simulado | ✅ CONFORME | "Sem tela de pagamento" na Story 2 |
| Sem automação de contato | ✅ CONFORME | Sem menção a mensagens automáticas |
| Separação de rotas | ✅ CONFORME | Story 3 referencia `/gestor/agenda` explicitamente |
| Sem botão clicável desenhado | ✅ CONFORME | Nota explícita: "Nenhum dos dois faz parte do texto principal" |

**Pendência registrada nos roteiros (válida, não é desvio de guardrail):**
- Resolver divergência "Marca Salão" vs "Meu Salão" na interface **antes das capturas finais**. Isso é uma pendência de execução, não de conformidade editorial.

#### Saneamento de materiais legados (04-legendas/)
Além dos roteiros oficiais NS-001 e NS-002, foram auditados e saneados materiais legados de teste em `04-legendas/`:
- `04-legendas/roteiro_demo_link_agendamento.md` e `.srt`: removida menção a "automatizado 24 horas por dia", substituída por agendamento online simples e rápido; padronizado para "Marca Salão".
- `04-legendas/roteiro_enviar_link.md` e `.srt`: removida promessa de "agenda atualiza no automático 24 horas por dia" e "Automatize seu salão", substituída por "o atendimento aparece direto na agenda do salão".

---

### Tarefa 5 — `contexto_projeto.md`

**Este arquivo.** Criado em `contexto_projeto.md` na raiz do projeto como devlog permanente e acumulativo.

---

## 3. Worktrees de outros agentes (preservadas)

| Worktree | Branch | HEAD | Ação |
|----------|--------|------|------|
| `.workspace/worktrees/prova-campanha-conclusao` | `wip/prova-campanha-conclusao-worktree` | `c4fda91` | Preservada — não tocar |
| `.workspace/worktrees/studio-package-verify2` | `codex/studio-delivery-package-verification` | `4f10431` | Preservada — não tocar |

---

## 4. Arquivos criados/modificados nesta sessão

| Arquivo | Ação | Branch |
|---------|------|--------|
| `docs/rastreio-utm.md` | Criado | `codex/fase1-conformidade-editorial` |
| `docs/fixtures/fixture-editorial-marca-salao.json` | Criado | `codex/fase1-conformidade-editorial` |
| `contexto_projeto.md` | Criado / Atualizado | `codex/fase1-conformidade-editorial` |
| `04-legendas/instagram_captions.md` | Modificado (padronização de marca) | `codex/fase1-conformidade-editorial` |
| `04-legendas/legendas_cards.md` | Modificado (padronização de marca) | `codex/fase1-conformidade-editorial` |
| `04-legendas/roteiro_0802_cadastro_profissional.md` | Modificado (padronização de marca) | `codex/fase1-conformidade-editorial` |
| `04-legendas/roteiro_demo_link_agendamento.md` | Modificado (marca + guardrails) | `codex/fase1-conformidade-editorial` |
| `04-legendas/roteiro_demo_link_agendamento.srt` | Modificado (marca + guardrails) | `codex/fase1-conformidade-editorial` |
| `04-legendas/roteiro_enviar_link.md` | Modificado (guardrails) | `codex/fase1-conformidade-editorial` |
| `04-legendas/roteiro_enviar_link.srt` | Modificado (guardrails) | `codex/fase1-conformidade-editorial` |

---

## 5. Pendências humanas (decisão do titular)

1. **Divergência "Meu Salão" vs "Marca Salão" na interface:** confirmar, antes das capturas finais, qual nome será exibido na interface do produto (Salao02) ou se um overlay de texto cobrirá o nome exibido.
2. **Rastreio UTM:** definir ferramenta de analytics e preencher as seções PENDENTE em `docs/rastreio-utm.md` antes da primeira publicação com link rastreado.
3. **Fixture editorial:** validar nomes, preços e dados com o titular antes de usar em capturas.
4. **Roteiros NS-001 e NS-002:** ambos aguardam aprovação editorial do titular para autorizar capturas, gravação e publicação.
5. **Link da bio do @marcasalao:** confirmar link externo real cadastrado antes de usar "link na bio" em qualquer legenda.

---

## 6. Próximos passos (Fase 2 — a definir com o titular)

- Capturar telas com a fixture editorial (somente após aprovação das pendências acima)
- Criar SRT e narração em `04-legendas/` para os roteiros NS-001 e NS-002
- Renderizar vídeos no padrão 1080×1920, 30fps, sem áudio
- Validar entrega com `ffprobe` (ausência de faixa de áudio)
- Submeter PR para revisão do titular

---

## 7. Histórico de sessões

### 2026-11-18 — codex/fase1-conformidade-editorial

- **Executor:** Agente de marketing (Antigravity/codex)
- **Branch:** `codex/fase1-conformidade-editorial` a partir de `main` (`584f842`)
- **Raiz:** `D:/MEGA/Marketing/marcasalao-marketing`
- **Concluído:**
  - Auditoria de identidade visual: 0 substituições automáticas; divergência documentada como pendência de execução
  - Fixture editorial: criada em `docs/fixtures/fixture-editorial-marca-salao.json`
  - Rastreio UTM: criado em `docs/rastreio-utm.md`
  - Conformidade NS-001: CONFORME — 5/5 guardrails atendidos
  - Conformidade NS-002: CONFORME — 5/5 guardrails atendidos
  - `contexto_projeto.md`: este arquivo
- **Worktrees preservadas:** `prova-campanha-conclusao`, `studio-package-verify2`
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

---

### 2026-11-18 — codex/etapa1-piloto-ns002 (Etapa 1 — Piloto Real Ponta a Ponta da Campanha NS-002)

- **Executor:** Engenheiro de Software Sênior / Arquiteto de Automação de Vídeo (Antigravity)
- **Branch:** `codex/etapa1-piloto-ns002` a partir de `codex/fase1-conformidade-editorial` (`43fcac8`)
- **Raiz:** `D:/MEGA/Marketing/marcasalao-marketing`
- **Resumo:** Piloto completo e parametrizado da campanha `NS-002` (`Agendamento online no Marca Salão`), com separação explícita de superfícies (`/booking/marca-salao-modelo` vs `/gestor/agenda`), cabeçalho de marca `MARCA SALAO` cobrindo referências legadas a "Meu Salão", ausência total de pagamento simulado e de promessas automáticas, exportação transacional FFmpeg `1080×1920 @ 30 fps` sem faixa de áudio (`-an`), storyboard visual `2×2` e testes automatizados.

#### Arquivos criados e modificados

| Arquivo | Ação | Finalidade |
| --- | --- | --- |
| `04-legendas/ns002_roteiro_001.srt` | Criado | Legendas sincronizadas (6 blocos, 30,0 s, UTF-8 LF, validado por `srt_validate.py`) |
| `04-legendas/ns002_roteiro_001_narracao.txt` | Criado | Roteiro limpo por cena para locução humana externa (aderente aos guardrails) |
| `00-briefings/campanhas/NS-002/NS-002-H02-variacao-carga-cognitiva.md` | Criado | Variação opcional de hook `NS-002-H02` focada em redução de carga cognitiva (`NS-002-H01` preservado intacto) |
| `02-hooks/campanhas/NS-002/hooks.md` | Modificado | Incorporada formulação de redução de carga cognitiva em `NS-002-H02`; `NS-002-H01` intacto |
| `02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json` | Criado | Configuração desacoplada de marca/paleta/cenas (`preset: "saas-demo"`, `audioPolicy.enabled: false`), base direta para `brand-kit.json` na Etapa 2 |
| `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001.srt` | Criado | Cópia sincronizada no pacote de entrega |
| `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001_narracao.txt` | Criado | Cópia sincronizada no pacote de entrega |
| `02-reels-shorts/ns002-piloto-01/preview-storyboard-ns002.png` | Criado | Storyboard visual 2×2 (1080×1920) com frames extraídos nos segundos `2.0`, `8.0`, `16.0` e `24.0` |
| `02-reels-shorts/ns002-piloto-01/manifest.json` | Criado | Manifesto de integridade SHA-256, bytes, comando reproduzível e medição FFprobe |
| `02-reels-shorts/ns002-piloto-01/README.md` | Criado | Documentação do pacote piloto e instruções de reprodução |
| `02-reels-shorts/ns002-piloto-01/ns002-piloto-01.mp4` | Gerado localmente | MP4 vertical 1080×1920@30fps sem áudio (`-an`), legendas queimadas (cópia em `.workspace/archives/ns002-piloto-01/ns002-piloto-01.mp4`; ignorado no Git por `*.mp4` em `.gitignore`) |
| `tools/ns002_pilot.py` | Criado | Construtor parametrizado (`config` + `fixture-editorial` + FFmpeg + storyboard + manifesto SHA-256 + promoção transacional) |
| `tools/tests/test_ns002_pilot.py` | Criado | Regressões de SRT, sync de pacote, estrutura pronta para `brand-kit.json`, bloqueio de guardrails, integridade de manifesto e contenção de raiz |
| `contexto_projeto.md` | Atualizado | Registro da Etapa 1 |

#### Auditoria técnica literal (`ffprobe`)

Comando executado:
```text
.workspace/tools/ffmpeg/ffprobe.exe -v error -show_streams -show_format -of json 02-reels-shorts/ns002-piloto-01/ns002-piloto-01.mp4
```

Resultado observado:
```json
{
  "streams": [
    {
      "index": 0,
      "codec_name": "h264",
      "profile": "High",
      "codec_type": "video",
      "width": 1080,
      "height": 1920,
      "sample_aspect_ratio": "1:1",
      "display_aspect_ratio": "9:16",
      "pix_fmt": "yuv420p",
      "r_frame_rate": "30/1",
      "avg_frame_rate": "30/1",
      "duration": "30.000000",
      "bit_rate": "115174",
      "nb_frames": "900"
    }
  ],
  "format": {
    "filename": "02-reels-shorts/ns002-piloto-01/ns002-piloto-01.mp4",
    "nb_streams": 1,
    "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
    "duration": "30.000000",
    "size": "443550",
    "bit_rate": "118280"
  }
}
```
- **Confirmado:** `1` stream de vídeo (`h264`, `yuv420p`, `1080x1920`, `30/1` fps, `30.000000 s`) e **0 streams de áudio**.

#### Hashes SHA-256 do pacote `02-reels-shorts/ns002-piloto-01/`

| Artefato | Tamanho (bytes) | SHA-256 |
| --- | ---: | --- |
| `02-reels-shorts/ns002-piloto-01/ns002-piloto-01.mp4` | 443 550 | `ec340c106c56592a8f026089ab1b0a8582ea8b464cc8f0dac6fc3ddc305cda4b` |
| `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001.srt` | 496 | `2a1e42bcf01294844bc7768e6d4965bf10f7cddd06479c06fa6491a5e433e8f5` |
| `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001_narracao.txt` | 1 378 | `f3a322eade93a16e295efb7eaa1cd25c7408bc28b0056a57ca3d38a8bf5f44c6` |
| `02-reels-shorts/ns002-piloto-01/preview-storyboard-ns002.png` | 641 956 | `d74a5f4cc27fb378af07a700eca81da7aeed8820bdd64f03a88bf06d1b32ebf9` |
| `docs/fixtures/fixture-editorial-marca-salao.json` (insumo referenciado) | — | `1cb32a7b34d0d7dc8619d21f1a9ddafe14c8614e541665af9dc207b81f432efa` |

#### Storyboard visual para revisão humana

- Arquivo inspecionado: `02-reels-shorts/ns002-piloto-01/preview-storyboard-ns002.png` (grade 2×2 nos segundos `2.0`, `8.0`, `16.0` e `24.0`).
- Verificação visual: cabeçalho `MARCA SALAO` explícito em todas as cenas (sem exposição de `Meu Salão`, `E2E` ou `A pagar`), dados da fixture (`Corte Feminino R$ 85,00`, `Camila Rocha`, `Rafael Mendes`, `Juliana Costa`, `Lucas Alves`, `Ana Beatriz Souza`), separação `/booking/marca-salao-modelo` vs `/gestor/agenda` e legendas queimadas legíveis na faixa segura inferior sem sobrepor os cartões.

#### Testes executados após último ajuste

- `test_srt_validate.py` + `test_build_video.py` + `test_r002_pilot.py` + `test_ns002_pilot.py`: **26/26 OK** (`21.007s`).
- `test_delivery_verify.py`: **16/16 OK** (`0.260s`).
- `test_campaign_proof.py`: **5/5 OK** (`14.726s`).

#### Status das pendências humanas e recomendações técnicas para a Etapa 2 (`tenants/` + `brand-kit.json`)

- **Pendências humanas mantidas:** aprovação editorial do titular sobre o storyboard/texto de narração `NS-002` antes de publicação, preenchimento do link de analytics em `docs/rastreio-utm.md`, confirmação do link da bio do `@marcasalao` e definição sobre eventual captura real adicional no Salao02 já atualizado para "Marca Salão". A questão visual `"Meu Salão"` no piloto técnico ficou mitigada pelo `headerOverlay` (`MARCA SALAO`).
- **Recomendações técnicas para a Etapa 2 (Refatoração Multi-Tenant):**
  1. Extrair o objeto `brand` + `subtitleStyle` de `02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json` para `tenants/<tenantId>/brand-kit.json` (iniciando por `tenants/marca-salao/brand-kit.json` e `tenants/multitrack-hub/brand-kit.json`), acompanhado de um `brand-kit.schema.json`.
  2. Organizar fixtures editoriais e campanhas por tenant (`tenants/<tenantId>/fixtures/`), passando `brandKitRef` e `fixtureRef` no config da campanha.
  3. Evoluir `tools/ns002_pilot.py` para um runner genérico multi-tenant por `preset` (ex.: `tools/preset_runner.py` com suporte inicial a `preset: "saas-demo"`), resolvendo dinamicamente paleta, monograma, domínio, `headerOverlay` e estilo de legenda sem duplicar código de renderização ou validação de guardrails.
- **Worktrees preservadas:** `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2`.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

---

### 2026-11-18 — codex/etapa2-agente1-arquitetura-tenants (Etapa 2 — Agente 1: Arquitetura Multi-Tenant e Contratos de Marca)

- **Executor:** Arquiteto de Software Sênior (Antigravity — Agente 1)
- **Branch:** `codex/etapa2-agente1-arquitetura-tenants` a partir de `codex/etapa1-piloto-ns002` (`da7d565`)
- **Raiz:** `D:/MEGA/Marketing/marcasalao-marketing`
- **Resumo:** Implementação dos contratos formais JSON Schema em `schemas/`, estrutura multi-tenant `tenants/` para três projetos (`marca-salao`, `meu-salao`, `multitrack-hub`), fixtures editoriais isoladas por tenant, validador em biblioteca padrão Python (`tools/tenant_validator.py`) e suíte de regressão de contratos (`tools/tests/test_tenant_contracts.py`), mantendo `tools/ns002_pilot.py`, `tools/r002/agenda-ficticia.pilot.json`, `docs/fixtures/fixture-editorial-marca-salao.json` e `02-reels-shorts/ns002-piloto-01/` intactos.

#### Arquivos criados e modificados

| Arquivo | Ação | Finalidade |
| --- | --- | --- |
| `schemas/brand-kit.schema.json` | Criado | Contrato JSON Schema de identidade visual, paleta hex+rgb, tipografia, `headerOverlay`, `subtitleStyle`, `defaultPreset` e `utmDefaults` |
| `schemas/guardrails.schema.json` | Criado | Contrato JSON Schema de `forbiddenClaims`, `forbiddenUiElements`, `routeRules` e `audioPolicy` por tenant |
| `tenants/marca-salao/brand-kit.json` | Criado | Brand kit oficial do Marca Salão extraído 1:1 de `02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json` (`defaultPreset: "saas-demo"`) |
| `tenants/marca-salao/guardrails.json` | Criado | Regras estritas da Fase 1/Etapa 1 (sem WhatsApp/SMS/lembretes/faltas/faturamento/pagamento/Meu Salão, rotas separadas, `allowAudioTrack: false`) |
| `tenants/marca-salao/fixtures/fixture-editorial-marca-salao.json` | Criado | Cópia sincronizada (SHA-256 `1cb32a7b34d0d7dc8619d21f1a9ddafe14c8614e541665af9dc207b81f432efa`) da fixture editorial original |
| `tenants/marca-salao/campaigns/README.md` | Criado | Índice de campanhas do tenant `marca-salao` |
| `tenants/meu-salao/brand-kit.json` | Criado | Brand kit white-label do Meu Salão (`monogram: "MS"`, `headerOverlay.label: "MEU SALAO"`, `defaultPreset: "saas-demo"`) |
| `tenants/meu-salao/guardrails.json` | Criado | Regras de veracidade e separação `/booking/[salonId]` vs `/gestor/agenda` (`allowAudioTrack: false`, permitindo marca própria `"Meu Salão"`) |
| `tenants/meu-salao/fixtures/fixture-editorial-meu-salao.json` | Criado | Fixture fictícia plausível para Meu Salão (4 profissionais, 5 serviços BRL, agenda sem checkout/E2E) |
| `tenants/meu-salao/campaigns/README.md` | Criado | Índice de campanhas white-label `meu-salao` |
| `tenants/multitrack-hub/brand-kit.json` | Criado | Brand kit dark/tech do Multitrack Hub (`monogram: "MH"`, `headerOverlay.label: "MULTITRACK HUB"`, `defaultPreset: "shorts-completo"`) |
| `tenants/multitrack-hub/guardrails.json` | Criado | Regras multi-nicho Shorts (`allowAudioTrack: true`, `requireExternalNarration: false`, `requireSrt: true`, sem WhatsApp/telefone comercial, rotas `/` e `/rateios`) |
| `tenants/multitrack-hub/fixtures/fixture-editorial-multitrack-hub.json` | Criado | Fixture fictícia de catálogo multitrack (3 projetos, BPM, tonalidade, stems `Click/Guide/...`, 2 rateios) |
| `tenants/multitrack-hub/campaigns/README.md` | Criado | Índice de campanhas `multitrack-hub` |
| `tools/tenant_validator.py` | Criado | Validador stdlib de schemas, fixtures e guardrails por tenant + CLI (`--all` / `--tenant`) |
| `tools/tests/test_tenant_contracts.py` | Criado | 7 testes de contrato (positivos, negativos, consistência com piloto NS-002 e CLI) |
| `contexto_projeto.md` | Atualizado | Registro da Etapa 2 — Agente 1 |

#### Resumo estrutural dos 3 `brand-kit.json`

| `tenantId` | `brandName` | `monogram` | `defaultPreset` | `palette` (hex principal) | `allowAudioTrack` | `utmDefaults` (`source/medium/prefix`) |
| --- | --- | --- | --- | --- | --- | --- |
| `marca-salao` | Marca Salão | `MS` | `saas-demo` | `#F5C107` / `#4F8CFF` / `#28B463` / `#121620` | `false` (`-an`) | `instagram` / `reels` / `ns` |
| `meu-salao` | Meu Salão | `MS` | `saas-demo` | `#10B981` / `#3B82F6` / `#F59E0B` / `#0F172A` | `false` (`-an`) | `instagram` / `reels` / `ms` |
| `multitrack-hub` | Multitrack Hub | `MH` | `shorts-completo` | `#06B6D4` / `#8B5CF6` / `#22C55E` / `#090D16` | `true` | `youtube` / `shorts` / `mth` |

#### Validações e Testes Executados

- **CLI `tenant_validator`:** `python tools/tenant_validator.py --all --json` — **OK (`0` erros)** para `marca-salao`, `meu-salao` e `multitrack-hub`.
- **Suíte consolidada (Etapa 1 + Etapa 2 Agente 1 + CI núcleo Python):**
  - `test_tenant_contracts.py` (7) + `test_ns002_pilot.py` (5) + `test_srt_validate.py` (10) + `test_build_video.py` (6) + `test_r002_pilot.py` (5) + `test_delivery_verify.py` (16) + `test_campaign_proof.py` (5): **54/54 testes aprovados em `44.901s` (`OK`)**.

#### Pontos de Entrada e Instruções Técnicas para o Agente 2 (`tools/preset_runner.py`)

1. **Importação direta do validador e carregador de tenant (`tools/tenant_validator.py`):**
   - `ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)` devolve um dicionário validado com:
     - `ctx["brandKit"]` (inclui `palette.rgb` compatível 1:1 com os helpers de desenho PNG de `tools/ns002_pilot.py`, `displayTitle`, `monogram`, `tagline`, `domain`, `headerOverlay`, `subtitleStyle`, `defaultPreset`, `utmDefaults`).
     - `ctx["guardrails"]` (inclui `audioPolicy.allowAudioTrack`, `requireSrt`, `requireExternalNarration`, `forbiddenClaims`, `forbiddenUiElements`, `routeRules`).
     - `ctx["fixture"]` e `ctx["fixturePath"]`.
   - `tenant_validator.validate_text_against_guardrails(text, ctx["guardrails"], check_ui_elements=True)` deve ser aplicado sobre captions, SRT e roteiro de narração antes do render FFmpeg.
   - `tenant_validator.load_schema("brand-kit.schema.json", root)` e `validate_brand_kit(...)` / `validate_guardrails_contract(...)` permanecem disponíveis caso um preset receba overrides locais.
2. **Contrato esperado em `tools/preset_runner.py`:**
   - Respeitar `ctx["guardrails"]["audioPolicy"]`: forçar `-an` e recusar trilha sonora sempre que `allowAudioTrack == False` (`marca-salao` e `meu-salao`), preservando `tools/ns002_pilot.py` e todos os testes existentes sem quebrar retrocompatibilidade.
   - Implementar roteamento por `preset` (`"saas-demo"` reutilizando o layout multi-superfície de `ns002_pilot.py` com parâmetros de `ctx["brandKit"]` + `ctx["fixture"]`, e `"shorts-completo"` para o fluxo de `multitrack-hub`).
- **Worktrees preservadas:** `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2`.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

---

### 2026-11-18 — codex/etapa2-agente2-preset-runner (Etapa 2 — Agente 2: Motor Genérico Multi-Tenant)

- **Executor:** Engenheiro de Software Sênior / Arquiteto de Motores de Vídeo Programático
- **Branch:** `codex/etapa2-agente2-preset-runner` a partir de `codex/etapa2-agente1-arquitetura-tenants`
- **Raiz:** `D:/MEGA/Marketing/marcasalao-marketing`
- **Resumo:** Implementação do motor genérico multi-tenant `tools/preset_runner.py` com suporte a presets de vídeo e áudio, interface programática (`run_preset_pipeline(...)`) e CLI completa, respeitando guardrails por tenant, saída transacional padronizada e suíte de testes de renderização real com FFmpeg. Retrocompatibilidade total mantida: `tools/ns002_pilot.py`, `tools/r002/agenda-ficticia.pilot.json`, `02-reels-shorts/ns002-piloto-01/` e todos os 54 testes anteriores seguem funcionando sem quebras.

#### Arquivos criados

| Arquivo | Ação | Finalidade |
| --- | --- | --- |
| `tools/preset_runner.py` | Criado | Motor genérico multi-tenant: `run_preset_pipeline(...)` + CLI (`--tenant --config --output-dir [--audio]`), presets `saas-demo` e `shorts-completo`, validação de tenant via `tenant_validator.load_and_validate_tenant(...)`, auditoria de textos via `validate_text_against_guardrails(...)`, força `-an` quando `allowAudioTrack == false`, geração de áudio AAC (`anullsrc` ou arquivo externo via `--audio`) quando permitido, saída atômica (`<slug>.mp4`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png` 2×2, `manifest.json` com SHA-256 + ffprobe) e cópia do MP4 em `.workspace/archives/<slug>/`. |
| `tools/tests/test_preset_runner.py` | Criado | 7 testes de renderização real com FFmpeg: saas-demo (marca-salao) 0 áudio, shorts-completo (multitrack-hub) 1 áudio AAC, áudio externo mixado, bloqueio de guardrails (frase proibida e `--audio` recusado), integridade de hashes SHA-256 do manifesto e storyboard, retrocompatibilidade dos tenants. |
| `tenants/marca-salao/campaigns/camp-saas-demo-marca-salao-001.json` | Criado | Config de campanha `saas-demo` para marca-salao (6 cenas, 30s, fluxo público `/booking/marca-salao-modelo` separado do `/gestor/agenda`). |
| `tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json` | Criado | Config de campanha `shorts-completo` para multitrack-hub (5 cenas, 30s, catálogo de projetos, métricas, rateios, áudio habilitado). |
| `contexto_projeto.md` | Modificado | Seção 1 (estado atual) e nova entrada na Seção 7 (este registro). |

#### Exemplos de comando CLI

```text
# saas-demo (marca-salao): vídeo sem áudio (-an), SRT + narração externa .txt
python tools/preset_runner.py --tenant marca-salao \
  --config tenants/marca-salao/campaigns/camp-saas-demo-marca-salao-001.json \
  --output-dir .workspace/tmp/entrega/marca-salao-saas-demo

# shorts-completo (multitrack-hub): áudio limpo gerado automaticamente (anullsrc -> AAC 128k)
python tools/preset_runner.py --tenant multitrack-hub \
  --config tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json \
  --output-dir .workspace/tmp/entrega/multitrack-hub-shorts

# shorts-completo com trilha externa fornecida via --audio
python tools/preset_runner.py --tenant multitrack-hub \
  --config tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json \
  --output-dir .workspace/tmp/entrega/multitrack-hub-audio \
  --audio .workspace/tmp/trilha-externa.wav

# Uso programático (ponto de entrada para o Agente 3):
#   from tools import preset_runner
#   manifest = preset_runner.run_preset_pipeline(
#       "marca-salao", "tenants/marca-salao/campaigns/...json",
#       ".workspace/tmp/entrega/...", audio_path=None, root=REPO_ROOT)
```

#### Resultado literal do ffprobe (comprova a diferença de streams de áudio)

Comando:
```text
ffprobe -v error -show_streams -show_format -of json <video.mp4>
```

`marca-salao` / `saas-demo` (`allowAudioTrack: false`, forçado `-an`):
```json
{"index": 0, "codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "avg_frame_rate": "30/1", "pix_fmt": "yuv420p"}
FORMAT: nb_streams=1, duration=30.000000
```
→ **1 stream de vídeo (h264, 1080×1920, 30 fps) e 0 streams de áudio.**

`multitrack-hub` / `shorts-completo` (`allowAudioTrack: true`, áudio automático):
```json
{"index": 0, "codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "avg_frame_rate": "30/1", "pix_fmt": "yuv420p"}
{"index": 1, "codec_type": "audio", "codec_name": "aac"}
FORMAT: nb_streams=2, duration=30.000000
```
→ **1 stream de vídeo (h264, 1080×1920, 30 fps) + 1 stream de áudio (AAC).**

#### Testes executados

- Suíte consolidada completa (54 testes existentes + 7 novos de `test_preset_runner.py`): **61/61 aprovados em 72,5 s (`OK`)**.
- `test_tenant_contracts.py` (7) + `test_srt_validate.py` (10) + `test_build_video.py` (6) + `test_r002_pilot.py` (5) + `test_ns002_pilot.py` (5) + `test_delivery_verify.py` (16) + `test_campaign_proof.py` (5) + `test_preset_runner.py` (7).

#### Pontos de entrada e instruções para o Agente 3

1. **Geração das campanhas de escala (`meu-salao` e `multitrack-hub`):** chamar `tools/preset_runner.run_preset_pipeline(tenant_id, config_path, output_dir, audio_path=None, root=REPO_ROOT)` para cada config de campanha dos tenants, respeitando `defaultPreset` de cada `brand-kit.json` (`meu-salao` → `saas-demo` com `-an`; `multitrack-hub` → `shorts-completo` com áudio). A criação em lote e a integração nos workflows do GitHub Actions ficam a cargo do Agente 3.
2. **Interface programática:** `run_preset_pipeline(...)` devolve o `manifest.json` como dicionário; o CLI expõe `--tenant`, `--config`, `--output-dir` e `--audio` (opcional).
3. **Guardrails obrigatórios no Agente 3:** antes de qualquer render, validar o tenant via `tenant_validator.load_and_validate_tenant(..., strict=True)` e auditar textos com `tenant_validator.validate_text_against_guardrails(..., check_ui_elements=True)`; nunca passar `--audio` para tenants com `allowAudioTrack: false`.
4. **Saída:** `<slug>.mp4`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png` e `manifest.json` no `output-dir`; cópia do MP4 em `.workspace/archives/<slug>/`.
5. **Worktrees preservadas:** `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2` não foram tocadas.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

### Sessão 2026-11-18 — Etapa 2 (Agente 3): Prova de Escala Multi-Tenant, Orquestrador em Lote e CI

- **Branch de trabalho:** `codex/etapa2-agente3-escala-ci` (criada a partir de `codex/etapa2-agente2-preset-runner`).
- **Status:** Etapa 2 concluída — Plataforma Multi-Tenant de Vídeo Programático 100% operacional com prova de escala real entre `marca-salao`, `meu-salao` (white-label) e `multitrack-hub`.

#### Entregáveis criados e atualizados

1. **Prova white-label (`tenants/meu-salao/campaigns/camp-saas-demo-meu-salao-001.json`):** campanha de 6 cenas (`30.0s`) no preset `saas-demo`, reutilizando a arquitetura do `marca-salao` com 100% da identidade visual (`MEU SALAO`, paleta esmeralda/azul) e dados próprios da fixture `fixture-editorial-meu-salao.json` (`Patrícia Gomes`, `serv-ms-001`, `prof-ms-001`, `atend-ms-001`, separação `/booking/meu-salao-modelo` vs `/gestor/agenda`).
2. **Orquestrador em lote (`tools/factory_cli.py`):**
   - `python tools/factory_cli.py list [--tenant <tenantId>] [--json]` — lista tenants válidos, metadados do `brand-kit.json`, política de áudio e campanhas descobertas em `tenants/<tenantId>/campaigns/*.json`.
   - `python tools/factory_cli.py render --tenant <tenantId> [--campaign <slug>] [--json]` e `render --all [--json]` — valida contratos com `tenant_validator`, aciona `tools/preset_runner.run_preset_pipeline(...)` (redirecionando logs internos do FFmpeg para `stderr` para preservar saída `--json` limpa), grava pacotes padronizados em `02-reels-shorts/deliveries/<tenantId>/<slug>/` (com cópias `.mp4` em `.workspace/archives/<slug>/`) e consolida o relatório `02-reels-shorts/deliveries/factory-report.json`.
3. **Suíte de testes da fábrica (`tools/tests/test_factory_cli.py`):** 4 testes cobrindo `list`, `render` filtrado por tenant/campanha com validação real por `ffprobe`, integridade dos artefatos versionados + `factory-report.json` e códigos de saída de erro.
4. **Guia de onboarding (`docs/guia-novo-nicho.md`):** passo a passo em 5 etapas (<10 min) para cadastrar e renderizar um novo tenant sem alterar código Python ou FFmpeg.
5. **Integração no CI (`.github/workflows/local-render-validation.yml`):** adicionados os caminhos `schemas/**`, `tenants/**` e `02-reels-shorts/deliveries/**` aos triggers `pull_request`/`push` e o passo `Validar contratos multi-tenant e suites da fabrica (Etapa 2)` executando `python tools/tenant_validator.py --all --json`, `python tools/factory_cli.py list --json` e `unittest` de `test_tenant_contracts.py`, `test_preset_runner.py` e `test_factory_cli.py`.

#### Auditoria comparativa das 3 entregas reais (`render --all --json` + `ffprobe`)

| Tenant | Campanha (`slug`) | Preset | `allowAudioTrack` | Formato / Streams (`ffprobe`) | MP4 local preservado (`.workspace/archives/`) — Bytes & SHA-256 | Artefatos versionados (`02-reels-shorts/deliveries/<tenant>/<slug>/`) — SHA-256 |
|---|---|---|---|---|---|---|
| `marca-salao` | `camp-saas-demo-marca-salao-001` | `saas-demo` | `false` (`-an`) | `1080x1920`, `30/1` fps, `h264`, `yuv420p`, `30.000000s`, `nb_streams: 1` (**0 áudio**) | `.workspace/archives/camp-saas-demo-marca-salao-001/camp-saas-demo-marca-salao-001.mp4` (`445686` bytes, `fb4dd43f3cf5f7d30a3a68b6d4c8874ec12d7cc825b7bef05f6e6b1e6c065791`) | SRT `2a1e42bcf01294844bc7768e6d4965bf10f7cddd06479c06fa6491a5e433e8f5` (`496` B); Narração `5399ea58058cec2551f8f9843ed1c1196d337400bcbe1d561162014cba4bc36d` (`906` B); Storyboard `b79ca9193951aacc5820b6810896e7706b5cc9b337e966a8144eef6b002ee537` (`643164` B) |
| `meu-salao` | `camp-saas-demo-meu-salao-001` | `saas-demo` | `false` (`-an`) | `1080x1920`, `30/1` fps, `h264`, `yuv420p`, `30.000000s`, `nb_streams: 1` (**0 áudio**) | `.workspace/archives/camp-saas-demo-meu-salao-001/camp-saas-demo-meu-salao-001.mp4` (`418019` bytes, `634e8e3d57d98931d6fc32e094ecaf7754fb6b4931df746325bf6c74fb207ca3`) | SRT `8c59c014218eaf41476d2a76403374bf839f7ace2fc1f07257f1c74d49ed8dcc` (`492` B); Narração `304d4a93157f8ef09fc094417f21d657a2c0b0567a8c701b41bc2fa8265d60a7` (`898` B); Storyboard `dcbda5440c0d9023655697feb525b64dee92f2eeea231dd0388c63cd9aab1a87` (`620208` B) |
| `multitrack-hub` | `camp-shorts-completo-multitrack-001` | `shorts-completo` | `true` (`aac`) | `1080x1920`, `30/1` fps, `h264`, `yuv420p`, `30.000000s`, `nb_streams: 2` (**1 áudio `aac` `44100 Hz` `stereo`**) | `.workspace/archives/camp-shorts-completo-multitrack-001/camp-shorts-completo-multitrack-001.mp4` (`352348` bytes, `39392faa1d92a7b42fe933c9344184af00f3d226e1d86af2555d2bac148b1197`) | SRT `eb957ce54aefca108d9236405c1a4758cf70a23f68276b39e9605caa83ae6582` (`444` B); Narração `71afbf1558edf21f66553d6aba60c34517344f86738d590e2afcbc9fb04e16f1` (`743` B); Storyboard `82fcc1cfa9178d52f7ccfaff82caddf0e69fae60c0ed02a72bf13e6988ef4dbf` (`479092` B) |

- **Inspeção visual realizada:** storyboards `preview-storyboard.png` das 3 campanhas confirmam identidades visuais distintas (`MARCA SALAO` amarelo/azul, `MEU SALAO` esmeralda/azul, `MULTITRACK HUB` ciano/roxo), legendas queimadas legíveis e separação de superfícies preservada.

#### Validações e testes executados após o último ajuste de código (`tools/factory_cli.py`)

- `python tools/tenant_validator.py --all --json` → `ok: true` nos 3 tenants (`marca-salao`, `meu-salao`, `multitrack-hub`).
- `python tools/factory_cli.py list --json` → `ok: true`, `totalTenants: 3`, `totalCampaigns: 3`.
- Suíte de fábrica (`test_factory_cli.py`): **4/4 aprovados em 13,260 s (`OK`)**.
- Suíte consolidada completa (9 módulos — 61 testes anteriores + 4 novos de `test_factory_cli.py`): **65/65 aprovados em 88,581 s (`OK`)**:
  - `test_tenant_contracts.py` (7) + `test_preset_runner.py` (7) + `test_factory_cli.py` (4) + `test_ns002_pilot.py` (5) + `test_srt_validate.py` (10) + `test_build_video.py` (6) + `test_r002_pilot.py` (5) + `test_delivery_verify.py` (16) + `test_campaign_proof.py` (5).
- Retrocompatibilidade intacta: `tools/ns002_pilot.py`, `tools/r002/agenda-ficticia.pilot.json`, `docs/fixtures/fixture-editorial-marca-salao.json`, `02-reels-shorts/ns002-piloto-01/` e worktrees `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2` preservados sem alteração.

#### Checklist final — Revisão humana, merge e publicação manual

1. **Revisão visual:** inspecionar os storyboards em `02-reels-shorts/deliveries/<tenant>/<slug>/preview-storyboard.png` e assistir localmente os MP4 preservados em `.workspace/archives/<slug>/<slug>.mp4`.
2. **Locução humana externa (tenants `-an`):** para `marca-salao` e `meu-salao`, utilizar os arquivos `*_narracao.txt` e `*.srt` para gravação externa caso deseje adicionar voz fora da fábrica.
3. **Revisão de PR e merge para `main`:** abrir/revisar PR consolidando a cadeia `codex/fase1-conformidade-editorial` → `codex/etapa1-piloto-ns002` → `codex/etapa2-agente1-arquitetura-tenants` → `codex/etapa2-agente2-preset-runner` → `codex/etapa2-agente3-escala-ci` na `main` somente após revisão e aprovação do titular.
4. **Publicação manual:** este fluxo gera entregas prontas e metadados UTM, sem agendar ou publicar automaticamente no Postiz; eventual publicação/rascunho nas redes depende de autorização explícita posterior.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

### Sessão 2026-11-18 — Consolidação e Merge Seguro na `main` (Fase 1 + Etapas 1 e 2)

- **Branch de preparação:** `codex/merge-prep-etapa2` (criada a partir de `main` em `584f8429442c5236db0dbfea5d0bbeca64ec180a`, com `--no-ff` de `codex/etapa2-agente3-escala-ci` / `fb586c7`).
- **Status:** Merge validado com zero conflitos, blindagem de EOL (`LF`) aplicada em `.gitattributes` e consolidação local concluída na `main` (sem `git push`, aguardando revisão final do titular).

#### Blindagem de quebra de linha (`LF`) detectada no dry-run

- Na primeira execução pós-merge em `codex/merge-prep-etapa2`, `core.autocrlf = true` no Windows converteu `.srt` e arquivos de pacote fora da cobertura original de `.gitattributes` para CRLF no checkout (`6e71c8ba...`), divergindo dos hashes SHA-256 gravados em LF (`2a1e42bc...`).
- **Correção aplicada em `.gitattributes`:** adicionadas regras `text eol=lf` para `02-reels-shorts/**/*.srt`, `02-reels-shorts/**/*_narracao.txt`, `02-reels-shorts/**/*.json`, `docs/fixtures/*.json`, `schemas/*.json` e `tenants/**/*.json`, seguidas de restauração do checkout em LF.
- Com `.gitattributes` atualizado, todos os hashes SHA-256 dos blobs no Git e dos arquivos no disco passaram a coincidir em qualquer estação Windows/Linux.

#### Resumo do diff consolidado (vs. base `584f842`)

- **Diff do conjunto funcional (`584f842..69f12b9`):** `60 files changed, 6558 insertions(+), 23 deletions(-)` (mais `.gitattributes` e esta atualização de `contexto_projeto.md` na consolidação final → `61 files changed`).
- **Nenhum `.mp4` rastreado no Git:** `git ls-files "*.mp4"` retornou vazio.

#### Validações pós-merge executadas em `codex/merge-prep-etapa2`

- `python tools/tenant_validator.py --all --json` → `ok: true` para `marca-salao`, `meu-salao` e `multitrack-hub`.
- `python tools/factory_cli.py list --json` → `ok: true`, `totalTenants: 3`, `totalCampaigns: 3`.
- `python tools/verify_egm_install.py` → `EGM verification OK: 8 skills, 10 agents, 5 standards, manifests and workspace wiring verified.`
- Suíte consolidada completa (9 módulos): **65/65 testes aprovados em `84.417s` (`OK`)** (`test_tenant_contracts`, `test_preset_runner`, `test_factory_cli`, `test_ns002_pilot`, `test_srt_validate`, `test_build_video`, `test_r002_pilot`, `test_delivery_verify`, `test_campaign_proof`).

#### Integridade de worktrees paralelas e arquivos locais

- **Worktrees preservadas sem alterações:**
  - `.workspace/worktrees/prova-campanha-conclusao` (`c4fda91b7dfa6e98e38ea286a2fedddfb55dc61a`, `wip/prova-campanha-conclusao-worktree`)
  - `.workspace/worktrees/studio-package-verify2` (`4f10431713580747c6f69bd7ed3c4be21e07b4bf`, `codex/studio-delivery-package-verification`)
- **Arquivos `.mp4` preservados em `.workspace/archives/`:**
  - `.workspace/archives/ns002-piloto-01/ns002-piloto-01.mp4` (`443550` bytes)
  - `.workspace/archives/camp-saas-demo-marca-salao-001/camp-saas-demo-marca-salao-001.mp4` (`445686` bytes)
  - `.workspace/archives/camp-saas-demo-meu-salao-001/camp-saas-demo-meu-salao-001.mp4` (`418019` bytes)
  - `.workspace/archives/camp-shorts-completo-multitrack-001/camp-shorts-completo-multitrack-001.mp4` (`352348` bytes)

#### Resumo pronto para Pull Request / Release Notes

```markdown
## Release Notes — Content Factory Multi-Tenant (Fase 1 + Etapas 1 e 2)

### O que muda nesta entrega
- **Conformidade Editorial (Fase 1):** auditoria de marca (`Marca Salão` vs `Meu Salão`), fixture editorial isolada em `docs/fixtures/fixture-editorial-marca-salao.json`, remoção de menções a automações não validadas e guia de rastreamento UTM (`docs/rastreio-utm.md`).
- **Piloto NS-002 (Etapa 1):** pipeline parametrizado `tools/ns002_pilot.py` + entregas e roteiros em `04-legendas/` e `02-reels-shorts/ns002-piloto-01/` (1080×1920, 30 fps, `-an`).
- **Plataforma Multi-Tenant (Etapa 2):**
  - Contratos formais (`schemas/brand-kit.schema.json`, `schemas/guardrails.schema.json`), `tools/tenant_validator.py` e 3 tenants configurados (`marca-salao`, `meu-salao`, `multitrack-hub`).
  - Motor genérico `tools/preset_runner.py` (`saas-demo` com `-an` e `shorts-completo` com faixa AAC) e orquestrador em lote `tools/factory_cli.py`.
  - Provas de entrega em `02-reels-shorts/deliveries/`, guia `docs/guia-novo-nicho.md`, validação no workflow `.github/workflows/local-render-validation.yml` e blindagem `eol=lf` em `.gitattributes`.

### Verificação pós-merge
- `tenant_validator.py --all --json` (`ok: true`), `factory_cli.py list --json` (`3` tenants / `3` campanhas), `verify_egm_install.py` (`OK`) e `65/65` testes aprovados.
```

- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

### 1. NS-001 incorporada ao motor multi-tenant (marca-salao)
<!-- devlog-sync:etapa3-agente1.md -->

- `tenants/marca-salao/campaigns/camp-saas-demo-ns001-agenda-001.json`
  - SHA-256: `9bb35ac0e6edcfecacf678f74f41c3d811512c94e9de6acca5986c7eefd6fc83`
  - 6 cenas / 30,0 s / preset `saas-demo` / campaignId `SAAS-DEMO-NS001-AGENDA-001`
  - Foco NS-001 (briefing `00-briefings/campanhas/NS-001/briefing.md`, hook NS-001-H15 revisado, roteiro `03-roteiros/campanhas/NS-001/roteiro-001.md`): organização e visibilidade diária de `/gestor/agenda`
  - Cenas: `cena-01-hook` (pergunta do hook), `cena-02-visao-do-dia`, `cena-03-filtros` (profissional/status), `cena-04-status-manual` (equipe), `cena-05-busca-cliente` (nome do cliente), `cena-06-cta`
  - Dados reais da fixture `tenants/marca-salao/fixtures/fixture-editorial-marca-salao.json` (destaques `atend-001`, `atend-003`, `atend-005`, `atend-006` — todos entre os 6 primeiros atendimentos desenhados)
  - Cabeçalho `MARCA SALAO` via brand-kit; **nenhuma cena de `/booking`**, zero slots, zero pagamento, zero promessas vetadas

### 2. White-label expandido (meu-salao)

- `tenants/meu-salao/campaigns/camp-saas-demo-meu-salao-002.json`
  - SHA-256: `d54ad8945e878bfa3585d1cd00a0d50c843c464bc483f3e72fbd4c75e6f77aac`
  - 6 cenas / 30,0 s / preset `saas-demo` / campaignId `SAAS-DEMO-MEU-SALAO-002`
  - Foco: rotina da equipe em `/gestor/agenda`
  - Cenas: `cena-01-hook`, `cena-02-abertura-do-dia`, `cena-03-equipe` (atendimentos por profissional), `cena-04-status-manual`, `cena-05-fim-do-dia`, `cena-06-cta`
  - Dados reais da fixture `tenants/meu-salao/fixtures/fixture-editorial-meu-salao.json` (destaques `atend-ms-001`, `atend-ms-002`, `atend-ms-003`, `atend-ms-005`)
  - Cabeçalho `MEU SALAO` via brand-kit; "Meu Salão" é termo permitido neste tenant (não está nos forbiddenClaims do meu-salao)

## Entregas renderizadas (`02-reels-shorts/deliveries/`)

### `marca-salao/camp-saas-demo-ns001-agenda-001/`

| artefato | bytes | SHA-256 |
| --- | --- | --- |
| `camp-saas-demo-ns001-agenda-001.mp4` (não versionado; `*.mp4` no `.gitignore`) | 585286 | `bb8d1e45098c039f078d7bbf4492f34ef89d7f850dbbdffbab0add122e896bd3` |
| `camp-saas-demo-ns001-agenda-001.srt` | 584 | `8fd2c485641cc325ad0b299ff918e7ba0828fc3128c2e84016a038791882e85e` |
| `camp-saas-demo-ns001-agenda-001_narracao.txt` | 958 | `ad925a6784c6a7baf59c5be095e94f152e35788598294fdab2f3b3d17d4382a7` |
| `preview-storyboard.png` | 703861 | `b0f0460c1c4bb30cd8b49e865d40ba333c53ffb8619323f51e1471675cc7088c` |
| `manifest.json` | 3065 | `b73004ab73782c91bef52cac889ea14330c4284f94875f047a55929dafed22b2` |

### `meu-salao/camp-saas-demo-meu-salao-002/`

| artefato | bytes | SHA-256 |
| --- | --- | --- |
| `camp-saas-demo-meu-salao-002.mp4` (não versionado; `*.mp4` no `.gitignore`) | 513587 | `82702ce609891c83d2ec4196c3b7fdb91a4c0262a5fe6407c81cf1988e669c35` |
| `camp-saas-demo-meu-salao-002.srt` | 573 | `e0e31d4d925c87b21a5bcb2fa6706e7b2f82f50515a79fd22f2ba19ef33d9b49` |
| `camp-saas-demo-meu-salao-002_narracao.txt` | 896 | `1d05c23c8c48566fc3de547b1a94127b0e62d44523f9f8b6d9f3f6bca1a465eb` |
| `preview-storyboard.png` | 645948 | `4b36f0c24b207a58deb04e08cdd0902f54aa9b19ca3623c12a7be61176e6f563` |
| `manifest.json` | 3001 | `7ff4cd4490550d1917ec01b955dd8e30104bce52b0b51968c5d0e3811a381c4e` |

Cópia dos MP4s preservada em `.workspace/archives/<slug>/` (padrão da etapa 2).

## ffprobe (MP4s em `.workspace/archives/`)

- `camp-saas-demo-ns001-agenda-001.mp4`: `h264`, **1080x1920**, `avg_frame_rate 30/1`, `duration 30.000000`, **1 stream de vídeo / 0 streams de áudio**
- `camp-saas-demo-meu-salao-002.mp4`: `h264`, **1080x1920**, `avg_frame_rate 30/1`, `duration 30.000000`, **1 stream de vídeo / 0 streams de áudio**
- Relatórios da fábrica (mode `filtered`): `allowAudioTrack: false`, `audioStreams: 0`, `audioCodec: null` — política `-an` respeitada pelos dois tenants.

## Comandos executados (a partir da worktree)

```
python tools/factory_cli.py render --tenant marca-salao --campaign camp-saas-demo-ns001-agenda-001 --report .workspace/tmp/etapa3-agente1/factory-report-marca-salao.json --json
python tools/factory_cli.py render --tenant meu-salao --campaign camp-saas-demo-meu-salao-002 --report .workspace/tmp/etapa3-agente1/factory-report-meu-salao.json --json
python tools/tenant_validator.py --all --json
python -m unittest tools/tests/test_tenant_contracts.py tools/tests/test_factory_cli.py -v
```

FFmpeg/FFprobe portáteis do checkout principal (`<RAIZ>/.workspace/tools/ffmpeg`) adicionados ao `PATH` apenas para os processos destes comandos.

### Adaptação documentada em relação ao pedido original

O pedido indicava `render --tenant <id> --json` sem `--campaign`/`--report`. O escopo foi ajustado por três motivos:

1. `02-reels-shorts/deliveries/factory-report.json` versionado está **fora do território exclusivo** deste agente (regra de isolamento da Etapa 3);
2. o `test_03` de `tools/tests/test_factory_cli.py` valida o conteúdo exato do relatório versionado (3 tenants / 3 campanhas) — sobrescrevê-lo em modo `filtered` quebraria o teste, e o arquivo de teste também está fora do território;
3. renderizar o tenant inteiro reprocessaria as campanhas `-001` já entregues e commitadas, criando diffs desnecessários (o MP4 muda a cada render por metadados de muxer, alterando o `manifest.json`).

Os relatórios destas renderizações ficaram em `.workspace/tmp/etapa3-agente1/factory-report-*.json`. **Pendência para a consolidação da Etapa 3:** regenerar o relatório versionado com `render --all` (agora 5 campanhas) e atualizar o `test_03` para as novas contagens.

## Resultado dos testes

- `python tools/tenant_validator.py --all --json` → `ok: true`, 3 tenants (`marca-salao`, `meu-salao`, `multitrack-hub`), **0 erros**
- `python -m unittest tools/tests/test_tenant_contracts.py tools/tests/test_factory_cli.py -v` → **11/11 OK** em 14,974 s (7 testes de contratos + 4 do factory_cli, incluindo render real com `-an` e integridade do relatório versionado)

## Guardrails conferidos

- `allowAudioTrack: false` → `-an` forçado pelo motor; ffprobe confirma **0 streams de áudio**
- Zero menções a WhatsApp/SMS/e-mail/lembrete/24h/automação (auditoria do motor passou antes do render)
- Zero promessas de redução de faltas, faturamento, ocupação ou "agenda sempre cheia"
- Zero telas/termos de pagamento (forbiddenUiElements)
- Separação estrita `/booking/[salonId]` × `/gestor/agenda`: as duas campanhas usam somente superfícies `manager-agenda` (rota `/gestor/agenda`) e `marca` (hook/CTA); nenhuma cena de booking, nenhum slot exibido
- Textos desenhados em tela sem acentos (fonte bitmap 5x7 do motor); legendas (SRT) e narração em português brasileiro com acentos

## Pendências para a consolidação

- Regenerar `02-reels-shorts/deliveries/factory-report.json` com `render --all` e atualizar `test_03` (contagens 3 → 5 campanhas)
- Aprovação editorial das duas campanhas continua pendente junto ao titular (entregas de fábrica são rascunhos técnicos, não campanhas aprovadas para publicação)
- Branch com commit local; publicação no remoto fica para a consolidação (nenhum `git push` foi executado, conforme instrução "faça commit na branch")

### Devlog — Etapa 3 / Agente 2 (áudio + Multitrack Hub)
<!-- devlog-sync:etapa3-agente2.md -->

**Branch:** `codex/etapa3-agente2-audio-multitrack`
**Data:** 2026-11-18
**Papel:** Engenheiro de Mídia Programática e FFmpeg (Agente 2 de 4, paralelo)

## Raiz e isolamento

- `<RAIZ>` desta estação (checkout principal): `D:/MEGA/Marketing/marcasalao-marketing`.
- Worktree isolada criada a partir de `main`:
  `git worktree add -b codex/etapa3-agente2-audio-multitrack .workspace/worktrees/etapa3-agente2 main`
- Todos os comandos e edições ocorreram exclusivamente dentro de
  `.workspace/worktrees/etapa3-agente2`. Nenhuma outra worktree foi tocada.
- Território editado (respeitado): `tools/audio_tts.py`, `tools/tests/test_audio_tts.py`,
  `tenants/multitrack-hub/**`, `02-reels-shorts/deliveries/multitrack-hub/**`,
  `.workspace/devlogs/etapa3-agente2.md`.
  **Não** foram modificados `tools/preset_runner.py` nem `contexto_projeto.md`.

### `tools/derivative_formats.py` (novo, ~535 linhas)
<!-- devlog-sync:etapa4-agente1.md -->

Gerador de derivados multiformato a partir dos MP4s 9:16 (1080x1920) arquivados em
`.workspace/archives/<slug>/<slug>.mp4` pelas entregas vigentes.

- **API programática**: `generate_derivatives(tenant_id, slug, root=".") -> dict`
  e `discover_campaigns(root, tenant_id=None, campaign=None)` (glob dos
  `02-reels-shorts/deliveries/*/*/manifest.json`).
- **CLI**: `--all` | `--tenant <id> [--campaign <slug>]`, `--root`, `--json`
  (payload `{ok, total, generated, campaigns, errors}`; exit 0/1/2).
- **Derivados por campanha** em `.workspace/archives/<slug>/derivatives/`:
  - `<slug>-cover.png` — 1080x1920, frame em 2.0 s (ou metade da duração quando
    `< 2.5 s`), moldura `drawbox` na cor primária do brand-kit (inset 12 px,
    espessura 8 px, alpha 0.85).
  - `<slug>-1x1.mp4` — 1080x1080, 30 fps, h264, yuv420p, `-movflags +faststart`,
    `-crf 20 -preset veryfast`. Fundo boxblur escurecido derivado do próprio vídeo
    (`boxblur=20:2,eq=brightness=-0.2:saturation=0.9`) + tinta da paleta a 12%
    (`blend` sobre `lavfi color`), vídeo 9:16 centralizado em altura total
    (608x1080), preservando a legenda queimada.
  - `<slug>-16x9.mp4` — 1920x1080, mesma composição com primeiro plano 608x1080.
- **Política de áudio estrita** por `tenants/<id>/guardrails.json`
  (`audioPolicy.allowAudioTrack`), lida via `tenant_validator.load_and_validate_tenant(strict=True)`:
  - `false` (marca-salao, meu-salao, estudio-flow) → `-an`, 0 streams de áudio,
    **mesmo que a fonte tenha trilha**.
  - `true` (multitrack-hub) → `-map 0:a:0 -c:a aac -ar 44100 -ac 2 -b:a 128k`;
    fonte sem trilha → erro `FONTE_SEM_AUDIO` (nada é gerado).
- **Auditoria ffprobe antes de gravar manifesto** (`_audit_derivative`): geometria,
  codec, pix_fmt, fps, contagem/codec/rate/canais de áudio e duração; qualquer
  desvio → `AUDITORIA_DERIVADO` e nenhum manifesto é gravado.
- **Manifesto versionado** `02-reels-shorts/deliveries/<tenantId>/<slug>/derivatives.json`
  (UTF-8 LF via `render_local.write_text`): dimensões, codecs, streams de áudio,
  bytes e SHA-256 de cada derivado + ffprobe resumido + hash da fonte + comando
  reproduzível + versões de ffmpeg/ffprobe. Os .mp4/.png continuam apenas no
  `.workspace/` local (`.gitignore` versionado ignora `*.mp4`).
- **Erros contratuais estáveis**: `ENTREGA_NAO_ENCONTRADA`, `FONTE_AUSENTE`,
  `FONTE_GEOMETRIA_INVALIDA`, `FONTE_SEM_AUDIO`, `FONTE_DURACAO_INVALIDA`,
  `FFMPEG_TIMEOUT`, `FFMPEG_NAO_EXECUTAVEL`, `FFMPEG_FALHOU`, `AUDITORIA_DERIVADO`.

### `tools/tests/test_derivative_formats.py` (novo, 10 testes)

Fontes sintéticas 1080x1920/3 s (com e sem trilha AAC) em slugs de teste — a suíte
não depende dos MP4s reais arquivados (`.workspace/` é local e não existe no CI);
manifestos de entrega sintéticos são criados em `deliveries/<tenant>/<slug-de-teste>`
e removidos no cleanup da classe.

1. `test_01` — 1x1 1080x1080/30 fps/h264/yuv420p com **`-an` forçado** (fonte COM
   áudio + marca-salao): 0 streams, sonda independente confirma.
2. `test_02` — 16x9 1920x1080/30 fps, mesmo bloqueio, primeiro plano 608x1080.
3. `test_03` — cover PNG 1080x1920, timestamp 2.0 s, moldura na cor primária
   `#F5C107` do brand-kit.
4. `test_04` — multitrack-hub preserva AAC: 1 stream aac 44100 Hz stereo em 1x1 e 16x9.
5. `test_05` — `FONTE_SEM_AUDIO` rejeitado e nenhum derivado gerado.
6. `test_06` — integridade SHA-256/bytes dos 3 derivados contra o retorno e contra
   o `derivatives.json` em disco (LF, sem `\r`).
7. `test_07` / `test_08` — `FONTE_AUSENTE` / `ENTREGA_NAO_ENCONTRADA`.
8. `test_09` — `discover_campaigns` (>= 8 entregas reais, filtros por tenant/campanha).
9. `test_10` — CLI `--json` exit 0, `ok=true`, `generated=1`.

### `tools/static_cards.py` — Motor programático de cards estáticos (100% stdlib)
<!-- devlog-sync:etapa5-agente1.md -->

API programática e CLI:

- `generate_campaign_static_cards(tenant_id, slug=None, root=None, kinds=None)`
- `generate_all_static_cards(root=None, kinds=None)`
- CLI: `python tools/static_cards.py --all [--types stories,carousel] [--json]`
  e `python tools/static_cards.py --tenant <tenantId> [--campaign <slug>] [--json]`

Reutiliza as primitivas de canvas PNG e fonte bitmap 5x7 de `tools/ns002_pilot.py` (mesmas de
`tools/preset_runner.py`): `_draw_text`, `_wrap_text`, `_fill_rect`, `_stroke_rect`, `_draw_card`,
`_draw_pill`, `_encode_png`, `_base_gradient`, `_pal`, `_format_price_brl`, `_norm_text`,
`_text_width`. Zero dependências externas (sem `Pillow`/`PIL`).

### Fluxo por campanha (8 campanhas × 4 tenants)

Para cada campanha de `tenants/<tenantId>/campaigns/*.json`:

1. Carrega e valida o tenant via `tenant_validator.load_and_validate_tenant(..., strict=True)`
   (brand-kit, guardrails, fixture).
2. Lê o roteiro/legendas da entrega: `02-reels-shorts/deliveries/<tenantId>/<slug>/<slug>_narracao.txt`.
3. **Auditoria obrigatória de guardrails** antes de qualquer pixel:
   `tenant_validator.validate_text_against_guardrails(text, guardrails, check_ui_elements=True)`
   sobre títulos, subtítulos, badges de rota, itens da fixture e CTAs. Qualquer violação aborta com
   `StaticCardsError(code="GUARDRAIL_VIOLACAO")`.
4. Renderiza 2 kits versionados em `01-insta-stories/deliveries/<tenantId>/<slug>/`:
   - `stories/` — 3 lâminas verticais 1080x1920 (PNG RGB):
     `story-01-hook.png` (monograma, `headerOverlay.label`, gancho principal da campanha, `1/3`),
     `story-02-fluxo.png` (dados reais da fixture: profissional/serviço/preço BRL ou projeto/stems/rateio,
     rotas de `routeRules` separadas, sem botões clicáveis falsos, sem telas de pagamento),
     `story-03-cta.png` (resumo de valor operacional + CTA explícito "LINK NA BIO"/"LINK NA DESCRIÇÃO",
     sem sticker clicável falso, `3/3`).
   - `carousel/` — 4 slides retrato 1080x1350 (4:5, PNG RGB):
     `slide-01-capa.png`, `slide-02-problema.png`, `slide-03-pratica.png`, `slide-04-resumo-cta.png`.
   - `static-manifest.json` (UTF-8 LF, determinístico, caminhos relativos):
     `schemaVersion: 1`, `tenantId`, `slug`, `guardrailsAudited: true`, dimensões, bytes e
     SHA-256 de cada uma das 7 lâminas.

### Diferenças por tenant respeitadas

- `marca-salao`: proíbe "meu salão"/"meu salao" (CLAIM_FORBIDDEN) — nunca renderizado nos cards desse tenant.
- `meu-salao`: permite "Meu Salão" (nome da marca desse tenant).
- Paletas distintas aplicadas por tenant (headerBg, primaryAccent, gradiente de fundo).
- CTA: "LINK NA BIO" (Instagram, `utm_source=instagram`) vs "LINK NA DESCRIÇÃO" (YouTube/Shorts).

## Resultados da execução consolidada

`python tools/static_cards.py --all --json` → exit code 0:

| Tenant | Campanhas | Láminas PNG |
|---|---|---|
| estudio-flow | 1 | 7 |
| marca-salao | 2 | 14 |
| meu-salao | 2 | 14 |
| multitrack-hub | 3 | 21 |
| **Total** | **8** | **56** + **8 static-manifest.json** |

Validações realizadas:

- Todas as 56 lâminas conferidas pelo header PNG (IHDR): `stories/` = 1080x1920, `carousel/` = 1080x1350.
- Manifestos: `guardrailsAudited: true`, SHA-256 e bytes condizem com os arquivos, LF puro, sem caminhos absolutos (`D:/`, `C:/`).
- Determinismo: segunda execução sobre a mesma campanha produz SHA-256 idênticos (manifesto e lâminas).

## Suíte de testes — `tools/tests/test_static_cards.py`

12 testes (mínimo exigido: 10), todos OK:

1. 3 lâminas Stories 1080x1920 exatas no header PNG.
2. 4 lâminas Carrossel 1080x1350 exatas no header PNG.
3. Paletas distintas dos 4 tenants (pixel de cabeçalho = `headerBg`, faixa de acento = `primaryAccent`, gradiente = `backgroundTop/Bottom`; 4 amostras pairwise distintas).
4. Bloqueio preventivo com elemento UI proibido (`checkout` → `UI_FORBIDDEN`, `GUARDRAIL_VIOLACAO`).
5. Bloqueio com claim proibida (`reducao de faltas garantida` → `CLAIM_FORBIDDEN`).
6. Regra diferencial: `marca-salao` bloqueia "MEU SALAO"; `meu-salao` permite.
7. Integridade SHA-256 + bytes das 7 lâminas vs `static-manifest.json` (8 campanhas).
8. Sem caminhos absolutos e LF puro nos 8 manifestos.
9. Determinismo: execuções repetidas geram bytes idênticos.
10. Validação consolidada das 8 entregas reais em `01-insta-stories/deliveries/`.
11. CLI `--tenant` + `--campaign` + `--json` → exit code 0.
12. CLI `--all --json` → exit code 0 (8 campanhas).

Execução: `python -m unittest tools/tests/test_static_cards.py -v` → `Ran 12 tests, OK` (~17 s).

## Vídeo sem áudio

Este módulo produz apenas imagens estáticas. Não há faixa de áudio, narração, música ou efeitos; a
regra de produção do projeto (vídeo mudo, legenda separada em `04-legendas/`) permanece intocada — não
se aplica diretamente a cards estáticos, mas o motor não gera nem referencia áudio.

## Nota de commit

O índice da worktrave travou (`index.lock` imutável por restrição do sandbox); o commit foi feito via
plumbing (`hash-object -w`, `mktree`, `commit-tree`, `update-ref`) sobre a árvore de `HEAD`,
adicionando somente os arquivos listados acima, sem alterar histórico nem outros agentes.

### Problema
<!-- devlog-sync:etapa5-agente2.md -->

O checklist calculava `sha256_disk_ok` da mídia abrindo o caminho relativo da
entrega. Os MP4s não são versionados: em qualquer worktree o arquivo não
existe ali, e a auditoria de vídeo caía sempre em `false`.

### Mudança

- `resolve_workspace_root(root)` implementado com o padrão de
  `derivative_formats.py` / `review_dashboard.py`: prefere
  `<raiz>/.workspace/archives`; em worktree resolve o checkout principal via
  `git rev-parse --git-common-dir` e usa o `.workspace/` de lá. Raiz sem
  checkout git cai no próprio `<raiz>/.workspace`.
- `_main_checkout_root(root)` isola a chamada git (timeout de 15s, falha
  silenciosa → fallback).
- `_resolve_artifact_path(root, workspace_root, entry)` resolve
  `archivePath` (`.workspace/archives/...`) contra o workspace principal e
  confina o resultado (`render_local.contained`). Artefatos versionados (SRT,
  narração, storyboard) continuam relativos à raiz do checkout.
- `_build_checklist(...)` passou a receber `root_real` + `workspace_root`, em
  vez de inferir três níveis acima do pacote. Cada item de mídia agora traz
  `archivePath`, `resolvedFrom` (`archive`/`delivery`/`fora_da_raiz`),
  `presentOnDisk` e `sha256_disk_ok`. `guardrailStatus` sempre inclui
  `srt_violations` e `narration_violations` (lista vazia quando ok).

### Execução obrigatória

```
python tools/publish_pack.py --all --json
```

Resultado: **8 pacotes / 4 tenants**, **0 violações de guardrails**,
`autoPublish: false` em todos. Os 8 `checklist-publicacao.json` foram
regravados com os campos novos (diff esperado e restrito a
`04-legendas/pacotes-publicacao/**`).

---

### Devlog — Etapa 5B / Agente 4 (integração do QA editorial no pipeline)
<!-- devlog-sync:etapa5-agente5.md -->

> **Data:** 2026-11-20  
> **Branch/worktree:** `codex/etapa5b-agente4` em `.workspace/worktrees/etapa5b-agente4`  
> **Base integrada:** `main` @ `3f8cb1a` (Etapa 5B consolidada: 5 tenants, 10 campanhas)  
> **Escopo:** estágio opcional `editorial_qa` no pipeline mestre, cobertura de teste e suíte do CI

### 1. Schema (`schemas/brand-kit.schema.json`)
<!-- devlog-sync:etapa6-agente1.md -->

Nova propriedade **opcional** `uiLabels` (`type: object`, `additionalProperties: false`)
com 7 chaves string (`minLength: 1`):
`teamSectionTitle`, `catalogSectionTitle`, `publicRouteFallback`,
`managerRouteFallback`, `journeyBridgeCaption`, `itemUnitLabel`, `customerLabel`.

- `additionalProperties: false` garante que o validador
  (`tenant_validator.validate_against_schema`) rejeite chaves desconhecidas dentro de
  `uiLabels`.
- Opcional (fora de `required`) → fixtures/brand-kits sintéticos sem `uiLabels`
  continuam válidos.

### 2. Brand-kits (5 tenants) — valores de `uiLabels`

| tenant | teamSectionTitle | catalogSectionTitle | publicRouteFallback | managerRouteFallback | journeyBridgeCaption | itemUnitLabel | customerLabel |
| --- | --- | --- | --- | --- | --- | --- | --- |
| marca-salao | PROFISSIONAIS DO SALAO | SERVICOS DISPONIVEIS | /booking/[salonId] | /gestor/agenda | DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO | atendimento | Cliente |
| meu-salao | PROFISSIONAIS DO SALAO | SERVICOS DISPONIVEIS | /booking/[salonId] | /gestor/agenda | DO AGENDAMENTO DA CLIENTE A AGENDA DO MEU SALAO | atendimento | Cliente |
| estudio-flow | INSTRUTORES DO ESTUDIO | MODALIDADES DISPONIVEIS | /aulas/[studioId] | /gestor/turmas | DA RESERVA DA ALUNA A GRADE DO ESTUDIO | aula | Aluna |
| clinica-vital | ESPECIALISTAS DA CLINICA | PROCEDIMENTOS DISPONIVEIS | /avaliacao/[clinicId] | /gestor/consultas | DA MARCACAO DO PACIENTE A AGENDA DA CLINICA | consulta | Paciente |
| multitrack-hub | CATALOGO DE PROJETOS | FAIXAS E RATEIOS | / | /rateios | DA ORGANIZACAO DOS STEMS AOS RATEIOS | projeto | Musico |

- `marca-salao` NÃO inclui "Meu Salão" (é `forbiddenClaim`) — verificado.
- Todos os rótulos passam pelos `guardrails.json` de cada tenant (auditoria abaixo).

### 3. Refatoração (`tools/preset_runner.py`)

- `DEFAULT_UI_LABELS` (valores de salão) + `_resolve_ui_labels(brand_kit)`:
  mescla defaults com `brand_kit["uiLabels"]`, por chave; chaves ausentes/vazias/tipo
  inválido caem no padrão de salão → retrocompatibilidade total.
- `_render_saas_frame` passou a usar os rótulos resolvidos (normalizados via
  `_norm_text`, compatível com a fonte bitmap 5x7):
  - `PROFISSIONAIS DO SALAO` → `teamSectionTitle`;
  - `SERVICOS DISPONIVEIS` → `catalogSectionTitle`;
  - `/BOOKING`, `/BOOKING/[SALONID]` → `publicRouteFallback`;
  - `/GESTOR/AGENDA` → `managerRouteFallback`;
  - ponte `DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO` → `journeyBridgeCaption`;
  - `CLIENTE` (passos do hook e resumos) → `customerLabel`;
  - `VALOR ESTIMADO` → `VALOR ESTIMADO POR {itemUnitLabel}` (atendimento/aula/consulta);
  - fallback da rota em `booking-selection` deixou de ser hardcoded
    (`"/booking/[salonId]"`) e passou a usar `publicRouteFallback`.
- **Auditoria de guardrails dos `uiLabels`:** em `run_preset_pipeline`, os rótulos
  resolvidos entram em `texts_to_audit` (`uiLabels.<chave>`) ANTES de qualquer render,
  com `validate_text_against_guardrails(..., check_ui_elements=True)`.
- O manifesto agora registra `"uiLabels"` resolvidos (normalizados) — rastreável e
  testável.

### 4. Testes (`tools/tests/test_preset_runner.py`)

- Nova classe `UiLabelsTest` com **5 testes** (total do arquivo = 13):
  1. `test_ui01` fallback sem `uiLabels` == `DEFAULT_UI_LABELS` (retrocompatível).
  2. `test_ui02` resolução específica de `clinica-vital` e `estudio-flow` (+ fallback parcial por chave).
  3. `test_ui03` guardrail bloqueia `uiLabel` proibido ("Meu Salão" injetado em marca-salao).
  4. `test_ui04` schema rejeita chave desconhecida dentro de `uiLabels`.
  5. `test_ui05` gera frames `saas-demo` reais de clinica-vital e estudio-flow (PNG 1080x1920) e confirma ausência de regressão no marca-salao.
- Ajuste de ambiente (dentro do território): a injeção de `ffmpeg` no `PATH` do teste
  agora resolve a **raiz principal** via `git rev-parse --git-common-dir`, achando o
  ffmpeg compartilhado em `<MAIN_ROOT>/.workspace/tools/ffmpeg` mesmo rodando numa
  worktree (antes dependia de `<worktree>/.workspace/tools/ffmpeg`, inexistente).

## Resultados

- `python tools/tenant_validator.py --all --json` → `ok: true` nos 5 tenants.
- `python -m unittest tools.tests.test_preset_runner tools.tests.test_tenant_contracts -v`
  → **22 testes OK** (8 preset_runner + 5 uiLabels + 9 tenant_contracts), ~88s
  (inclui renders reais FFmpeg de marca-salao saas-demo e multitrack-hub shorts, com e
  sem áudio externo).
- Frames `saas-demo` gerados para `clinica-vital` (`ESPECIALISTAS DA CLINICA`) e
  `estudio-flow` (`INSTRUTORES DO ESTUDIO`) sem regressão no `marca-salao`.
- FFmpeg usado: 9.1-essentials em `<MAIN_ROOT>/.workspace/tools/ffmpeg` (compartilhado,
  fora do versionamento).

## Observações / limitações (fora do escopo deste agente)

- Rótulos singulares no resumo (`PROFISSIONAL:`, `SERVICO:`) NÃO estão entre as 7
  chaves de `uiLabels`; permanecem como estão e não disparam guardrails. Uma futura
  extensão poderia adicionar `professionalLabel`/`serviceLabel`.
- `multitrack-hub` usa preset `shorts-completo`; seus `uiLabels` são preenchidos e
  auditados, mas o render de shorts não consome essas chaves nesta etapa (shorts tem
  vocabulário próprio e não vazava salão).
- `_norm_text` (e `_draw_text`) já aplicam uppercase/transliteração; a normalização é
  idempotente.

## Conformidade

- Trabalho restrito à worktree `.workspace/worktrees/etapa6-agente1`.
- `contexto_projeto.md` não editado (sincronização delegada ao consolidador).
- Working tree da branch limpo ao final; commit na branch `codex/etapa6-agente1`.

### Etapa 6 — Agente 2 — Quebra mobile determinística de SRT (46 avisos → 0)
<!-- devlog-sync:etapa6-agente2.md -->

**Data:** 2026-11-20
**Papel:** Engenheiro Sênior de Pós-Produção e Qualidade de Legendas (Agente 2 de 8, paralelo)
**Branch:** `codex/etapa6-agente2`
**Worktree:** `.workspace/worktrees/etapa6-agente2` (já existente, base `8a1b361` = `main`)
**Raiz da estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

> `contexto_projeto.md` não foi tocado; este relatório é a fonte para o
> `devlog_sync.py` na consolidação. `camp-saas-demo-estudio-flow-002` não foi
> criado nem alterado (não existe em `02-reels-shorts/deliveries/`).

---

## 1. Problema reproduzido

```
python tools/editorial_qa.py --all --strict --json   -> exit 1
ok: false | campanhas: 10 com problemas | 0 erros | 46 avisos
lente legibilidade_mobile: 46 x SRT_LINHA_LONGA
```

Linhas entre 49 e 82 caracteres (teto mobile = 48) distribuídas pelas 10
entregas. Cada `manifest.json` guarda `artifacts.srt.sha256`/`bytes`, então o
hash e o tamanho precisam acompanhar qualquer reformatação.

## 2. Motor `tools/srt_formatter.py` (novo, 100% stdlib)

API implementada:

- `wrap_srt_cue_text(text, max_chars=48, max_lines=2) -> str`
  - normaliza espaços, preserva palavras/pontuação/acentos;
  - corte preferencial depois de pontuação (`, . ; : ! ? — –`), depois antes
    de conjunção (` e `, ` ou `, ` mas `, ` que `, ` para `, ` com `…), por
    fim no espaço mais próximo do ponto médio;
  - entre candidatos válidos (`len <= max_chars` nos dois lados) escolhe o
    mais equilibrado;
  - palavra isolada maior que o teto é cortada em pedaços seguros
    (`_hard_cut`, sem loop);
  - conteúdo maior que `max_lines * max_chars` é preservado integralmente com
    mais linhas, sempre `len(linha) <= max_chars`.
- `format_srt_content(srt_text, max_chars=48, max_lines=2) -> (str, dict)`
  - copia índices e timestamps literalmente; reúne o corpo de cada cue e
    re-quebra; valida com `srt_validate` antes de devolver; estatísticas de
    antes/depois por linha.
- `format_delivery_srts(root=".", max_chars=48, update_manifests=True,
  tenant=None, slug=None, dry_run=False) -> dict`
  - descobre `02-reels-shorts/deliveries/<tenant>/<slug>/<slug>.srt`;
  - grava sempre em LF puro (`\n`) e atualiza `artifacts.srt.sha256/bytes`
    (e `files.srt` quando presente), preservando vídeo, narração e storyboard;
  - `dry_run=True` não grava nada (usado pelo `--check-only`);
  - filtros por tenant/campanha e contenção de path (regex de slug + realpath
    sob a raiz).
- CLI:
  `python tools/srt_formatter.py [--all | --tenant <id> [--campaign <slug>]]
  [--max-chars 48] [--check-only] [--root <raiz>] [--json]`
  - `--check-only`: exit 1 se houver linha acima do teto; nunca grava.

## 3. Resultado por campanha (antes → depois)

`bytes` permaneceu igual porque a quebra troca um espaço (1 byte) por LF
(1 byte); o formatador recalcula o SHA-256 sempre.

| Tenant | Campanha | Max linha antes | Max linha depois | Bytes | Novo SHA-256 do `.srt` |
| --- | --- | ---: | ---: | ---: | --- |
| clinica-vital | camp-saas-demo-clinica-vital-001 | 74 | 47 | 606 | `7ead3171cfd5b06365a1ee043caa416191d5d95a09e2886fd3e5182449a743cc` |
| clinica-vital | camp-saas-demo-clinica-vital-002 | 82 | 47 | 638 | `7ddaeecfced5e4abe475018e1af0e13d12ae32ac63591026a2780a9324afa303` |
| estudio-flow | camp-saas-demo-estudio-flow-001 | 73 | 46 | 572 | `771a38c5c77e10cb38e6cb37ddf88592b7303b8e9b5290d4c501d6fed317be1a` |
| marca-salao | camp-saas-demo-marca-salao-001 | 63 | 47 | 496 | `14b560ff6667789c892acad515aa6625c7fb0b47e5cbbf1587c2f07bc7710ff8` |
| marca-salao | camp-saas-demo-ns001-agenda-001 | 68 | 44 | 584 | `85a7ce46d868677c581b2829627cb7f64a80f0f80a47a656c4fc775be91f21e8` |
| meu-salao | camp-saas-demo-meu-salao-001 | 63 | 47 | 492 | `bd04bd659a960000565161a8d3368c6802e84641e456bcd3339dd5aaa0685898` |
| meu-salao | camp-saas-demo-meu-salao-002 | 70 | 47 | 573 | `2c2babf3abc64ed5fb0b4728ddfbf461a0e1c4f4381572a26280fb67730be5f7` |
| multitrack-hub | camp-shorts-completo-multitrack-001 | 62 | 47 | 444 | `88c9f93934efe07ad195c8225fb66b6f48dc407ec1e2b55a8a7ac2e8f76a4582` |
| multitrack-hub | camp-shorts-rateios-002 | 75 | 44 | 516 | `daeb5d71ef29ce8be3a21844ca1a72e6341d935a307a3eed0049b9ba0da58791` |
| multitrack-hub | camp-shorts-stems-workflow-003 | 71 | 43 | 488 | `901df302c3e8db10ca46387f0047a2d4645d808f9637f4f175ea4ff715a81e93` |

Totais do formatter: **10 campanhas alteradas, 10 manifestos sincronizados,
46 linhas longas antes, 0 depois**. Segunda execução: `changed: 0`.

## 4. Auditorias finais

```
python tools/editorial_qa.py --all --strict --json   -> exit 0, ok: true
  problemas: 0 erros, 0 avisos | checks: 5 ok, 0 warn, 0 fail
python tools/release_audit.py --strict --json        -> exit 0, ok: true
  7/7 domínios ok | 0 erros, 0 avisos | 10/10 entregas, 10/10 pacotes
```

## 5. Testes

`tools/tests/test_srt_formatter.py` (11 testes): quebra equilibrada 48/2,
preservação de índices/timestamps/acentos, idempotência, `--check-only` sem
escrita, sync de manifesto (artifacts + files; demais hashes intactos), LF
puro, 10 campanhas reais (≤48 e hash íntegro), filtros tenant/campanha,
contenção de path, CLI `--json`, palavra única acima do teto.

```
python -m unittest tools/tests/test_srt_formatter.py tools/tests/test_srt_validate.py \
  tools/tests/test_editorial_qa.py tools/tests/test_release_audit.py -v
-> Ran 56 tests ... OK
```

## 6. Desvios declarados (necessários para o critério `ok: true`)

1. **`04-legendas/pacotes-publicacao/**/checklist-publicacao.json` (10 arquivos)**
   — fora do território nominal desta tarefa, mas o `release_audit` cruza
   `checklist.media[kind=srt].sha256` com o arquivo em disco. Atualizei
   cirurgicamente **apenas** `sha256` (e `bytes`, quando divergente) da entrada
   `kind: "srt"`; vídeo, narração e storyboard foram verificados
   programaticamente como idênticos ao HEAD. Sem isso, `release_audit` fica
   `pacotes_sociais: HASH_DIVERGENTE` para as 10 campanhas.
2. **`tools/tests/test_editorial_qa.py`** — também fora do território nominal.
   Três testes codificavam o baseline antigo de 46 avisos:
   - `test_01` esperava `legibilidade_mobile: warn`; agora espera `ok` e 0 avisos;
   - `test_02` substituía uma frase longa que deixou de existir; passou a usar
     o helper `_set_cue_body` (independente do texto atual);
   - `test_10` esvaziava um cue por frase literal; passou a esvaziar o cue por
     índice com o mesmo helper.
   O restante da suíte não foi alterado.
3. **`dry_run`** foi adicionado como parâmetro opcional da API (além da
   assinatura pedida) para implementar `--check-only` sem gravar disco.

## 7. Arquivos alterados

- Novos: `tools/srt_formatter.py`, `tools/tests/test_srt_formatter.py`,
  `.workspace/devlogs/etapa6-agente2.md`.
- Modificados: 10 `.srt` + 10 `manifest.json` em `02-reels-shorts/deliveries/`;
  10 `checklist-publicacao.json`; `tools/tests/test_editorial_qa.py`.
- `contexto_projeto.md` e `camp-saas-demo-estudio-flow-002` intocados.
- Commit local na `codex/etapa6-agente2`; sem push.

### Compatibilidade de schema (nuance registrada)
<!-- devlog-sync:etapa6-agente3.md -->

O `POST /api/approvals` do portal valida estritamente um conjunto de chaves que
**não inclui `updatedAt`**. O `GET` não valida. Portanto:

- o arquivo gerado pela CLI é lido e exibido pelo portal normalmente;
- uma reexportação pelo navegador descarta `updatedAt` (sem corromper os demais
  campos), e a CLI continua operando (o campo é opcional na leitura).

`tools/review_dashboard.py` não foi alterado (fora do território).

## 5. Contratos JSON (exemplos reais)

`python tools/approval_cli.py status --json` (sem store):

```json
{
  "ok": true,
  "autoPublish": false,
  "exists": false,
  "approvalsFile": ".workspace/tmp/aprovacoes-titular.json",
  "summary": {"total": 10, "aprovadas": 0, "aguardando": 10, "ajuste": 0},
  "externalAudioTenants": ["clinica-vital", "estudio-flow", "marca-salao", "meu-salao"],
  "locucaoExternaPendente": [],
  "campaigns": [
    {"tenantId": "clinica-vital", "slug": "camp-saas-demo-clinica-vital-001",
     "decision": "aguardando", "externalAudio": true,
     "locucaoExternaConferida": false, "updatedAt": null}
  ]
}
```

`decide` (trecho da resposta e do arquivo):

```json
{
  "ok": true, "autoPublish": false,
  "tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
  "decision": "aprovado", "reviewer": "Titular", "updatedAt": "2026-11-21T01:21:43Z",
  "campaign": {
    "tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
    "campaignId": "SAAS-DEMO-NS001-AGENDA-001", "preset": "saas-demo",
    "politicaAudio": "-an", "decisao": "aprovado",
    "locucaoExternaConferida": true, "observacoes": "",
    "hashes": {"video": "...", "srt": "...", "narracao": "...", "storyboard": "..."},
    "updatedAt": "2026-11-21T01:21:43Z"
  }
}
```

Documento gravado: `schemaVersion: 2`, `arquivo: "aprovacoes-titular.json"`,
`origem: "tools/approval_cli.py"`, `exportadoEm`, `revisor`, `resumo`
(`totalCampanhas/aprovadas/ajustes/pendentes`) e `campanhas` ordenadas.

`validate`:

```json
{
  "ok": true, "exists": true, "total": 1,
  "summary": {"total": 1, "aprovadas": 1, "aguardando": 0, "ajuste": 0},
  "errors": [], "warnings": [], "staleApprovals": [],
  "campaigns": [{"tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
                 "decision": "aprovado", "staleApproval": false, "changedHashes": [],
                 "hashCheck": "ok"}]
}
```

`staleApproval`: quando o `manifest.json` muda após a decisão, a campanha sai
com `staleApproval: true` e `changedHashes` (ex.: `["video"]`), `ok: false`.
Sem manifesto, `hashCheck: "sem_hashes"` e sem falso positivo. Aviso (não erro):
`-an` aprovado sem `--external-audio-checked`.

## 6. Subcomando `handoff` no orquestrador

```bash
python tools/factory_cli.py handoff --date 2026-11-23 \
  --approvals-file .workspace/tmp/aprovacoes-titular.json \
  --output-dir .workspace/handoff-diario --json
```

Fluxo: importa `approval_cli` e `handoff_bundler` via `_optional_module`
(mesmo padrão dos módulos paralelos), roda `cmd_validate`, aborta com
`APROVACOES_INVALIDAS` somente em erros de schema/campanha e chama
`build_handoff_bundle`. Saída unificada:

```json
{
  "schemaVersion": 1, "ok": true, "autoPublish": false,
  "mode": "date", "date": "2026-11-23",
  "approvalAudit": {"ok": true, "exists": true, "total": 1,
                    "summary": {"total": 1, "aprovadas": 1, "aguardando": 0, "ajuste": 0},
                    "staleApprovals": [], "warnings": []},
  "handoff": {"ok": true, "autoPublish": false, "bundledSlots": 1,
              "dates": ["2026-11-23"], "reason": null, "slots": ["..."]}
}
```

Stale não bloqueia o bundle (o bundler já falha fechado por hash na mídia);
o relatório expõe `staleApprovals` para decisão humana. `list`, `render` e
`pipeline` mantêm assinatura, saída e exit codes.

## 7. Testes

```bash
python -m unittest tools/tests/test_approval_cli.py tools/tests/test_factory_cli.py tools/tests/test_handoff_bundler.py -v
# Ran 34 tests — OK (skipped=1)
```

- `test_approval_cli.py` — 14/14: status sem store; decide aprovado/ajuste/
  aguardando; notes obrigatórias em ajuste; hashes do manifesto; `staleApproval`;
  validate reprovando schema/campanha; roundtrip `handoff_bundler.load_approvals`;
  contenção de path; CLI `--json`; escrita atômica sem `.tmp`; migração v1.
- `test_factory_cli.py` — 8 testes: os 6 anteriores + `handoff` com 0 aprovadas
  (JSON limpo e `NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR`) e com campanha
  aprovada em diretório temporário (`bundledSlots >= 1`, `autoPublish: false`).
  `test_02` (render binário) segue `skipped` porque `ffmpeg` não está no PATH
  desta estação.
- `test_handoff_bundler.py` — 12/12, sem regressão.

## 8. Smoke real (dados de produção fictícios versionados)

Sequência executada no checkout com store descartável em
`.workspace/tmp/etapa6-agente3-smoke/` (removido ao final):

```
decide  -> ok, aprovado, 2026-11-21T01:21:43Z, hashes: narracao/srt/storyboard/video
validate -> ok, total 1, stale [], errors [], warnings []
factory handoff --date 2026-11-23
  -> ok, autoPublish false, audit.aprovadas 1, bundled 1 (slot-001 marca-salao)
  -> mediaCopied true, POSTAGEM-MANUAL.md + copy-pronta.txt + cover.png + handoff-manifest.json
```

Nenhum store permanente foi criado; o arquivo padrão
`<workspace>/tmp/aprovacoes-titular.json` do checkout principal não foi tocado.

## 9. Limites e pendências para a consolidação

1. `review_dashboard.py` não foi alterado; se o time quiser preservar
   `updatedAt` numa reexportação pelo navegador, o conjunto de chaves do POST
   precisa ser estendido pelo dono desse arquivo.
2. `test_factory_cli.test_02` continua dependente de `ffmpeg`; o CI cobre.
3. Stale apenas detecta mudança de hash declarado no manifesto; divergência
   entre arquivo arquivado e manifesto continua sendo bloqueada pelo
   `handoff_bundler` (fail-closed por hash na cópia).

## 10. Handoff de armazenamento

- Raiz usada: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.
- Worktree: `.workspace/worktrees/etapa6-agente3` (existente, preservada).
- Fixtures de teste e smoke: somente em `.workspace/tmp` (ignorado), removidos.
- Ferramentas portáteis: nenhuma.
- Arquivos permanentes do commit: `tools/approval_cli.py`,
  `tools/tests/test_approval_cli.py`, `tools/factory_cli.py`,
  `tools/tests/test_factory_cli.py` e este devlog.
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido
  fora de `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.

### 3.1 Normalização multi-provedor
<!-- devlog-sync:etapa6-agente4.md -->

- `auto` pontua cabeçalhos por marcadores distintos (GA4 usa `Session *`;
  Plausible usa `utm_*` + `visitors`; Umami usa `source/medium/campaign/content` +
  `views/events`). Empate ou zero marcadores vira erro explícito pedindo `--provider`.
- Aliases canônicos aceitam variações reais de exportação: GA4
  `Session manual ad content`/`Session manual content`; Plausible
  `visitors`/`visits`; Umami `views`, `events`; conversões GA4 também aceitam
  `Key events`.
- Números toleram vírgula de milhar e vírgula decimal; linhas inválidas são
  registradas em `dataQuality.invalidRows` em vez de derrubar a execução.

### 3.2 Cruzamento e atribuição

- Chave de junção: `(utm_source, utm_medium, utm_campaign, utm_content)`.
- Fonte primária `04-legendas/calendario-editorial.json`; fallback automático para
  `04-legendas/matriz-utm-consolidada.csv` quando o JSON não existe.
- Linhas sem par vão para `unmatchedRows` com motivo `UTM_NOT_IN_CALENDAR`; a execução
  continua com `ok: true`.
- Chaves duplicadas no calendário são expostas em `dataQuality.duplicateCalendarKeys`.

### 3.3 Hook A/B

- Variante pode vir da coluna `hook_variant_used` do CSV ou de `--hook-log`.
- O log aceita três formatos: lista em `hooks` com `slot_id`, lista com
  `utm_campaign`+`utm_content`, ou mapa direto `{"slot-001": "A"}`.
- Precedência: log manual sobre a coluna do CSV.
- Comparativo `rankings.byHook` só aparece quando há variante informada.

### 3.4 Rankings e relatório

- `rankings.byTenant`, `byChannel`, `byWave` (rótulos fixos
  `Onda 1 9:16` e `Onda 2 1:1/16:9`) e `byHook`, ordenados por conversões e sessões.
- Dimensões são semeadas com todos os valores do calendário (inclusive zero) para
  evidenciar cobertura.
- Saídas em `--out-dir`: `utm-performance-report.json` e `utm-performance-report.md`.
- `financialSimulation: false`; nenhum campo monetário é calculado ou inferido.

### 3.5 Template e contenção

- `--generate-template <csv>` exporta as 40 linhas da matriz com as colunas
  `sessions`, `engaged_sessions`, `conversions` e `hook_variant_used` vazias.
- CSV de entrada, hook log, calendário e `--out-dir` precisam ficar dentro da raiz;
  caminho externo retorna `PATH_OUTSIDE_ROOT` (exit 2).

## 4. Evidências

```
$ python -m unittest tools/tests/test_utm_report_importer.py tools/tests/test_utm_simulator.py -v
Ran 28 tests — OK
# 16 do importador + 12 do simulador

$ smoke end-to-end com o calendário real (CSV GA4 de 7 linhas, 6 casadas)
provider=ga4 ok=True
totals: 7 linhas, 6 casadas, 1 não atribuída, 2490 sessões, 139 conversões (5.58%)
byChannel: youtube 1510/82 (5.43%) · instagram 680/47 (6.91%) · facebook 300/10 (3.33%)
byWave: Onda 1 9:16 2090/99 · Onda 2 1:1/16:9 400/40 (10.0%)
byHook: Hook A 1720/88 · Hook B 680/47
byTenant: marca-salao 2400, clinica-vital 90, demais 0 (semeados)
unmatched: tiktok/bio/camp-xyz/ghost (reportado, sem falhar)
```

O smoke também confirmou `utm-performance-report.md` com tabelas de totais, canal,
onda, tenant, hooks, não atribuídos e qualidade de dados.

## 5. Limitações

- Os aliases cobrem os formatos descritos na tarefa e variações comuns de exportação;
  exportações com cabeçalhos muito diferentes devem usar `--provider` explícito ou
  ganhar novo alias.
- O importador exige arquivos dentro da raiz do projeto (regra de portabilidade);
  exports baixados devem ser movidos para `.workspace/tmp/` antes de rodar.
- Nenhuma receita, ROAS ou cobrança é simulada; o relatório é descritivo.
- `test_srt_formatter.py`, `test_approval_cli.py` e `test_workspace_doctor.py` são de
  agentes paralelos e podem ainda não existir nesta branch; foram adicionados ao CI
  conforme o contrato de integração.

## 6. Handoff

- Branch `codex/etapa6-agente4` com commit limpo.
- Verificação rápida:
  `python tools/utm_report_importer.py --root . --metrics-csv <csv> --out-dir .workspace/tmp/utm-report/<semana> --json`
- `contexto_projeto.md` não foi editado; este devlog é a fonte para `devlog_sync.py`
  na consolidação.

### Novo — `tenants/estudio-flow/campaigns/camp-saas-demo-estudio-flow-002.json`
<!-- devlog-sync:etapa6-agente5.md -->

`SAAS-DEMO-ESTUDIO-FLOW-002`, `tenantId: "estudio-flow"`, `preset: "saas-demo"`, 6 cenas,
`format.duration: 30.0` (soma exata das durações), `1080x1920`, 30 fps, `h264`, `yuv420p`.

| # | ID | Tempo | Duração | Superfície / rota | Foco |
| --- | --- | --- | --- | --- | --- |
| 1 | `cena-01-hook` | 0–4s | 4.0s | `marca` | abertura da rotina da equipe |
| 2 | `cena-02-grade` | 4–10s | 6.0s | `manager-agenda` / `/gestor/turmas` | grade do dia (`turma-ef-001`) |
| 3 | `cena-03-filtro` | 10–15s | 5.0s | `manager-agenda` / `/gestor/turmas` | filtro por instrutora Clara Nogueira (`inst-ef-003`, `turma-ef-003`) |
| 4 | `cena-04-status` | 15–20s | 5.0s | `manager-agenda` / `/gestor/turmas` | presença/status manual: Aguardando → Confirmado |
| 5 | `cena-05-busca` | 20–26s | 6.0s | `manager-agenda` / `/gestor/turmas` | busca por aluna: Andréia Silveira (`turma-ef-004`) |
| 6 | `cena-06-cta` | 26–30s | 4.0s | `marca` | `estudioflow.com.br` |

- **Nenhuma cena de `/aulas`**: não há `surface: "public-booking"`, nenhuma rota
  `/aulas/[studioId]`, nenhum `bookingCase`, nenhum `booking-selection`/`booking-confirm`/
  `booking-success` e nenhum `baseCaptureRef` herdado. Rotas presentes: apenas `/gestor/turmas`
  e o domínio institucional no CTA.
- `artifacts` segue o padrão da campanha 001 (vídeo, SRT, narração, manifesto, storyboard com
  timestamps 2/8/16/24s). `subtitleStyle` idêntico ao brand-kit.

### Alterado — `tenants/estudio-flow/campaigns/README.md`

Preservadas as linhas originais da campanha 001; acrescentada a entrada da campanha 002 com as
superfícies, a instrutora/aluna em destaque, a ausência de `/aulas` e a nota sobre o limite de 48
caracteres no SRT.

### Entregas — `02-reels-shorts/deliveries/estudio-flow/camp-saas-demo-estudio-flow-002/`

Geradas pelo render: `camp-saas-demo-estudio-flow-002.mp4` (não versionado, arquivado em
`.workspace/archives/`), `.srt`, `_narracao.txt`, `manifest.json`, `derivatives.json`,
`preview-storyboard.png`, `cover.png`, `thumb-16x9.png` e `preview-formats.png`.

## 4. Conformidade editorial e limite do SRT

Auditoria pré-render feita com o mesmo pipeline de `preset_runner._audit_texts` e
`tenant_validator.validate_text_against_guardrails(check_ui_elements=True)` sobre todos os campos
de texto das cenas, sobre o SRT gerado e sobre a narração: **0 violações**.

- Sem promessa de cura clínica, tratamento médico, emagrecimento ou resultado imediato.
- Sem WhatsApp, SMS, lembretes, 24h, automação/confirmação automática.
- Sem redução de faltas, zero faltas ou `no-show`.
- Sem checkout, pagamento, cobrança ou cartão; nenhuma tela de pagamento em cena.
- Status e presença sempre descritos como **manuais**.

O `preset_runner.build_srt_text()` usa o campo `caption` literalmente, sem quebra automática —
por isso todas as captions foram escritas com até 48 caracteres. Verificação no arquivo entregue:

```
linhas: 6  max: 44  acima_de_48: []
```

Legendas entregues (comprimentos 40, 41, 44, 44, 43 e 37): grade do dia, filtro da Clara,
mudança de status, busca da Andréia e CTA. Tempos do SRT conferidos: 0–4, 4–10, 10–15,
15–20, 20–26 e 26–30s, todos dentro dos 30.0s do vídeo.

## 5. Validação

```bash
python tools/tenant_validator.py --tenant estudio-flow --json
```

Resultado: `ok: true`, `errors: []`, com brand-kit, guardrails e fixture localizados em
`tenants/estudio-flow/`.

Pré-auditoria adicional da campanha (normalizando `start`/`end` como o render faz): 6 cenas,
soma `30.0s` = `format.duration`, superfícies apenas `manager-agenda` e `marca`, rotas sem
`/aulas`, `max_len: 44`, `over_48: []`, `guardrail_violations: []`.

## 6. Ambiente ffmpeg, render e derivados

O ffmpeg não está no PATH do shell, mas os binários portáteis 9.1 (gyan.dev) estão em
`<MAIN_ROOT>/.workspace/tools/ffmpeg/`. Foram expostos **somente no PATH do processo** da
tarefa (sem `setx`, sem PATH global, sem download e sem arquivo fora de `<RAIZ>`).

```bash
python tools/factory_cli.py render --tenant estudio-flow \
  --campaign camp-saas-demo-estudio-flow-002 \
  --report .workspace/tmp/etapa6-agente5/report.json --json
```

Resultado: `ok: true`, `mode: filtered`, 1 tenant, 1 campanha. `1080x1920`, `h264`,
`yuv420p`, 30 fps, `30.0s`, `videoStreams: 1`, `audioStreams: 0`, `allowAudioTrack: false`.
O relatório foi gravado em `.workspace/tmp/etapa6-agente5/report.json`;
`02-reels-shorts/deliveries/factory-report.json` **não foi tocado**.

Hashes registrados no manifesto: vídeo `d993c9dcb166bfaa3087b55036551df5d17e3115d3fcf70b5c97a975ab67ca53`,
SRT `3421fdf8e63322d116f047dcc6af402b596c16ccbe95141144994ac6236e211f`,
narração `edaf9602a4e65cfe9730dceb7efe032abda2de206708f3a4ad619dfd20843d63`,
storyboard `fafc9cfdfaeaeadc83f7434154377356f0b0c7184827f8092ff7949b03943775`.

```bash
python tools/derivative_formats.py --tenant estudio-flow \
  --campaign camp-saas-demo-estudio-flow-002 --json
```

Resultado: `ok: true`, `total: 1`, `generated: 1`, `skipped: 0`, `errors: []`. Formatos
`1x1`, `16x9`, `cover`, `thumb-16x9` e `preview-formats`, todos com `audioStreams: 0` e
`appliedAudioPolicy: "-an"`.

Verificação explícita com `ffprobe -v error -select_streams a -show_entries stream=index,codec_name`
sobre o MP4 arquivado: **nenhuma saída**, confirmando zero faixas de áudio. Nenhum áudio foi
gerado, preservado ou inserido; a narração segue apenas como texto externo em português brasileiro.

## 7. Handoff de armazenamento

- Raiz usada nesta estação: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`
  (valor de `git rev-parse --show-toplevel` no checkout principal).
- Worktree: `<RAIZ>/.workspace/worktrees/etapa6-agente5` (preexistente; não removida).
- Auxiliares criados: `<RAIZ>/.workspace/tmp/etapa6-agente5/` (relatório de render) e
  `<RAIZ>/.workspace/worktrees/etapa6-agente5/.workspace/tmp/preset-runner-*/` (cenas e
  artefatos intermediários) — todos sob `<RAIZ>/.workspace/`, ignorados pelo Git.
- Arquivos permanentes adicionados ao Git: campanha 002, `README.md` atualizado, pacote de
  entrega da campanha 002 e este devlog, todos na branch `codex/etapa6-agente5`.
- Arquivos mantidos somente em `.workspace/`: relatório de render, arquivos temporários do
  preset runner, MP4 arquivado e derivados MP4 — por política do `.gitignore`, com hashes e
  metadados preservados nos manifestos versionados.
- Worktrees criadas: nenhuma. Worktrees removidas: nenhuma. Ferramenta portátil usada:
  ffmpeg/ffprobe 9.1 (gyan.dev) já presentes em `<MAIN_ROOT>/.workspace/tools/ffmpeg`.
- Temporários removidos: `tools/__pycache__/` da worktree.
- `git status --short` final da worktree: limpo após o commit (sem arquivos rastreados pendentes).
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de
  `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.

### Agente 6 — `workspace_doctor`: diagnóstico e higiene do `.workspace/` compartilhado
<!-- devlog-sync:etapa6-agente6.md -->

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa6-agente6`  
> **Worktree:** `.workspace/worktrees/etapa6-agente6`  
> **Base:** `main` @ `8a1b361`  
> **Escopo:** CLI/API 100% stdlib de higiene do workspace, auditoria de mídia local contra hashes versionados, limpeza segura de `tmp/` e suíte automatizada

## 1. Objetivo

Entregar, no território exclusivo do Agente 6 da Etapa 6, uma ferramenta de confiabilidade local que audite o `.workspace/` do checkout **principal** (compartilhado por todas as worktrees): presença/versão do FFmpeg portátil, integridade das mídias em `.workspace/archives/` contra os SHA-256 declarados nas entregas versionadas, higiene de worktrees/arquivos não rastreados e limpeza restrita de subdiretórios descartáveis de `.workspace/tmp/`. O relatório completo fica neste devlog para ser transferido ao `contexto_projeto.md` pelo `devlog_sync.py` — `contexto_projeto.md` **não** foi editado diretamente.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/workspace_doctor.py` | novo | API `run_workspace_doctor(root=".", clean_tmp=False)` e CLI `python tools/workspace_doctor.py [--check \| --clean-tmp] [--json] [--root DIR]`; 4 seções (ffmpeg, archives, worktrees, tmp), relatório `schemaVersion: 1`, exit codes 0/1/2; somente biblioteca padrão |
| `tools/tests/test_workspace_doctor.py` | novo | 11 testes em `TemporaryDirectory`, cobrindo auditoria íntegra, hash corrompido, preservação de protegidos no `--clean-tmp`, contenção de caminhos, CLI `--json`/`--clean-tmp`, FFmpeg ausente, higiene de worktrees e avisos de mídia ausente/não declarada |
| `.workspace/devlogs/etapa6-agente6.md` | novo | este relatório completo |

## 3. Desenho e decisões

- **Raiz principal por Git:** `_resolve_main_root()` usa `git rev-parse --git-common-dir` (o mesmo mecanismo de `bootstrap_ffmpeg.py`), de modo que, mesmo executado dentro de uma worktree, o doutro aponte para o `.workspace/` compartilhado. Sem Git, cai para o diretório informado.
- **Separação `source_root` × `resolution_root` (correção encontrada na validação real):** os manifestos `manifest.json`/`derivatives.json` são **versionados** e podem ser lidos de uma worktree, mas as mídias declaradas vivem em `.workspace/archives/` da **raiz principal**. Os caminhos `.workspace/archives/...` são resolvidos contra `MAIN_ROOT`, e as chaves de comparação são relativas a `MAIN_ROOT`. Sem essa separação, a primeira execução real acusava 70 erros falsos de `PATH_OUTSIDE_ARCHIVES`.
- **Cruzamento de hashes:** `manifest.json → artifacts.video.archivePath` e `derivatives.json → source.path` alimentam a categoria `9:16`; `derivatives.json → derivatives.{1x1,16x9,cover,thumb-16x9,preview-formats}` alimentam as demais. Caminhos declarados fora de `archives/` são recusados (`PATH_OUTSIDE_ARCHIVES`); hashes conflitantes para o mesmo arquivo geram `DECLARACAO_CONFLITANTE`.
- **Severidades:** divergência de SHA-256, FFmpeg ausente/inválido e worktree registrada sem diretório são `error`. Mídia declarada mas ausente (política do projeto: mídia local não é versionada), mídia não declarada, arquivos não rastreados e worktree órfã são `warning` — `ok` depende somente de `error`.
- **`--clean-tmp` restrito:** percorre apenas filhos diretos de `<MAIN_ROOT>/.workspace/tmp/`, remove somente diretórios, nunca arquivos soltos. `aprovacoes-titular.json` está em `PROTECTED_TMP_NAMES`; links/junções e alvos cujo `realpath` saia de `tmp/` são ignorados. `archives/`, `tools/` e `devlogs/` são irmãos de `tmp/`, estruturalmente inalcançáveis.
- **Isolamento dos testes:** `TemporaryDirectory(dir=<RAIZ>/.workspace/tmp/etapa6-agente6-doctor-tests/)` mantém todos os artefatos sob a raiz; `_resolve_main_root` e `_probe_version` são substituídos por `mock.patch.object` em `setUp` para que nenhum teste toque o `.workspace/` real ou execute binários.

## 4. Evidências de validação (nesta estação)

```
$ python -m unittest tools/tests/test_workspace_doctor.py -v
Ran 11 tests — OK   (PYTHON_EXIT_CODE=0)
  test_01_auditoria_integra_e_formatos ........................ ok
  test_02_detecta_hash_corrompido_em_archive .................. ok
  test_03_clean_tmp_preserva_protegidos ....................... ok
  test_04_clean_tmp_preserva_arquivos_soltos .................. ok
  test_05_declaracao_fora_de_archives_e_recusada .............. ok
  test_06_contenção_de_alvos_do_clean_tmp ..................... ok
  test_07_cli_json ............................................ ok
  test_08_cli_clean_tmp_json ................................... ok
  test_09_ffmpeg_ausente ....................................... ok
  test_10_worktrees_e_nao_rastreados ........................... ok
  test_11_midia_nao_declarada_e_midia_ausente_sao_avisos ....... ok

Execução real somente leitura (python tools/workspace_doctor.py --root . --json,
a partir da worktree, após a correção source_root/resolution_root):
  exit=1, ok=False, errors=1, warnings=1
  ffmpeg: ffmpeg.exe e ffprobe.exe presentes, versão 9.1-essentials_build-www.gyan.dev
  archives: 60 declarados, 60 presentes, 59 verificados, 1 divergente, 0 ausentes
  por formato: 9:16=10, 1x1=10, 16x9=10 (cover/thumb/preview também 10 cada)
  worktrees: 9 registradas, 0 órfãs, 4 arquivos não rastreados
  único error: ARCHIVE_HASH_DIVERGENTE em
    .workspace/archives/camp-shorts-completo-multitrack-001/camp-shorts-completo-multitrack-001.mp4
    (declarado em multitrack-hub/camp-shorts-completo-multitrack-001:derivatives.source)
```

O `ARCHIVE_HASH_DIVERGENTE` é um achado legítimo do auditor sobre mídia local não versionada desta estação (os derivados do Multitrack Hub foram regenerados em rodadas anteriores); **não** foi alterado — `.workspace/archives/` está fora do território do Agente 6. O `ARQUIVOS_NAO_RASTREADOS` são os próprios arquivos desta entrega antes do commit (`tools/workspace_doctor.py`, `tools/tests/test_workspace_doctor.py` e dois `__pycache__`, removidos antes de commitar).

## 5. Incidente registrado (transparência)

Na **primeira** execução da suíte, antes do `mock.patch.object(wd, "_resolve_main_root", ...)` em `setUp`, os testes de `--clean-tmp` rodaram com `workspace_root` apontando para a raiz principal real e removeram os **subdiretórios** então presentes em `<RAIZ>/.workspace/tmp/` (diretório hoje vazio). Eram artefatos locais ignorados pelo Git — pertencentes a rodadas anteriores (por exemplo simulações UTM, sandbox editorial-qa e staging de bootstrap) — e nenhum arquivo versionado foi afetado. Não há como restaurá-los; o isolamento foi corrigido imediatamente e a suíte foi reexecutada com 11/11 OK sem novo acesso ao `.workspace/` real. Sinalizo o fato para que outras estações/agentes saibam que evidências locais ali depositadas podem ter sido perdidas nesta sessão.

## 6. Limitações

- Não foi necessário baixar ferramentas portáteis: o FFmpeg já existe em `<RAIZ>/.workspace/tools/ffmpeg/` e foi apenas inspecionado.
- A auditoria compara hash dos arquivos **presentes**; encoded characteristics (fps/codec/dimensões) e `-an` continuam sendo verificados pelo `release_audit.py`. Mídia ausente permanece como aviso, conforme a política do projeto.
- Suíte roda em Windows (py 3.15 nesta estação) com nomes `ffmpeg.exe`/`ffprobe.exe`; em outras plataformas a ferramenta procura os nomes sem extensão.
- `contexto_projeto.md` não foi tocado; a consolidação deve ser feita por `python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md --pattern "etapa6-agente*.md"`.

## 7. Arquivos não tocados

`contexto_projeto.md`, `tenants/`, `02-reels-shorts/deliveries/`, `.workspace/archives/`, `.workspace/tools/`, a worktree principal e as worktrees dos outros agentes não foram alterados por esta entrega (com a exceção transitória registrada na Seção 5, já contida). Nenhum post, campanha, calendário ou portal foi publicado ou editado.

## 8. Handoff

- Branch pronta para merge: `codex/etapa6-agente6` (commit com os 3 arquivos do território).
- Verificação rápida: `python -m unittest tools/tests/test_workspace_doctor.py -v`.
- Diagnóstico local: `python tools/workspace_doctor.py --check --json` (somente leitura).
- Limpeza segura: `python tools/workspace_doctor.py --clean-tmp --json`.
- A divergência de hash do Multitrack Hub detectada na estação deve ser tratada pelo responsável de mídia, não por este agente.

### Etapa 6 — Agente 7: coerência de hooks A/B e aderência de uiLabels
<!-- devlog-sync:etapa6-agente7.md -->

- **Data:** 2026-11-20
- **Papel:** Engenheiro Sênior de Qualidade Editorial (Agente 7 de 8, Etapa 6, em paralelo).
- **Branch isolada:** `codex/etapa6-agente7`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa6-agente7` (já existia; reutilizada, não recriada, conforme regra 1 do pedido).
- **Base:** `main` @ `8a1b361cfda236ed9cdb553bdd81201b146f9bca` (release da Etapa 5B).
- **Território exclusivo:** `tools/editorial_qa.py`, `tools/tests/test_editorial_qa.py` e `.workspace/devlogs/etapa6-agente7.md`.
- **Protocolo `contexto_projeto.md`:** não editado. Este devlog é a fonte completa para o `devlog_sync.py` na consolidação.

## 1. Partida

O `tools/editorial_qa.py` existente (Etapa 5B, Agente 8) já tinha cinco lentes e a API pública
`run_editorial_qa(root=".", strict=False, tenant=None)`. Antes de alterar, foi confirmado que
os 10 hooks A/B do calendário real são distintos, não vazios e limpos quanto aos guardrails
(30 pares avaliados, zero violações), e que nenhum `brand-kit.json` define `uiLabels` hoje —
portanto as duas novas lentes são no-op no acervo atual e não alteram o resultado das 13
verificações originais.

A API pública foi preservada integralmente: mesma assinatura, mesmo `schemaVersion: 1`, mesmos
códigos de saída (`0` aprovado, `1` reprovado, `2` erro). `CHECK_IDS` passou de 5 para 7 entradas
e `CHECK_NAMES` ganhou os dois rótulos correspondentes; nenhum campo existente foi removido ou
renomeado.

## 2. Novas verificações

### 2.1 `coerencia_hooks_calendario` (lente 6)

Só executa quando `04-legendas/calendario-editorial.json` existe e é legível. Para cada slot com
`tenantId` e `slug`, avalia `hookVarianteA` e `hookVarianteB`:

| Código | Severidade | Condição |
| --- | --- | --- |
| `HOOK_VARIANTE_AUSENTE` | erro | campo ausente, não string ou vazio após `strip()` |
| `HOOK_GUARDRAIL_VIOLACAO` | erro | `validate_text_against_guardrails(texto, guardrails, check_ui_elements=True)` retorna violação |
| `HOOK_VARIANTES_IDENTICAS` | aviso | A e B iguais após `strip()` + `casefold()` |
| `TENANT_INVALIDO` | erro | brand-kit/guardrails do tenant ilegíveis |
| `CALENDARIO_ILEGIVEL` | erro | calendário presente mas inválido |

Os problemas são deduplicados por `(tenant/slug, código, mensagem)` para evitar repetição nas
várias superfícies da mesma campanha, e respeitam o filtro `tenant`. Guardrails são carregados
com cache por execução via `tenant_validator.load_and_validate_tenant(..., strict=False)`.

### 2.2 `aderencia_ui_labels` (lente 7)

Para cada tenant em `tenants/*` com `brand-kit.json` que **defina** `uiLabels`, percorre
recursivamente objetos e listas e valida cada valor textual:

| Código | Severidade | Condição |
| --- | --- | --- |
| `UI_LABELS_TIPO_INVALIDO` | erro | `uiLabels` não é objeto |
| `UI_LABEL_TIPO_INVALIDO` | erro | valor folha não é string |
| `UI_LABEL_VAZIA` | erro | string vazia após `strip()` |
| `UI_LABEL_GUARDRAIL_VIOLACAO` | erro | violação de `forbiddenClaims`/`forbiddenUiElements` |
| `TENANT_INVALIDO` | erro | guardrails do tenant ilegíveis |

Quando `uiLabels` não existe, a lente é aprovada sem problemas. O filtro `tenant` também se
aplica. `validate_brand_kit` sinaliza `uiLabels` como propriedade adicional (schema `additionalProperties: false`),
mas `editorial_qa` usa `strict=False` e consome somente os guardrails, sem reprovar o tenant por isso.

## 3. Arquivos alterados

| Arquivo | Mudança |
| --- | --- |
| `tools/editorial_qa.py` | Docstring atualizada (7 lentes), constantes `CALENDAR_REL`, dois IDs/nomes em `CHECK_IDS`/`CHECK_NAMES`, helpers `_tenant_guardrails`, `_check_calendar_hooks` e `_check_ui_labels`, chamadas das duas lentes em `run_editorial_qa`, descrição da CLI atualizada. |
| `tools/tests/test_editorial_qa.py` | Helpers `_write_json`, `_sandbox_with_calendar`, `_mutate_hooks`, `_add_ui_labels` e 6 novos testes (12 a 17). |
| `.workspace/devlogs/etapa6-agente7.md` | Este relatório completo para consolidação via `devlog_sync.py`. |

## 4. Testes adicionados (6)

1. `test_12_hooks_identicos_sao_aviso` — A == B gera aviso; modo normal aprovado, `--strict` reprova.
2. `test_13_hook_com_termo_proibido_e_erro` — hook com `whatsapp` gera erro e o filtro de tenant isola o problema.
3. `test_14_hook_vazio_e_erro` — `hookVarianteA` em branco gera erro.
4. `test_15_ui_labels_invalidos_sao_erro` — valor vazio, termo proibido e valor não string.
5. `test_16_ui_labels_validos_sao_aprovados` — rótulos válidos, incluindo objeto aninhado.
6. `test_17_acervo_real_novas_lentes_aprovadas` — calendário e brand-kits reais sem problemas nas duas lentes.

Os testes de defeito usam sandbox somente-leitura copiado para `<RAIZ>/.workspace/tmp/editorial-qa/`,
fora do Git; o calendário real é copiado para o sandbox somente nos testes de hooks.

## 5. Evidências

```text
python -m unittest tools/tests/test_editorial_qa.py -v
Ran 19 tests in 21.346s — OK
(13 testes anteriores + 6 novos)

python tools/editorial_qa.py --json
schemaVersion=1; ok=True; checks=7
checkIds=duracao_srt_manifest, legibilidade_mobile, paridade_entregas,
         guardrails_cruzados, integridade_utf8,
         coerencia_hooks_calendario, aderencia_ui_labels
errors=0; warnings=46 (avisos conhecidos de linha longa de SRT)
coerencia_hooks_calendario: status=ok, 0 problemas
aderencia_ui_labels: status=ok, 0 problemas
```

## 6. Limites e governança

- Ferramenta permanece somente leitura: não publica, não agenda, não grava artefatos de campanha.
- Não edita `contexto_projeto.md`, `rastreio-utm.md`, calendário, brand-kits nem matriz UTM.
- Não gera áudio, TTS, música nem faixa sonora (política de vídeo sem áudio).
- Não altera as cinco lentes existentes nem muda a semântica de `strict`/`--tenant`.
- O calendário e os brand-kits reais seguem como estão; nenhum hook ou rótulo foi "corrigido".

## 7. Handoff

Commit realizado apenas nesta branch; consolidação/merge na `main` fica a cargo do titular.
A worktree permanece registrada (remoção exige autorização). Nenhum arquivo relacionado ao
projeto foi criado fora de `<RAIZ>`.

### Devlog — Etapa 6, Agente 8 de 8 (Arquitetura de Documentação e Operações)
<!-- devlog-sync:etapa6-agente8.md -->

- **Data:** 2026-11-20
- **Agente:** Agente 8 de 8 — Arquiteto de Documentação e Operações
- **Branch:** `codex/etapa6-agente8`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa6-agente8` (já existia; criada a partir de `main`)
- **<RAIZ> nesta estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`
- **Base:** `main` em `8a1b361` (conclusão da Etapa 5B), atualizada com `git fetch origin --prune && git pull --ff-only` no início.

## Escopo executado

| Arquivo | Ação |
| --- | --- |
| `docs/guia-operacional-titular.md` | **Criado.** Manual prático da rotina diária e semanal: (1) revisão no portal `review_dashboard.py --serve` com decisões `aguardando`/`aprovado`/`ajuste`, locução externa conferida para tenants `-an`, exportação de aprovações e alternativa `approval_cli.py status`/`decide`; (2) geração do pacote diário com `factory_cli.py handoff --all-approved`, conteúdo do handoff, lembrete de locução externa e regras de publicação manual por rede (`autoPublish: false`); (3) fechamento semanal com `utm_report_importer.py` + `workspace_doctor.py --check` e rotina do playbook de UTM. Inclui checklist copiável e referências internas. |
| `docs/arquitetura-fabrica.md` | Atualizado para Etapas 2–6: diagrama com a camada da Etapa 6, subcomando `handoff` em 2.6, nova seção 2.18 (tabela com `srt_formatter.py`, `approval_cli.py`, `factory_cli.py handoff`, `utm_report_importer.py`, `workspace_doctor.py`, `uiLabels` no brand-kit e o guia), fluxo operacional com passos 17–20, correção de "4 tenants" para 5, novas referências e nota sobre consolidação das suítes da Etapa 6. |
| `README.md` | Link para o guia no início, comandos 17–20 da Etapa 6 nos comandos rápidos, parágrafo "Operação do titular (Etapa 6)" e checklist ampliado com revisão/aprovação → handoff → publicação manual → importação UTM + doctor. |
| `.workspace/devlogs/etapa6-agente8.md` | Este relatório, para ser transferido ao `contexto_projeto.md` por `devlog_sync.py` na consolidação. `contexto_projeto.md` **não** foi editado diretamente. |

## Verificações exigidas

Script temporário executado de `<RAIZ>/.workspace/tmp/etapa6-agente8/validate_docs.py` sobre os três documentos versionados:

- **Encoding UTF-8:** 3/3 arquivos decodificam estritamente como UTF-8, sem BOM e sem `\ufffd`/mojibake.
- **Links internos:** todos os links relativos dos três arquivos resolvem para arquivos existentes (incluindo os links novos para `guia-operacional-titular.md`, `analytics-utm-playbook.md` e `05-review-portal/README.md`). URLs externas e âncoras foram ignoradas.
- **Caminhos absolutos de usuário:** nenhuma ocorrência de `C:\...`, `/home/`, `/Users/` ou similar. Os únicos `/tmp/` encontrados são parte de `.workspace/tmp/...`, que é caminho relativo portátil; o validador foi ajustado com lookbehind para não gerar falso positivo. Resultado final: **0 problemas**.
- Temporários removidos ao final; nenhum `__pycache__` deixado na worktree.

## Achado importante para a consolidação

No commit-base `8a1b361`, **os módulos da Etapa 6 ainda não existiam na `main` nem nas worktrees irmãs**: não havia `tools/srt_formatter.py`, `tools/approval_cli.py`, `tools/utm_report_importer.py`, `tools/workspace_doctor.py`, nem chave `uiLabels` nos brand-kits/schema, e `factory_cli.py` só registrava os subcomandos `list`, `render` e `pipeline`. Portanto:

- A documentação foi escrita a partir das **interfaces explicitadas no pedido** e das convenções já consolidadas das Etapas 4/5B (portal, aprovações v2, handoff_bundler e playbook UTM).
- Onde uma opção opcional não foi especificada, o guia manda conferir `--help` — não foi inventada nenhuma bandeira como fato verificado.
- As seções 2.18 do Guia e da Arquitetura registram explicitamente esse estado de consolidação. **Ação para o integrador:** ao mergear as branches dos agentes da Etapa 6, reconferir cada assinatura de CLI e atualizar o guia se algum nome/opção divergir.

## Segurança e escopo

- Nenhuma ferramenta de publicação foi executada; nada foi publicado, agendado ou rascunhado.
- Nenhum áudio, TTS ou trilha foi gerado; a regra de vídeo sem áudio e a locução externa foram reforçadas no manual.
- Nenhum contrato, SRT, manifesto ou pacote social foi alterado; nenhum caminho absoluto de estação foi gravado em documento versionado.
- Território respeitado: apenas os quatro arquivos acima.

## 1. Contexto

A versão consolidada da Etapa 5B já trazia o `factory_cli.py pipeline` com 9 estágios
(contratos, render, derivados, cards, pacotes, calendário, portal, UTM e release gate),
o `utm_simulator`, o playbook de analytics e os triggers de `01-insta-stories/deliveries/**`.
Esta rodada fecha a integração com o módulo paralelo de QA editorial.

## 2. Alterações

| Arquivo | Mudança |
| --- | --- |
| `tools/factory_cli.py` | novo estágio opcional `editorial-qa` entre `utm` e `release-gate`; resolução via `importlib` com adaptador para `run_editorial_qa`/`audit_editorial_qa`/`run_qa`/`audit`; `counts.editorialQa`; saída humana atualizada |
| `tools/tests/test_factory_cli.py` | `test_02` (render binário) com `skipUnless` quando `ffmpeg`/`ffprobe` ausentes; listas de estágios atualizadas com `editorial-qa`; `editorial-qa` aceito como `ok` ou `skipped` (módulo paralelo) |
| `.github/workflows/local-render-validation.yml` | `tools/tests/test_editorial_qa.py` incluído na suíte explícita do CI |
| `.workspace/devlogs/etapa5-agente5.md` | este relatório |

Contrato assumido para o módulo paralelo (documentado no erro do estágio):

```
tools/editorial_qa.py :: run_editorial_qa(root=".") -> dict
# retorno: {"ok": bool, "totalChecked": int?, "findings": list?, "warnings": int?, "reportPath": str?}
```

Se o módulo não existir, o estágio fica `skipped` e o pipeline segue. Se existir e
retornar `ok: false`, o estágio falha com `EDITORIAL_QA_REPROVADO` e o pipeline
retorna `ok: false` (fail-closed apenas para o módulo presente).

## 3. Evidências

```
$ python -m unittest tools/tests/test_factory_cli.py -v
Ran 6 tests — OK (skipped=1)
# skip: ffmpeg/ffprobe indisponiveis nesta estacao; render binario nao executavel

$ python tools/factory_cli.py pipeline --all --skip-render --json
ok=True
contratos ok · render ok · derivados ok · cards-estaticos ok · pacotes ok
calendario ok · portal ok · utm ok · editorial-qa skipped · release-gate ok
counts: 5 tenants, 10 campanhas, 10 entregas, 10 derivados, 70 cards,
        10 pacotes, 40 slots, 10 campanhas no portal, 40 URLs UTM, 7/7 domínios ok

$ probe com módulo fake (fora do Git, em .workspace/tmp, removido)
ok-path:   editorial-qa ok (totalChecked=10), pipeline ok=True
fail-path: editorial-qa failed (EDITORIAL_QA_REPROVADO), pipeline ok=False
```

## 4. Limitações

- `ffmpeg`/`ffprobe` continuam fora do PATH nesta estação e a worktree não possui
  `.workspace/tools/ffmpeg`; por isso o teste de render binário foi marcado como
  `skip` (permitido pelo contrato desta tarefa). O caminho real roda no CI.
- `tools/editorial_qa.py` e `tools/tests/test_editorial_qa.py` ainda não existem
  nesta branch; o estágio fica `skipped` e a entrada do CI passa a valer assim que
  o módulo do agente paralelo for integrado.

## 5. Handoff

- Branch `codex/etapa5b-agente4` com commit limpo.
- Verificação rápida: `python tools/factory_cli.py pipeline --all --skip-render --json`
  deve listar 10 estágios, com `editorial-qa` em `ok` ou `skipped`.
- Nenhum arquivo fora do território exclusivo foi alterado; `contexto_projeto.md`
  permanece intacto.

### Etapa 5B — Agente 5 de 8: auditoria, validação e render do 5º tenant (`clinica-vital`)
<!-- devlog-sync:etapa5-agente6.md -->

Data: 2026-11-20
Branch isolada: `codex/etapa5b-agente5`
Worktree: `<RAIZ>/.workspace/worktrees/etapa5b-agente5` (já existia; **não** foi recriada)
Base: `main` @ `3f8cb1a` — "chore(release): conclui Etapa 5B (5 tenants, 10 campanhas, ffmpeg portatil e handoff)"
Raiz real desta estação: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

## 1. Objetivo e isolamento

Atuar como Arquiteto de Conteúdo Multi-Tenant, seguindo `schemas/brand-kit.schema.json`,
`schemas/guardrails.schema.json` e o tenant de referência `tenants/estudio-flow/`.

- `git fetch origin --prune --no-tags` executado no início; sem alteração de branch ou HEAD.
- Worktree `etapa5b-agente5` conferida por `git worktree list --porcelain` antes de qualquer escrita:
  já registrada no commit `3f8cb1a`, na branch `codex/etapa5b-agente5`. A regra 1 do pedido
  ("criar se não existir") não se aplicou; nenhuma worktree foi criada, movida ou removida.
- Território respeitado: `tenants/clinica-vital/**`,
  `02-reels-shorts/deliveries/clinica-vital/**` e este devlog.
  Não houve escrita em `contexto_projeto.md`, `factory-report.json`, schemas, ferramentas
  ou outros tenants. Nenhuma outra worktree foi aberta para edição.

## 2. Achado principal: tenant já integrado na base

Ao abrir a worktree, `tenants/clinica-vital/` já continha a estrutura completa. A procedência
foi confirmada no Git:

```
47e0f0e feat(etapa5b-agente3): onboarding do tenant clinica-vital (nicho regulado)
3f8cb1a chore(release): conclui Etapa 5B (5 tenants, 10 campanhas, ffmpeg portatil e handoff)
```

Ou seja, o trabalho do Agente 3 já estava consolidado na `main` antes desta sessão.
**Não houve recriação, sobrescrita ou duplicação de arquivos do tenant.** Em vez disso, o
escopo foi convertido em auditoria formal contra o contrato pedido:

| Item exigido | Situação observada |
| --- | --- |
| `brand-kit.json` — tenantId, brandName, displayTitle, monogram, tagline, domínio | conferido, literal do pedido preservado |
| Paleta clínico-moderna (`#0EA5E9`, `#14B8A6`, `#F59E0B`, `#0B1324`) | conferida, com `palette.rgb` completo |
| `headerOverlay.enabled: true`, `label: "CLINICA VITAL"` | conferido |
| `defaultPreset: "saas-demo"` | conferido |
| UTM `instagram` / `reels` / `cv` | conferido no formato exigido pelo schema (`utm_source`, `utm_medium`, `utm_campaign_prefix`) |
| Guardrails clínicos (cura, diagnóstico online, antes/depois, resultado estético, sem dor, WhatsApp/SMS/lembretes 24h, faltas, faturamento) | presentes em `forbiddenClaims` |
| UI proibida (pagamento, prontuário, receita digital, fotos antes/depois, "Meu Salão", "E2E", "Lorem ipsum") | presente em `forbiddenUiElements` |
| Separação `/avaliacao/[clinicId]` × `/gestor/consultas` | presente em `routeRules` (`public-booking` × `manager-agenda`) |
| `allowAudioTrack: false` / `-an` | presente em `audioPolicy` |
| Fixture: 4 especialistas, 5 procedimentos com duração e BRL, grade diária | conferido, com chaves `profissionais`, `servicos`, `agenda.atendimentos`, `booking.rota` |
| `campaigns/README.md` + 2 campanhas `30.0s`, 6 cenas, `saas-demo` | conferido |
| Campanha 001 — marcação em `/avaliacao/clinica-vital-centro` + recepção em `/gestor/consultas` (Patricia Monteiro) | conferido (`bookingCase`, cenas 02–05) |
| Campanha 002 — rotina exclusiva da recepção, sem `/avaliacao` | conferido (4 cenas `manager-agenda`) |

Adaptações ao contrato já aplicadas na base e confirmadas nesta auditoria: o pedido trouxe
`utmDefaults` na forma curta (`source`/`medium`/`campaignPrefix`), mas o schema exige
`utm_source`/`utm_medium`/`utm_campaign_prefix` e proíbe propriedades adicionais; da mesma forma,
`headerOverlay` exige `badgeText`, `bgColor` e `textColor`. Os valores pedidos foram preservados
nas chaves do schema, idênticas aos demais tenants.

## 3. Validação de contratos

Comandos executados dentro da worktree:

```bash
python tools/tenant_validator.py --tenant clinica-vital --json
python tools/tenant_validator.py --all --json
```

Resultado do primeiro: `ok: true`, `errors: []`, com `brandKitPath`, `guardrailsPath` e
`fixturePath` apontando para `tenants/clinica-vital/`.

Resultado do segundo: `ok: true` para **5 tenants**, todos com `errors: []`:

`clinica-vital`, `estudio-flow`, `marca-salao`, `meu-salao`, `multitrack-hub`.

## 4. Ambiente ffmpeg — disponibilidade e exposição controlada

No shell nu, `Get-Command ffmpeg` não retorna binário e
`build_video.get_ffmpeg()` falha com:

```
DeliveryError: ffmpeg nao encontrado no PATH; instale ou exponha o binario antes de exportar
```

Contudo, o bootstrap do Agente 1 deixou os binários portáteis versionados no repositório,
em `<RAIZ>/.workspace/tools/ffmpeg/ffmpeg.exe` e `ffprobe.exe` (ffmpeg 9.1 gyan.dev).
Observe-se que `render_local.ensure_video_tools()` procura essa pasta sob a **raiz do checkout**,
que nesta sessão é a worktree; por isso foi necessário expor o diretório portátil no PATH
**apenas do processo** (sem `setx`, sem alterar PATH global e sem criar nada fora de `<RAIZ>`):

```powershell
$env:PATH = "<RAIZ>/.workspace/tools/ffmpeg;" + $env:PATH
python -c "import sys; sys.path.insert(0,'tools'); import build_video; print(build_video.get_ffmpeg())"
# -> <RAIZ>/.workspace/tools/ffmpeg/ffmpeg.EXE
```

Com essa exposição, a condição do pedido ("ffmpeg disponível no ambiente") foi satisfeita e o
render foi executado — não foi necessário diferir para a consolidação pós-bootstrap.

## 5. Render e derivados

```bash
python tools/factory_cli.py render --tenant clinica-vital \
  --report .workspace/tmp/etapa5b-agente5/report.json --json
```

Resultado: `ok: true`, `mode: filtered`, 1 tenant, 2 campanhas. Para cada uma:
`1080x1920`, `h264`, `yuv420p`, `30.0s`, `videoStreams: 1`, `audioStreams: 0`,
`allowAudioTrack: false`. O relatório ficou em `.workspace/tmp/etapa5b-agente5/report.json`,
dentro da worktree — `02-reels-shorts/deliveries/factory-report.json` **não foi tocado**.

- `SAAS-DEMO-CLINICA-VITAL-001` — sha256 do vídeo `39e2841059156d074473556a2c3339441a3ba2f139cfcd2e153903b60bd603af`.
- `SAAS-DEMO-CLINICA-VITAL-002` — sha256 do vídeo `f4c29946494b3fd42cf570c25222f1d88c2d30b180878de714434485e4f68cdd`.

```bash
python tools/derivative_formats.py --tenant clinica-vital --json
```

Resultado: `ok: true`, `total: 2`, `generated: 2`, `skipped: 0`, `errors: []`.
Formatos `1x1`, `16x9`, `cover`, `thumb-16x9`, `preview-formats` para as duas campanhas,
todos com `audioStreams: 0` e `appliedAudioPolicy: "-an"`.

Verificação de entrega: `git diff` sobre `02-reels-shorts/deliveries/clinica-vital/` ficou
**vazio** — o rerender foi byte-a-byte idêntico ao já versionado no commit de release. Não houve
churn de manifests, SRT, narração, storyboards ou PNGs. Os MP4 não são versionados (o `.gitignore`
os ignora); os manifests preservam hash, ffprobe e comando reproduzível, e as cópias ficam em
`.workspace/archives/<slug>/` sob a raiz. Nenhum áudio foi gerado, preservado ou inserido.

## 6. Arquivos alterados nesta sessão

- Novo: `.workspace/devlogs/etapa5-agente6.md` (este relatório).
- Nenhum arquivo em `tenants/clinica-vital/` ou `02-reels-shorts/deliveries/clinica-vital/`
  precisou ser criado ou modificado: o base já estava conforme e o rerender foi determinístico.
- Cache `tools/__pycache__/` gerado pelas execuções Python foi removido na limpeza.
- `factory-report.json`, `contexto_projeto.md`, schemas, ferramentas e outros tenants: intactos.

## 7. Handoff de armazenamento

- Raiz usada nesta estação: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`
  (valor de `git rev-parse --show-toplevel` no checkout principal).
- Worktree utilizada: `<RAIZ>/.workspace/worktrees/etapa5b-agente5` (preexistente; não removida).
- Diretórios auxiliares criados nesta tarefa: `<RAIZ>/.workspace/tmp/etapa5b-agente5/`
  (relatório de render) e arquivos temporários do preset runner sob a worktree — todos dentro
  de `<RAIZ>/.workspace/`, todos ignorados pelo Git.
- Arquivo permanente adicionado ao Git: apenas este devlog, na branch `codex/etapa5b-agente5`.
- Worktrees criadas: nenhuma. Worktrees removidas: nenhuma. Ferramentas portáteis usadas:
  ffmpeg/ffprobe 9.1 (gyan.dev) já presentes em `<RAIZ>/.workspace/tools/ffmpeg`, sem download.
- Temporários removidos ao final: `tools/__pycache__/` da worktree; arquivos de execução do
  preset runner permanecem sob `.workspace/tmp/` por serem evidência local ignorada.
- `git status --short` final da worktree: limpo após o commit (sem arquivos rastreados pendentes).
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de
  `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.

### Devlog — Etapa 5B / Agente 6 (qualidade e documentação técnica)
<!-- devlog-sync:etapa5-agente7.md -->

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa5b-agente6`  
> **Worktree:** `.workspace/worktrees/etapa5b-agente6`  
> **Base:** `main` @ `3f8cb1a`  
> **Escopo:** suíte de contratos de tenants robusta a 4/5 tenants, cobertura do nicho regulado `clinica-vital` e guia de novo nicho

> Nota de nome: o arquivo segue literalmente o caminho `.workspace/devlogs/etapa5-agente7.md` indicado na tarefa, embora esta seja a entrega do Agente 6.

## 1. Objetivo

Atuar como Engenheiro de Qualidade e Documentação Técnica na Etapa 5B, dentro do território exclusivo:
fazer a suíte `tools/tests/test_tenant_contracts.py` passar tanto com 4 tenants quanto após a integração do
5º tenant (`clinica-vital`), cobrir o nicho regulado com contratos em memória e com verificação condicional
no disco, e atualizar `docs/guia-novo-nicho.md` com a referência oficial e o fluxo completo pós-criação.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/tests/test_tenant_contracts.py` | evoluído | contagens globais `>= 4`; `test_01` renomeado para `core_tenants` com os quatro tenants originais; `test_07` com `>= 4` e `clinica-vital` condicional; `test_08` reescrito como validação **em memória** (brand-kit + guardrails literais); `test_09` reescrito como validação **condicional no disco** (`Path.exists()` + `skipTest`) cobrindo `load_and_validate_tenant(strict=True)`, fixture e 2 campanhas |
| `docs/guia-novo-nicho.md` | atualizado | `clinica-vital` promovido a **referência oficial** para saúde/estética; novo **Passo 6** com o fluxo pós-criação (`static_cards.py`, `derivative_formats.py`, `publish_pack.py`, `campaign_calendar.py`, `review_dashboard.py`, `release_audit.py`, `devlog_sync.py`); bloco do nicho regulado com o mesmo fluxo completo e nota sobre contagens `>= 4` |
| `.workspace/devlogs/etapa5-agente7.md` | novo | este relatório |

## 3. Decisões de desenho

- **Contagens `>= 4`, nunca `== 5`:** a base desta worktree já contém `clinica-vital` (o commit de release
  `3f8cb1a` registra 5 tenants/10 campanhas), mas a suíte não deve depender disso. `test_01` e `test_07`
  exigem apenas os quatro tenants originais; a presença do 5º é verificada à parte.
- **Contratos clínicos em memória (`test_08`):** os literais de `brand-kit` e `guardrails` são cópias dos
  contratos reais, validados contra os schemas com `validate_brand_kit` / `validate_guardrails_contract`.
  O teste cobre explicitamente o bloqueio de `antes e depois`, `cura garantida`, `diagnostico online`
  (e a variante acentuada) e `lembrete automatico` (e a variante acentuada), elementos de UI proibidos,
  a separação auditável entre `/avaliacao/[clinicId]` (`public-booking`) e `/gestor/consultas`
  (`manager-agenda`) e a política `allowAudioTrack == False` com `-an`, `requireSrt` e narração externa.
  Por não ler `tenants/`, este teste roda inclusive antes do merge do 5º tenant.
- **Disco condicional (`test_09`):** `if not (Path(REPO_ROOT) / "tenants" / "clinica-vital").exists():`
  encerra com `self.skipTest(...)`, que é mais informativo que um `return` silencioso. Quando o diretório
  existe, valida `load_and_validate_tenant("clinica-vital", strict=True)`, a fixture e as duas campanhas
  (tempos, textos contra guardrails, rotas por superfície e caso de booking).
- **Documentação sem inventar CLI:** todas as flags documentadas foram conferidas nos `argparse` das
  ferramentas (`--types` em `static_cards.py`, `--tenant`/`--campaign` em `derivative_formats.py`,
  `--all`/`--tenant`/`--slug` em `publish_pack.py`, `--start-date` em `campaign_calendar.py`,
  `--build`/`--serve` em `review_dashboard.py`).

## 4. Evidências de validação (nesta estação)

```
$ python -m unittest tools/tests/test_tenant_contracts.py -v
Ran 9 tests em ~0,18 s — OK   (PYTHON_EXIT_CODE=0)
  test_01_core_tenants_pass_contract_validation ... ok
  test_02_marca_salao_brand_kit_and_fixture_sync_with_pilot ... ok
  test_03_ns002_artifacts_pass_marca_salao_guardrails ... ok
  test_04_invalid_brand_kit_rejected_by_schema ... ok
  test_05_forbidden_claims_and_ui_elements_blocked_per_tenant ... ok
  test_06_fixture_rejects_generic_or_e2e_placeholders ... ok
  test_07_cli_exit_codes ... ok
  test_08_clinica_vital_regulated_niche_contracts_in_memory ... ok
  test_09_clinica_vital_contracts_and_campaigns_on_disk ... ok

Prova de robustez com 4 tenants (REPO_ROOT apontado para um diretorio temporario
dentro da worktree, com schemas copiados e SEM tenants/clinica-vital):
  IN_MEMORY_WITHOUT_TENANT_DIR=OK
  DISK_TEST_SKIPPED=tenant clinica-vital ainda nao integrado nesta worktree
```

O diretorio temporario dessa prova foi removido ao final; nenhum arquivo de `tenants/` foi criado,
renomeado ou apagado.

## 5. Limitações

- A simulacao de 4 tenants foi feita por substituicao de `REPO_ROOT` em processo isolado, nao por
  remocao do diretorio real (fora do territorio autorizado). Os testes `test_01` e `test_07` foram
  inspecionados e nao exigem `clinica-vital`.
- `test_08` replica os contratos clinicos como literais; se o tenant real mudar, o `test_09` (disco)
  continua sendo a fonte de verdade. A duplicacao e intencional para manter o teste em memoria independente.
- Nao executei render, derivados, cards, pacotes, calendario, portal ou release gate: a tarefa e de
  qualidade/documentacao e os comandos do Passo 6 foram validados apenas quanto as flags.

## 6. Arquivos nao tocados

`contexto_projeto.md` nao foi editado. Nenhum arquivo foi criado em `tenants/`. Nenhuma worktree de outro
agente foi acessada. Nenhum post, campanha, calendario ou portal foi publicado ou alterado.

## 7. Handoff

- Branch pronta para merge: `codex/etapa5b-agente6`.
- Comando de verificacao rapida: `python -m unittest tools/tests/test_tenant_contracts.py -v`.
- Ao integrar, nao ha contagens fixas a ajustar nesta suite (`>= 4` ja cobre 4 e 5 tenants); a
  consolidacao de `tools/tests/test_factory_cli.py` continua sendo responsabilidade do integrador.

### Etapa 5B — Agente 7 de 8: Growth & Analytics (auditoria e simulação UTM)
<!-- devlog-sync:etapa5-agente8.md -->

> O nome de arquivo `etapa5-agente8.md` é o definido no pedido; o executor é o
> **Agente 7** da rodada Etapa 5B (Engenheiro de Growth & Analytics).

- **Branch isolada:** `codex/etapa5b-agente7`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa5b-agente7`
- **Base:** `main` @ `3f8cb1a92755b72a1283a4182acc93b4814df919` (worktree já existia;
  não foi recriada, conforme regra 1 do pedido).
- **Data:** 2026-11-20
- **Território exclusivo:** `tools/utm_simulator.py`,
  `tools/tests/test_utm_simulator.py`, `docs/analytics-utm-playbook.md` e
  `.workspace/devlogs/etapa5-agente8.md`. `contexto_projeto.md` não foi tocado.

## Contexto de partida

Já existia na main uma implementação anterior do Agente 4 (`e05c46e`) nos mesmos
três arquivos de território. Foi lida antes de qualquer escrita e seu comportamento
útil foi preservado (auditoria de domínio, parâmetros, colisões, URLs derivadas,
simulação determinística, contenção de path, CLI). A versão desta branch atende aos
requisitos específicos do pedido: eventos recomendados com os nomes exatos
`view_booking_page`, `select_service_or_class`, `request_evaluation` e
`inspect_multitrack_split`, e colisão definida sobre a **tupla completa**
`(utm_source, utm_medium, utm_campaign, utm_content)` entre tenants distintos.

## Arquivos alterados

| Arquivo | Conteúdo |
| --- | --- |
| `tools/utm_simulator.py` | API `audit_and_simulate_utm(root, calendar_path, simulate_traffic, out_dir, seed)` e CLI com `--calendar`, `--simulate-traffic`, `--out-dir`, `--json`, `--root`, `--seed`. 100% stdlib (sem dependência de módulo local). Descoberta de tenants em `tenants/*/brand-kit.json`, auditoria de 100% das URLs do calendário + URLs derivadas de campanhas de tenants ainda não agendados, verificação de HTTPS/domínio exato, quatro parâmetros obrigatórios com formato limpo, `utm_campaign == slug`, colisão da tupla de atribuição e contenção de caminhos. Simulação sintética determinística das duas ondas (Reels 9:16, Shorts 9:16, Feed 1:1, Vídeo 16:9) com eventos por nicho e `revenueBRL: null`. |
| `tools/tests/test_utm_simulator.py` | 12 testes `unittest`. |
| `docs/analytics-utm-playbook.md` | Guia de conversões por nicho em GA4, Plausible e Umami, códigos de auditoria, checklist pré-publicação e rotina semanal com `matriz-utm-consolidada.csv`. |
| `.workspace/devlogs/etapa5-agente8.md` | Este relatório. |

## Cobertura dos testes

1. auditoria real de todas as URLs do calendário (40 slots, 5 tenants);
2. detecção de domínio divergente;
3. detecção de colisão de atribuição entre tenants;
4. cobertura de tenant descoberto em `tenants/*` e ainda não agendado (URL derivada);
5. `--simulate-traffic`: arquivos gerados, duas ondas, três formatos, sem receita;
6. contenção de path (`out-dir` e `calendar` fora da raiz);
7. CLI `--json`;
8. parâmetro ausente e valor sujo;
9. HTTPS e campanha igual ao slug;
10. catálogo fechado dos quatro eventos recomendados;
11. determinismo da seed;
12. CLI retorna `1` quando a auditoria reprova.

## Evidências

```text
python -m unittest tools/tests/test_utm_simulator.py -v
Ran 12 tests in 0.342s — OK

python tools/utm_simulator.py --json
ok=True; urlsAudited=40; urlsOk=40; derivedUrls=0;
totalUrls=40; unscheduledTenants=[]; collisions=0

python tools/utm_simulator.py --simulate-traffic --out-dir .workspace/tmp/utm-sim --json
ok=True; sessoes=210; conversoes=17;
formatos=16:9, 1:1, 9:16; onda-1=170, onda-2=40
arquivos: utm_sessions_sample.json (145312 bytes), utm_attribution_summary.md (1763 bytes)
```

Todos os `revenueBRL` das sessões são nulos; nenhuma transação financeira é simulada.
Os arquivos de simulação ficaram em `.workspace/tmp/utm-sim/` (local, fora do Git).

## Limites e governança

- Não publica, agenda, edita posts publicados nem altera outras marcas.
- Não gera áudio, TTS, música nem faixa sonora (política de vídeo sem áudio).
- `contexto_projeto.md`, `rastreio-utm.md`, `matriz-utm-consolidada.csv` e
  `calendario-editorial.json` não foram alterados.
- A ferramenta de analytics segue como decisão pendente do titular; o playbook é
  operacional, mas não declara links UTM como ativos.

## Handoff

Commit realizado nesta branch, sem merge na main (consolidação a cargo do titular).
A worktree permanece registrada e não foi removida — remoção exige autorização.
Nenhum arquivo relacionado ao projeto foi criado fora de `<RAIZ>`.

### Devlog — Etapa 5B, Agente 8 de 8
<!-- devlog-sync:etapa5-agente9.md -->

- **Data:** 2026-11-20
- **Agente:** Agente 8 de 8 (Engenharia Sênior de Qualidade Editorial e Arquitetura)
- **Branch:** `codex/etapa5b-agente8`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa5b-agente8` (já existia; criada a partir de `main`)
- **<RAIZ> nesta estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`
- **Nome do arquivo:** segue literalmente o caminho solicitado no pedido (`.workspace/devlogs/etapa5-agente9.md`), embora o executor seja o Agente 8.

## Escopo executado

1. `tools/editorial_qa.py` — CLI `python tools/editorial_qa.py [--all | --tenant <id>] [--strict] [--json] [--root <dir>]` e API `run_editorial_qa(root=".", strict=False, tenant=None) -> dict`, 100% stdlib e somente leitura. Reaproveita `srt_validate`, `tenant_validator.validate_text_against_guardrails` e `render_local`. Relatório `schemaVersion: 1` com `campaigns[]`, `checks[]` (5 lentes) e `summary`.
2. `tools/tests/test_editorial_qa.py` — 13 testes com sandbox copiado para `<RAIZ>/.workspace/tmp/editorial-qa/`: acervo real, linha SRT longa, U+FFFD e mojibake, violação de guardrail, filtro por tenant, `--strict`, `--json` e saída humana, divergência de duração, pacote social ausente, bloco vazio e determinismo.
3. `docs/arquitetura-fabrica.md` — seções 2.13–2.17 para `static_cards.py`, `bootstrap_ffmpeg.py`, `handoff_bundler.py`, `utm_simulator.py` e `editorial_qa.py`; subcomando `pipeline` documentado em 2.6; diagrama, contagem de tenants/campanhas (5/10), fluxo operacional e suíte (21 módulos) atualizados. Notas obsoletas sobre a matriz UTM foram corrigidas (consolidação concluída, gate 7/7).
4. `README.md` — contagens, linha de `clinica-vital`, comandos das Etapas 5/5B, parágrafo da camada de acabamento e checklist operacional.

## Resultado observado no acervo atual

- 10 campanhas descobertas em `tenants/*/campaigns/*.json`; 5 tenants válidos.
- Lentes aprovadas: `duracao_srt_manifest`, `paridade_entregas`, `guardrails_cruzados`, `integridade_utf8` (0 erros).
- `legibilidade_mobile`: **46 avisos** `SRT_LINHA_LONGA` (linhas de 62 a 82 caracteres, limite 48) espalhados pelas 10 campanhas. Nenhum bloco vazio.
- Nenhum `MOJIBAKE_DETECTADO`, nenhuma violação de guardrail, nenhuma divergência de duração (todos os SRTs terminam em 30,000 s contra `format.duration = 30.0`).
- Modo normal: `ok: true`, exit 0. Modo `--strict`: `ok: false`, exit 1 — motivado pelos avisos de legibilidade. Isso é um achado editorial real, não uma falha da ferramenta: a correção das linhas dos SRTs pertence ao acervo e foi preservada (fora do território deste agente).
- `python -m unittest tools/tests/test_editorial_qa.py -v`: **13 testes, 100% OK**.

## Segurança e escopo

- Nenhuma ferramenta publica, agenda ou cria rascunho; nenhum áudio é gerado.
- Nenhum arquivo de `contexto_projeto.md`, SRT, manifesto ou pacote social foi alterado.
- Sandbox de testes e arquivos temporários ficaram sob `<RAIZ>/.workspace/tmp/etapa5-agente8/` e `<RAIZ>/.workspace/tmp/editorial-qa/`; `tools/__pycache__/` e `tools/tests/__pycache__/` foram removidos antes do commit.
- `git pull --ff-only` executado no início (já atualizado); `main` estava `ahead 13` do `origin/main` nesta estação.

## 2. Testes de `tools/publish_pack.py` refatorados

`tools/tests/test_publish_pack.py` não usa mais a raiz do repositório para
escrever: `setUpClass` monta uma raiz em `tempfile.TemporaryDirectory` com
cópia de `tenants/`, `schemas/`, das entregas (manifest.json, `.srt`,
`_narracao.txt`) e de `.workspace/archives/` sintéticos com hash coerente com
o manifesto. Contagens são dinâmicas (`>= 4` tenants, `>= 8` campanhas).

Casos (10): geração por tenant, hashes dos arquivos gravados, UTM por canal,
CTA de Instagram, bloqueio de `forbiddenClaims`, `_audit` abortando,
integridade do checklist, `resolve_workspace_root` (raiz temporária, raiz
falsa e raiz real com archives), hash do vídeo conferido em `archives/` e
snapshot provando que `04-legendas/pacotes-publicacao/` versionado não é
alterado pela suíte.

---

## 3. `tools/handoff_bundler.py` (novo)

CLI:

```
python tools/handoff_bundler.py [--approvals-file <json>]
    [--date YYYY-MM-DD | --all-approved] [--include-pending]
    [--output-dir .workspace/handoff-diario] [--root <raiz>] [--json]
```

API: `build_handoff_bundle(root=..., approvals_file=None, date=None,
all_approved=False, include_pending=False, output_dir=None)`.

### Entradas

- Aprovações do titular: default `<workspace>/tmp/aprovacoes-titular.json`
  (workspace resolvido, inclusive o do checkout principal a partir de
  worktree). Schema **v1** (`aprovada: true`) e **v2**
  (`decisao: "aprovado"`) normalizados por `_decision`.
- `04-legendas/calendario-editorial.json` (slots).
- Pacotes sociais (`04-legendas/pacotes-publicacao/<tenant>/<slug>/`) e
  `derivatives.json` das entregas.

### Travas de segurança

- Sem `--include-pending`, só campanhas **explicitamente aprovadas** entram.
  Sem nenhuma aprovada, retorna exatamente:
  `{"ok": true, "bundledSlots": 0, "reason": "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR"}`.
- Decisão `ajuste` nunca entra, nem com `--include-pending` (registrada em
  `skipped` como `AJUSTE_SOLICITADO`).
- `autoPublish` é sempre `false` (manifesto, índice e JSON de retorno).
- Todo caminho é resolvido e confinado (raiz do projeto para saída e
  pacotes; workspace resolvido para aprovacoes e archives). Nomes de slot,
  tenant, campanha e canal passam por regex estrita.
- A copy final (após substituição da URL UTM do slot) é reauditada com
  `tenant_validator.validate_text_against_guardrails`; violação aborta o slot.
- Mídia copiada é verificada por SHA-256; hash divergente remove o arquivo e
  marca `mediaCopied: false` + `error: HASH_DIVERGENTE` (nunca entrega mídia
  inconsistente).

### Saída por slot

`.workspace/handoff-diario/<dataSugerida>/<slotId>-<tenantId>-<canal>/`:

- `POSTAGEM-MANUAL.md` — status de aprovação/selo `PREVIA_NAO_APROVADA`,
  data e janela BRT, conta/marca, canal, formato (`9:16` / `1:1` / `16:9`),
  mídia esperada e disponibilidade local, `autoPublish: false`, alerta
  explícito de locução externa em tenants `-an`, copy pronta, URL UTM
  completa e checklist numerado de 5 passos.
- `copy-pronta.txt` — copy do canal com a URL UTM do slot (na Onda 2 troca
  `utm_content` para `repurpose-1x1` / `repurpose-16x9`).
- `handoff-manifest.json` — metadados, `approvalStatus`, `audioPolicy`,
  `sha256Expected`/`sha256Copied`/`hashVerified`, `mediaCopied`, bloco de
  `cover`, `guardrailsAudited` e `autoPublish: false`.
- `<slug>.mp4` (Onda 1), `<slug>-1x1.mp4` ou `<slug>-16x9.mp4` (Onda 2) e
  `cover.png`, copiados de `<workspace>/archives/` quando existem.

Índice consolidado em `.workspace/handoff-diario/INDICE-OPERACIONAL.md` e
`indice-operacional.json` (tabela por data/slot/canal, status e mídia local).

### Comportamento nesta estação

`.workspace/archives/` está vazia nesta estação (só `test-deriv-ms`). Com as
aprovações reais ausentes, a execução padrão devolve o JSON limpo de "nenhuma
campanha aprovada". Em smoke test com aprovações sintéticas, os 4 slots da
campanha `marca-salao/camp-saas-demo-marca-salao-001` foram empacotados com
`mediaCopied: false` e `error: MIDIA_AUSENTE_NESTA_ESTACAO`, que é o
diagnóstico correto — o handoff continua utilizável e a ficha aponta a
estação onde copiar o MP4.

---

## 4. Suíte `tools/tests/test_handoff_bundler.py` (12 testes)

Raiz temporária própria com `tenants/`, `schemas/`, calendário de 6 slots
(4 tenants, Ondas 1 e 2), pacotes copiados e `.workspace/archives/` com
mídias sintéticas + hashes atualizados. Casos:

1. Sem aprovações → JSON limpo (`bundledSlots == 0`, reason exata).
2. Schema v1 (`aprovada: true`).
3. Schema v2 (`decisao: "aprovado"`).
4. Filtragem seletiva: apenas a campanha aprovada (3 slots), nada de outro tenant.
5. Roteamento de mídia: 9:16 (`<slug>.mp4`), 1:1 (`-1x1.mp4`), 16:9 (`-16x9.mp4`) + `cover.png`, `mediaCopied`/`hashVerified` verdadeiros.
6. `--include-pending` com selo `PREVIA_NAO_APROVADA` e exclusão de `ajuste`.
7. Filtro `--date` (1 slot) e data sem aprovado (`NENHUM_SLOT_APROVADO_NA_DATA`).
8. Documentos do slot, 5 passos (sem passo 6), URL UTM `repurpose-16x9` na copy, `autoPublish: false`, `manualOnly: true`.
9. Alerta de locução externa só em `-an`; `multitrack-hub` sem alerta e `externalNarrationAlert: false`.
10. Contenção de path: output `../`, aprovacoes `../../` e slotId `../escape` bloqueados.
11. CLI `--json` via subprocess: exit 0 e JSON válido.
12. Índice `INDICE-OPERACIONAL.md` + `indice-operacional.json`.

Comando final:

```
python -m unittest tools/tests/test_publish_pack.py tools/tests/test_handoff_bundler.py -v
```

Resultado: **22 testes, OK** (rodado também com `-W error::ResourceWarning`).

---

## 5. Estado do worktree e limpeza

- Scratch removido: `.workspace/tmp/`, `.workspace/handoff-diario/` (smoke),
  `.workspace/tmp-publish.*`, `tools/__pycache__`, `tools/tests/__pycache__`.
- Alterações permanentes: `tools/publish_pack.py`,
  `tools/tests/test_publish_pack.py`, `tools/handoff_bundler.py`,
  `tools/tests/test_handoff_bundler.py`, os 8 `checklist-publicacao.json` e
  este devlog.
- Nenhum arquivo de `04-legendas/pacotes-publicacao/` foi sujado pela suíte
  (provado por snapshot no teste 10 do publish_pack); a regravação existente
  vem apenas do comando `--all` exigido, com os campos novos do checklist.
- Commit local na branch `codex/etapa5b-agente2-handoff-aprovacoes`; sem push.

## 6. Próximos passos sugeridos para integração

1. Revisar o diff dos 8 checklists (apenas campos novos: `archivePath`,
   `resolvedFrom`, `presentOnDisk`, listas de violações).
2. No merge, manter `resolve_workspace_root` alinhado ao padrão já existente
   em `derivative_formats.py`/`review_dashboard.py`.
3. Quando o titular aprovar campanhas no portal
   (`review_dashboard.py --serve`), rodar
   `python tools/handoff_bundler.py --all-approved --json` na estação que
   possui `.workspace/archives/` para empacotar com mídia.

### Novos — `tenants/clinica-vital/`
<!-- devlog-sync:etapa5-agente3.md -->

- `brand-kit.json`
  - `tenantId: "clinica-vital"`, `brandName: "Clínica Vital"`, `displayTitle: "CLINICA VITAL"`, `monogram: "CV"`, `domain: "clinicavital.com.br"`, `url: "https://clinicavital.com.br"`.
  - `tagline: "Organizacao de consultas e agenda clinica com clareza"` (literal do pedido).
  - Paleta clínico-moderna distinta dos 4 tenants anteriores: primary `#0EA5E9`, secondary `#14B8A6`, accent `#F59E0B`, background `#0B1324`, surface `#12203A`, textPrimary `#F1F5F9`, textMuted `#94A3B8`, com bloco `palette.rgb` completo (12 chaves exigidas quando presente).
  - `headerOverlay`: `enabled: true`, `label: "CLINICA VITAL"`, `badgeText: "CONSULTAS & AGENDA"`, `bgColor: "#070C18"`, `textColor: "#F1F5F9"`, `height: 170`.
  - `defaultPreset: "saas-demo"`; `utmDefaults`: `instagram` / `reels` / `cv`.
- `guardrails.json`
  - `forbiddenClaims`: cura e promessa de cura, resultado/resultado estético garantido, tratamento garantido, tratamento sem dor garantido, diagnóstico médico/odontológico online, antes e depois, fotos antes e depois, mensagens automáticas/automatizadas, WhatsApp, SMS, e-mail/email, lembretes automáticos, 24h/24 horas, redução de faltas, zero faltas, zero absenteísmo, aumento de faturamento, faturamento/lucro garantido.
  - `forbiddenUiElements`: checkout, pagamento, cobrança, a pagar, cartão de crédito, prontuário, receita digital, receita médica, fotos antes e depois, antes e depois, "Meu Salão", `E2E`, `Lorem ipsum`.
  - `routeRules`: `/avaliacao/[clinicId]` (`public-booking`) × `/gestor/consultas` (`manager-agenda`), com responsabilidades permitidas e vetadas por superfície (inclui `busca-paciente` e `alteracao-manual-status` na recepção; veta `diagnostico-online`, `exposicao-prontuario` e `promessa-cura` no público).
  - `audioPolicy`: `allowAudioTrack: false`, `requireSrt: true`, `requireExternalNarration: true`, `ffmpegFlag: "-an"`.
- `fixtures/fixture-editorial-clinica-vital.json`
  - 4 especialistas fictícios: Dra. Helena Vasconcelos, Dr. Rodrigo Nogueira, Dra. Camila Ferraz, Dr. Thiago Prado.
  - 5 procedimentos com duração e valor BRL: Avaliação Clínica Inicial (30 min, R$ 250,00), Limpeza e Profilaxia (45 min, R$ 320,00), Consulta Ortodôntica (40 min, R$ 280,00), Check-up Preventivo (30 min, R$ 290,00), Avaliação Estética Facial (50 min, R$ 350,00).
  - Grade diária de 6 consultas em 2026-11-18 com status `Confirmado` / `Aguardando` / `Concluído`, incluindo Patricia Monteiro às 10:00.
  - Chaves de compatibilidade com o motor: `profissionais`, `servicos`, `agenda.atendimentos`, `booking.rota = "/avaliacao/clinica-vital-centro"`; duplicatas do nicho: `especialistas`, `procedimentos`, `gradeDiaria.consultas`, `agenda.visaoRota = "/gestor/consultas"`.
- `campaigns/README.md`: descreve as duas campanhas, superfícies e notas de conformidade do nicho.
- `campaigns/camp-saas-demo-clinica-vital-001.json` — `SAAS-DEMO-CLINICA-VITAL-001`, 6 cenas, `30.0s`, `saas-demo`.
  - hook (4s) → booking-selection em `/avaliacao/clinica-vital-centro` (6s) → booking-confirm com slots `08:30/10:00/14:30/16:00` e seleção 10:00 (7s) → booking-success (3s) → manager-agenda em `/gestor/consultas` com `highlightId: cons-cv-002` (Patricia Monteiro, 6s) → CTA (4s).
  - `bookingCase`: Patricia Monteiro / `srv-cv-001` / `prof-cv-001` / 10:00.
- `campaigns/camp-saas-demo-clinica-vital-002.json` — `SAAS-DEMO-CLINICA-VITAL-002`, 6 cenas, `30.0s`, `saas-demo`.
  - Foco exclusivo na recepção: hook (4s) + 4 cenas `manager-agenda` (grade do dia, filtro por Dra. Camila Ferraz, atualização manual de status de Aguardando → Confirmado, busca por paciente Luciana Farias) + CTA (4s). Nenhuma rota `/avaliacao` e nenhuma superfície `public-booking`.

### Alterados

- `docs/guia-novo-nicho.md`: nova seção "Nicho regulado (saúde/clínicas) — exemplo `clinica-vital`" com estrutura, identidade/preset, tabela de superfícies, guardrails obrigatórios, compatibilidade de fixture, descrição das campanhas, comandos de validação/render e nota de consolidação sobre `test_factory_cli.py`.
- `tools/tests/test_tenant_contracts.py`:
  - `test_01`: inclui `clinica-vital` na descoberta e valida brand-kit/guardrails do tenant.
  - `test_07`: contagem de tenants passa de `== 4` para `>= 5`, com `clinica-vital` presente.
  - `test_08` (novo): bloqueio de promessas clínicas, elementos de UI proibidos, texto neutro permitido, `routeRules` por superfície.
  - `test_09` (novo): fixture (4 profissionais, 5 serviços, 6 atendimentos, status e Patricia Monteiro), campanhas (6 cenas, soma 30.0s, preset, tenantId), auditoria de todos os textos contra guardrails, rotas do público × recepção e contagem de superfícies.
- `.workspace/devlogs/etapa5-agente3.md`: este relatório.

## 4. Decisões de adaptação (e por quê)

1. **`utmDefaults` no formato do schema:** o pedido trouxe a forma curta `{"source","medium","campaignPrefix"}`, mas `schemas/brand-kit.schema.json` exige `utm_source`/`utm_medium`/`utm_campaign_prefix` e proíbe propriedades adicionais. Foi usado o formato do schema, idêntico aos 4 tenants e ao exemplo do guia. Valores preservados: instagram / reels / cv.
2. **`headerOverlay` completo:** o schema exige `badgeText`, `bgColor` e `textColor` além de `enabled`/`label`. Preenchidos no padrão dos demais tenants, preservando `enabled: true` e `label: "CLINICA VITAL"`.
3. **`baseCaptureRef` omitido:** a campanha 001 não herda captura de tela legada; sem o campo, o motor usa o gradiente neutro do brand-kit em `manager-agenda` (fallback nativo de `_load_neutral_capture_backdrop` para caminho ausente/nulo). Evita apontar para ativo inexistente.
4. **Sem tela de pagamento/checkout em nenhuma cena:** conforme `forbiddenUiElements`, e coerente com a superfície pública de avaliação.
5. **Rótulos internos do motor não alterados:** `tools/preset_runner.py` desenha textos fixos de engenharia (`PROFISSIONAIS DO SALAO`, `/BOOKING/[SALONID]`, `DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO`, pill de superfície `/GESTOR/AGENDA`) fora da auditoria de guardrails e fora do território deste agente. Não foram tocados; ficam registrados como ajuste cosmético pendente para a consolidação (ver §7).

## 5. Validação de contratos

Comando executado na worktree:

```bash
python tools/tenant_validator.py --tenant clinica-vital --json
```

Resultado literal: `ok: true`, `errors: []` (brand-kit, guardrails e fixture localizados e válidos).

```bash
python tools/tenant_validator.py --all --json
```

Resultado: `ok: true` para os 5 tenants, todos com 0 erros:

| tenant | ok | erros |
| --- | --- | --- |
| clinica-vital | true | 0 |
| estudio-flow | true | 0 |
| marca-salao | true | 0 |
| meu-salao | true | 0 |
| multitrack-hub | true | 0 |

Descoberta da fábrica (`python tools/factory_cli.py list --tenant clinica-vital --json`): `ok: true`, `totalCampaigns: 2`, as duas campanhas com `scenesCount: 6` e `durationSeconds: 30.0`, `allowAudioTrack: false`.

Auditoria pré-render dos textos (mesmo pipeline de `preset_runner._audit_texts`, com `check_ui_elements=True`): **0 violações** em ambas as campanhas; soma de cenas `30.0s` = `format.duration` nas duas.

## 6. Renderização — bloqueio controlado por ausência de ffmpeg

Verificação do ambiente: `which ffmpeg` e `which ffprobe` não encontram binários; não existe `.workspace/tools/ffmpeg` (nem na raiz nem na worktree); `build_video.get_ffmpeg()` falha com:

```text
DeliveryError: ffmpeg nao encontrado no PATH; instale ou exponha o binario antes de exportar
```

Tentativa explícita, sem gravar artefatos:

```bash
python tools/factory_cli.py render --tenant clinica-vital --report .workspace/tmp/etapa5b-agente3/report.json --json
# Erro: ffmpeg/ffprobe nao encontrados; exponha no PATH ou em .workspace/tools/ffmpeg
# exit 1
```

Derivados (sem entrega renderizada):

```bash
python tools/derivative_formats.py --tenant clinica-vital --json
# nenhuma entrega vigente para tenant=clinica-vital
# exit 2
```

Conclusão: nada foi gravado em `02-reels-shorts/deliveries/clinica-vital/`; nenhum MP4/SRT/narração/storyboard/derivado foi produzido nesta estação. **Contratos e campanhas do `clinica-vital` estão validados e prontos para `factory_cli.py render --all` na consolidação pós-bootstrap**, quando houver `ffmpeg`/`ffprobe`. A auditoria de `0` streams de áudio (`-an`) via `ffprobe` também fica pendente da mesma consolidação.

## 7. Pendências para a consolidação (fora do território deste agente)

1. **`tools/tests/test_factory_cli.py`**: mantém `totalTenants == 4` (`test_01`) e `totalTenants == 4` / `totalCampaigns == 8` / `len(deliveries) == 8` (`test_03`). Com o 5º tenant e as 2 novas campanhas, esses testes falharão até serem atualizados para 5/10 (ou `>=`). Arquivo não editado por não estar no território autorizado.
2. **Render e derivados**: executar `python tools/factory_cli.py render --all --json` (ou `--tenant clinica-vital --report .workspace/tmp/...`), conferir `audioStreams == 0` via ffprobe e rodar `python tools/derivative_formats.py --tenant clinica-vital --json` após o bootstrap do ffmpeg pelo Agente 1.
3. **`02-reels-shorts/deliveries/factory-report.json`**: regenerar na consolidação; não foi tocado por este agente.
4. **Rótulos internos do motor** (cosmético, opcional): `preset_runner.py` desenha "SALAO"/"/BOOKING/[SALONID]"/"/GESTOR/AGENDA" fixos; para nicho clínico, uma futura generalização por brand-kit seria mais adequada. Não é violação de guardrails (texto de engenharia, fora da auditoria).
5. **`contexto_projeto.md`**: permanece com `Raiz oficial: D:/MEGA/Marketing/marcasalao-marketing` (literal de outra estação). Não editado por escopo; a raiz efetiva desta sessão é `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`. Correção portável fica para o consolidador.

## 8. Testes

```bash
python -m unittest tools/tests/test_tenant_contracts.py -v
```

Resultado: `Ran 9 tests ... OK` (9/9), incluindo os novos `test_08` e `test_09`.

## 9. Handoff de armazenamento

- Raiz usada nesta estação: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.
- Worktree: `<RAIZ>/.workspace/worktrees/etapa5b-agente3` (isolada; será removida pelo consolidador após merge, mediante autorização).
- Temporários: `<RAIZ>/.workspace/worktrees/etapa5b-agente3/.workspace/tmp/etapa5b-agente3/` (evidência do `validator --all`), ignorados pelo Git.
- Nenhum arquivo permanente ficou apenas em `.workspace/tmp/`; os arquivos versionados estão em `tenants/clinica-vital/`, `docs/guia-novo-nicho.md`, `tools/tests/test_tenant_contracts.py` e `.workspace/devlogs/etapa5-agente3.md`.
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.

### Devlog — Etapa 5B / Agente 4 (orquestrador end-to-end e analytics)
<!-- devlog-sync:etapa5-agente4.md -->

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa5b-agente4-orquestrador-e2e-analytics`  
> **Worktree:** `.workspace/worktrees/etapa5b-agente4`  
> **Base:** `main` @ `edd56e8`  
> **Escopo:** orquestrador unificado, auditor/simulador UTM, playbook de analytics, testes e CI

## 1. Objetivo

Fechar a Etapa 5B no território do Agente 4: transformar o `factory_cli.py` em um
orquestrador mestre determinístico (contratos → render → derivados → cards →
pacotes → calendário → portal → UTM → release gate), entregar a auditoria UTM com
simulação sintética das duas ondas e documentar o mapa de eventos por nicho com
receitas de GA4, Plausible e Umami.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/factory_cli.py` | evoluído | subcomando `pipeline` com 9 estágios, imports opcionais, JSON por estágio com `durationMs`, contagens consolidadas |
| `tools/utm_simulator.py` | novo | auditoria de 100% das URLs UTM + simulação determinística de tráfego (`--simulate-traffic`) |
| `tools/tests/test_factory_cli.py` | atualizado | contagens dinâmicas (`>= 4` tenants, `>= 8` campanhas), testes de `pipeline` filtrado e `--all` |
| `tools/tests/test_utm_simulator.py` | novo | 11 testes: domínio, parâmetros, padronização, colisão, derivação, simulação, CLI e contenção de caminho |
| `docs/analytics-utm-playbook.md` | novo | eventos por nicho (5, incluindo `clinica-vital`), receitas GA4/Plausible/Umami, validação e rotina semanal |
| `.github/workflows/local-render-validation.yml` | atualizado | trigger `01-insta-stories/deliveries/**`, 4 novas suites no CI, smoke de `pipeline --all --skip-render` |
| `.workspace/devlogs/etapa5-agente4.md` | novo | este relatório |

## 3. Desenho do `pipeline`

Ordem fixa dos estágios (sempre os 9 no relatório, mesmo quando pulados):

1. `contratos` → `tenant_validator.load_and_validate_tenant(..., strict=True)`.
2. `render` → `preset_runner.run_preset_pipeline`; com `--skip-render`, verifica
   `02-reels-shorts/deliveries/<tenant>/<slug>/manifest.json` e registra o preset
   e `audioStreams` declarados.
3. `derivados` → `derivative_formats.generate_campaign_derivatives` (produção) ou
   verificação de `derivatives.json` + hashes quando o arquivo existe no disco.
4. `cards-estaticos` → `static_cards.generate_campaign_static_cards` ou verificação
   de `01-insta-stories/deliveries/<tenant>/<slug>/static-manifest.json`.
5. `pacotes` → `publish_pack.generate_pack` ou verificação de
   `checklist-publicacao.json` + 3 legendas, exigindo `autoPublish=false` e
   `guardrailsAudited=true`.
6. `calendario` (só `--all`) → `campaign_calendar.build_editorial_calendar` em
   memória, usando `--start-date`/`--weeks` ou os valores do calendário versionado.
7. `portal` (só `--all`) → `review_dashboard.build_portal` (produção) ou
   verificação de `05-review-portal/`.
8. `utm` → `utm_simulator.audit_and_simulate_utm`.
9. `release-gate` → `release_audit.run_release_audit(root, strict=args.strict_audit)`.

Decisões:

- **Importação opcional real:** módulos das etapas paralelas são importados via
  `importlib`; se ausentes, o estágio vira `skipped` com motivo e o pipeline segue.
  O Release Gate é fail-closed: ausência do módulo reprova.
- **`--skip-render` é modo de verificação**, não de omissão: todo artefato versionado
  é conferido (manifesto, derivados, cards, pacote, portal). Hashes só são exigidos
  quando o binário local existe, alinhado à política do `release_audit` para mídia
  não rastreada.
- **Compatibilidade total:** `list` e `render` mantêm assinatura, saída e exit codes.
- **Falha por estágio:** `StageFailure` preserva detalhes estruturados (ex.: domínios
  do release gate, códigos UTM) mesmo quando o estágio reprova.

## 4. Auditoria e simulação UTM

- Fonte primária: `04-legendas/calendario-editorial.json` (32 slots, 4 tenants).
- URL derivada para campanha ainda não agendada: `https://<domain>/?utm_source=
  <utmDefaults.utm_source>&utm_medium=<utmDefaults.utm_medium>&utm_campaign=<slug>
  &utm_content=<tenantId>`, marcada com `origin=derived`.
- Regras de erro: HTTPS, domínio do brand-kit, 4 parâmetros obrigatórios, alfabeto
  `[a-z0-9._-]`, `utm_campaign == slug`, ausência de duplicidade e de colisão entre
  tenants (campanha isolada e par campanha+conteúdo).
- Simulação: RNG semeado por `sha256(seed + slug + canal + midia + url)`; cobre
  Reels, Shorts, Feed 1:1 (`repurpose-1x1`) e Vídeo 16:9 (`repurpose-16x9`).
  Saída em `utm_sessions_sample.json` + `utm_attribution_summary.md`.
  `financialSimulation: false` e `revenueBRL: null` em 100% das sessões.
- Catálogo de eventos por nicho inclui `clinica-vital` (nicho em onboarding), mesmo
  sem tenant ativo, sem gerar URL antes de existir brand-kit.

## 5. Evidências de validação (nesta estação)

```
$ python tools/factory_cli.py pipeline --tenant marca-salao \
    --campaign camp-saas-demo-marca-salao-001 --skip-render --json
ok=True (287–405 ms)
estágios: contratos ok, render ok, derivados ok, cards-estaticos ok, pacotes ok,
          calendario skipped, portal skipped, utm ok, release-gate ok
counts: 1 tenant, 1 campanha, 7 cards, 32 URLs UTM, 7/7 domínios ok

$ python tools/factory_cli.py pipeline --all --skip-render --json
ok=True (~1,1 s)
counts: 4 tenants, 8 campanhas, 8 entregas, 8 derivados, 56 cards, 8 pacotes,
        32 slots de calendário, 8 campanhas no portal, 32 URLs UTM, 7/7 domínios ok

$ python tools/utm_simulator.py --json
ok=True, 32/32 URLs, 0 derivadas, 0 erros, 0 avisos

$ python tools/utm_simulator.py --simulate-traffic --out-dir .workspace/tmp/utm-sim --json
472 sessões, 52 conversões, ondas 400/72, pegadas instagram/reels,
youtube/shorts, instagram/feed, youtube/video, facebook/reels

$ python -m unittest tools.tests.test_utm_simulator -v
Ran 11 tests — OK

$ python -m unittest (test_factory_cli 01,03,04,05,06)
Ran 5 tests — OK

$ python tools/release_audit.py --strict --json
7/7 domínios ok, 0 erros, 0 avisos
```

## 6. Limitações desta estação

- `ffmpeg`/`ffprobe` continuam ausentes nesta máquina; por isso o modo de produção
  real (sem `--skip-render`) e a geração de derivados não foram executados aqui.
  O caminho de produção é exercitado no CI, que instala FFmpeg via ação oficial.
- Os testes `test_bootstrap_ffmpeg.py` e `test_handoff_bundler.py` ainda não existem
  nesta branch: pertencem aos Agentes 1 e 2. Foram adicionados à suíte do workflow
  conforme o contrato de integração; a execução completa ocorre na branch integrada.
- Divergência intencional entre ramos: estágios de módulos paralelos ficam `skipped`
  até que os arquivos correspondentes estejam presentes na branch final.

## 7. Arquivos não tocados

`contexto_projeto.md` não foi editado, conforme território exclusivo. Nenhuma
worktree de outro agente foi acessada. Nenhum post, tenant, campanha, calendário ou
portal foi publicado/alterado.

## 8. Handoff

- Branch pronta para merge: `codex/etapa5b-agente4-orquestrador-e2e-analytics`.
- Comando de verificação rápida: `python tools/factory_cli.py pipeline --all
  --skip-render --json`.
- Próximo agente/integrador: rodar a suíte completa no CI, onde FFmpeg está
  disponível, e confirmar `pipeline --all` no modo de produção após o merge dos
  Agentes 1–3.

## 2. Execução nas 8 campanhas

Comando: `python tools/derivative_formats.py --all --json` (na worktree, fontes
regeneradas pela fábrica `tools/preset_runner.py` nesta etapa; multitrack-hub com
trilha `ambient-bed` do `tools/audio_tts.py`).

| Tenant | Slug | Política | 1x1 | 16x9 | src SHA-256 (12) | 1x1 (12) | 16x9 (12) | cover (12) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| estudio-flow | camp-saas-demo-estudio-flow-001 | -an | 1080x1080 fps30 aac=0 | 1920x1080 fps30 aac=0 | 4256c7d9c73a | e97a8745c301 | 04d4d4b6ef6b | 08d664fa433e |
| marca-salao | camp-saas-demo-marca-salao-001 | -an | 1080x1080 fps30 aac=0 | 1920x1080 fps30 aac=0 | df1d45bbb8d7 | 94e6ca50f4da | 17a6b4543efe | d285336ae18c |
| marca-salao | camp-saas-demo-ns001-agenda-001 | -an | 1080x1080 fps30 aac=0 | 1920x1080 fps30 aac=0 | 45166ac75e7c | 6fe18ca9efb8 | 95239fd5d757 | 84e20cdc1d83 |
| meu-salao | camp-saas-demo-meu-salao-001 | -an | 1080x1080 fps30 aac=0 | 1920x1080 fps30 aac=0 | 76b3eb2ced36 | d88204865d11 | d2752a1aa267 | eb0561b2febb |
| meu-salao | camp-saas-demo-meu-salao-002 | -an | 1080x1080 fps30 aac=0 | 1920x1080 fps30 aac=0 | a2c9b047d498 | 59096667bd42 | 742e222793e9 | 4ff9b296ad3a |
| multitrack-hub | camp-shorts-completo-multitrack-001 | aac-44100-stereo | 1080x1080 fps30 aac=1 | 1920x1080 fps30 aac=1 | 2a909fbb4b80 | 05656be72769 | af799d2b6954 | 374f8c24a3d2 |
| multitrack-hub | camp-shorts-rateios-002 | aac-44100-stereo | 1080x1080 fps30 aac=1 | 1920x1080 fps30 aac=1 | 3e141f3bc1fd | 05dafd2c41dc | 5902f9cbdaab | bedb296828a1 |
| multitrack-hub | camp-shorts-stems-workflow-003 | aac-44100-stereo | 1080x1080 fps30 aac=1 | 1920x1080 fps30 aac=1 | 50b0a0fcfa8f | 712c1e8b40ad | 8b9156bf3cf7 | 3d9a6246c9a6 |

## 3. Auditoria ffprobe (evidência bruta)

- Geometria/fps/codec confirmados por ffprobe em todos os 24 derivados
  (8 covers PNG 1080x1920; 8 1x1 1080x1080; 8 16x9 1920x1080; todos h264
  yuv420p 30 fps exceto covers png).
- **Áudio**: 0 streams em todos os derivados de estudio-flow/marca-salao/meu-salao
  (política `-an`); 1 stream `aac` 44100 Hz stereo em todos os 6 derivados de vídeo
  do multitrack-hub.
- **Moldura do cover (medição de pixel)**: recorte `crop=8:8:14:14` do cover
  marca-salao decodificado em `rgb24` → bytes uniformes `216 166 0`, consistentes
  com `#F5C107` a 85% de opacidade sobre canto escuro do frame (0.85×245≈208;
  0.85×193≈164; 0.85×7≈6 + contribuição do fundo). A moldura é a cor primária
  do brand-kit, não um cinza preto.
- Frame representativo extraído a 2 s do 1x1 marca-salao e do 16x9 multitrack-hub
  em `.workspace/tmp/etapa4-agente1/frames/` (evidência local).

## 4. Suítes executadas

| Suíte | Resultado |
| --- | --- |
| `python -m unittest tools/tests/test_derivative_formats.py -v` | **Ran 10 tests in 22.029s — OK** |
| Núcleo do CI + módulo novo (`test_tenant_contracts`, `test_preset_runner`, `test_factory_cli`, `test_audio_tts`, `test_publish_pack`, `test_devlog_sync`, `test_derivative_formats`) | **Ran 49 tests in 96.715s — OK** (exit 0) |
| `python -m unittest discover -s tools/tests -v` | Ran 228 tests — FAILED (failures=2, errors=34, skipped=59) |

Sobre o discover: as 2 failures + 34 errors estão **todas** em módulos studio
(`test_studio_*`, `test_campaign_studio_e2e`, `test_queue_process_restart`,
`test_studio_work_backup`, `test_render_local` timeout) que exigem `platform/dist`
compilado — condição pré-existente desta worktree nova (sem build npm), **sem
relação com esta etapa**: nenhum desses testes importa `derivative_formats`
(verificado por grep no log; as 10 menções a "derivative" no log são os 10
testes do módulo novo, todos `ok`). Logs completos em
`.workspace/logs/etapa4-agente1/suite-discover.log` e `suite-core.log`.

## 5. Arquivos versionados neste commit

- `tools/derivative_formats.py` (novo)
- `tools/tests/test_derivative_formats.py` (novo)
- `02-reels-shorts/deliveries/{estudio-flow,marca-salao,meu-salao,multitrack-hub}/*/derivatives.json`
  (8 manifestos novos; nenhum `manifest.json` existente foi alterado)

Permanecem somente no `.workspace/` local (por desenho): MP4s/PNGs dos derivados,
fontes regeneradas, logs de suíte, frames de evidência e este devlog.

## 6. Limpeza e handoff

- Fixtures sintéticas dos testes removidas (slugs `test-deriv-*` fora de
  `deliveries/` e de `.workspace/archives/`; `git status` da worktree mostra
  apenas os 10 arquivos da entrega).
- Scratch `.workspace/tmp/etapa4-agente1/` preservado até o encerramento da etapa
  (fontes regeneradas + frames de evidência); descartável ao final.
- Próximo passo sugerido: revisão/merge da branch `codex/etapa4-agente1-derivados-multiformato`
  e, se desejado, inclusão de `tools/tests/test_derivative_formats.py` na linha
  explícita do CI (`local-render-validation.yml`, fora do território deste agente —
  o `discover` já o cobre na linha seguinte).

---

# Devlog — Rodada 2 (overnight): 5 formatos + manifesto v2 + resolucao de .workspace/

- **Data**: 2026-11-19
- **Papel**: Engenheiro de Midia Programatica e FFmpeg
- **Branch**: `codex/etapa4-agente1-derivados-multiformato` (worktree recriada de `main` @ `f7298dc`)
- **Worktree**: `<RAIZ>/.workspace/worktrees/etapa4-agente1`
- **Territorio respeitado**: somente `tools/derivative_formats.py`,
  `tools/tests/test_derivative_formats.py`, `02-reels-shorts/deliveries/**` e este
  devlog. `contexto_projeto.md` e `tools/preset_runner.py` nao foram tocados; a
  worktree do agente 3 desta rodada (`.workspace/worktrees/etapa4-agente3`) nao
  foi acessada.

## 1. O que mudou em relacao a rodada 1

### `tools/derivative_formats.py` (v2, ~860 linhas)

- **Cinco formatos por campanha** (rodada 1: tres):
  - `<slug>-1x1.mp4` — 1080x1080, 30 fps, h264, yuv420p, crf 20; fundo desfocado
    escurecido do proprio video (`boxblur=24:4,eq=brightness=-0.18:saturation=0.85`),
    9:16 centralizado em altura total (608x1080, lanczos) com moldura lateral de
    4 px na cor primaria (`pad=616:1080:4:0:<primaria>`).
  - `<slug>-16x9.mp4` — 1920x1080, mesmos codecs; fundo `boxblur=28:5,
    eq=brightness=-0.22:saturation=0.80`, mesmo primeiro plano 608x1080.
  - `<slug>-cover.png` — 1080x1920, frame hero em t=2.5 s com tarjas translucidas
    (fundo do brand-kit, alpha 0.55) e linhas de acento de 8 px na cor primaria
    (alpha 0.95) no topo e na base.
  - `<slug>-thumb-16x9.png` — 1920x1080, frame em t=2.5 s composto em 16:9
    (mesma composicao do derivado largo).
  - `<slug>-preview-grid.png` — 1920x1080, prancha comparativa 9:16 | 1:1 | 16:9
    extraida em t=2.5 s, altura uniforme de 540 px sobre fundo do brand-kit.
- **Previews leves versionados** na pasta da entrega: `cover.png`,
  `thumb-16x9.png` e `preview-formats.png` (24 PNGs no total; nenhum MP4).
- **Manifesto v2** (`derivatives.json`): `schemaVersion: 2`, `sourceVideoSha256`,
  `allowAudioTrack`, `appliedAudioPolicy` e por derivado (`1x1`, `16x9`, `cover`,
  `thumb-16x9`, `preview-formats`): caminho relativo, dimensoes, fps, codec,
  audioStreams, audioCodec, bytes, sha256, ffprobe resumido, metadados de
  composicao e `versionedCopy` (imagens). Nenhum caminho absoluto de estacao.
- **Resolucao de `.workspace/`**: `resolve_workspace_root(repo_root)` tenta
  `repo_root/.workspace` (com `archives/`) e, em worktree sem `.workspace/`
  proprio, resolve o checkout principal via `git rev-parse --git-common-dir`
  (pai do `.git` compartilhado). Ferramentas: `build_video.get_ffmpeg()/
  get_ffprobe()` com fallback `<MAIN_ROOT>/.workspace/tools/ffmpeg`.
- **CLI**: `--all [--formats 1x1,16x9,cover,thumb,grid] [--force] [--json]` e
  `--tenant <id> [--campaign <slug>] [--json]`; pulo por integridade (skip) quando
  o manifesto v2 em disco ja cobre os formatos pedidos com hashes validos.
- **API**: `generate_campaign_derivatives(...)`, `generate_all_derivatives(...)`,
  `probe_media(...)`, `discover_campaigns(...)`, `resolve_workspace_root(...)`.
- Politica de audio estrita, auditoria ffprobe pre-manifesto e erros contratuais
  da rodada 1 preservados (+ `FORMATO_INVALIDO`, `WORKSPACE_NAO_ENCONTRADO`,
  `PREVIEW_COPIA_DIVERGENTE`).

### `tools/tests/test_derivative_formats.py` (v2, 12 testes)

1. `test_01` — 1x1 1080x1080/30 fps/h264/yuv420p com **`-an` forcado**
   (fonte COM audio + marca-salao): 0 streams; sonda independente confirma;
   metadados do primeiro plano 608x1080/pad 616/4 px/#F5C107.
2. `test_02` — 16x9 1920x1080 com o mesmo bloqueio.
3. `test_03` — cover PNG 1080x1920, t=2.5 s, tarjas #121620 + acento #F5C107,
   copia versionada com sha identico.
4. `test_04` — thumb 1920x1080 e prancha 9:16|1:1|16:9 (altura 540, fundo da
   marca) com copias versionadas integras.
5. `test_05` — multitrack-hub preserva AAC: 1 stream aac 44100 Hz stereo em 1x1
   e 16x9 (sonda independente).
6. `test_06` — `FONTE_SEM_AUDIO` rejeitado e nenhum derivado gerado.
7. `test_07` — integridade SHA-256/bytes dos 5 derivados contra o retorno e o
   `derivatives.json` v2 em disco; LF puro; **sem caminhos absolutos**; MP4s sem
   `versionedCopy`.
8. `test_08` — `FONTE_AUSENTE` / `ENTREGA_NAO_ENCONTRADA` / `FORMATO_INVALIDO`.
9. `test_09` — `resolve_workspace_root` (worktree -> checkout principal) e
   `probe_media` normalizado.
10. `test_10` — `discover_campaigns` (>= 8 entregas reais, filtros), pulo por
    integridade (skip) e regeneracao com `force=True`.
11. `test_11` — CLI `--tenant --campaign --formats cover --force --json` exit 0,
    payload ok/generated=1; manifesto preserva entradas dos formatos nao
    re-gerados.
12. `test_12` — validacao consolidada das 8 campanhas reais: manifestos v2
    versionados, dimensoes por formato, politica de audio por tenant, previews
    PNG com sha identico; MP4s conferidos quando presentes no `.workspace/`.

## 2. Execucao nas 8 campanhas (rodada 2)

Comando: `python tools/derivative_formats.py --all --force --json` (worktree,
fontes 9:16 arquivadas no checkout principal via `resolve_workspace_root`).
Relatorio: `ok=true, total=8, generated=8, skipped=0, errors=0`
(log: `.workspace/logs/etapa4-agente1/all-force-round2.json`).

| Tenant | Slug | Politica | src (12) | 1x1 (12) | 16x9 (12) | cover (12) | thumb (12) | grid (12) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| estudio-flow | camp-saas-demo-estudio-flow-001 | -an | 4256c7d9c73a | 3e19313171dc | d69956a99265 | b8d1a5326c6f | 38ce7ca2d726 | 736fa583b004 |
| marca-salao | camp-saas-demo-marca-salao-001 | -an | df1d45bbb8d7 | 88509bea624e | 26e94cdf20bf | b1b2c7ad44ce | 3ca6015838fe | 74ccc468c93a |
| marca-salao | camp-saas-demo-ns001-agenda-001 | -an | 45166ac75e7c | d47ddf83365b | 2b2d8099ac20 | 064fe6914ce9 | d94c940ff1ba | e38df77e0534 |
| meu-salao | camp-saas-demo-meu-salao-001 | -an | 76b3eb2ced36 | 40202ef56207 | 1caad008800d | abda6e305111 | 8811842a4891 | 5e8203fe53ec |
| meu-salao | camp-saas-demo-meu-salao-002 | -an | a2c9b047d498 | 2d7ab532ecaf | 4f7f5cbf97b6 | 05e5c0ab5e08 | 0493926491fa | a25e0010af34 |
| multitrack-hub | camp-shorts-completo-multitrack-001 | aac-44100-stereo | 2a909fbb4b80 | a1ad8e3e91ba | 5744688f821c | 631dc53b3cb4 | f5e50cc70d0a | 5f849c00ce3a |
| multitrack-hub | camp-shorts-rateios-002 | aac-44100-stereo | 3e141f3bc1fd | f29466c9fea6 | f4e1fc34a22c | 66bc14a85a01 | 0c7995eba129 | e2af7197ed66 |
| multitrack-hub | camp-shorts-stems-workflow-003 | aac-44100-stereo | 50b0a0fcfa8f | 9a5d949f1bf7 | dec1784fcce6 | 9fb74cbb11ff | 243e0d42d2d2 | 90ee5ead70fd |

## 3. Auditoria independente (ffprobe direto, fora do motor)

- **16 MP4s** em `.workspace/archives/<slug>/derivatives/` (8x1x1 + 8x16x9):
  todos `h264`, `yuv420p`, `30/1 fps`, geometria 1080x1080 / 1920x1080.
- **Audio**: os 10 MP4s dos tenants `-an` (estudio-flow 1, marca-salao 2,
  meu-salao 2 — por formato) com **0 streams**; os 6 MP4s multitrack-hub com
  **1 stream `aac,44100,2`** cada.
- **24 PNGs versionados** (8x cover.png + 8x thumb-16x9.png + 8x
  preview-formats.png) e **8 derivatives.json v2** nas pastas de entrega;
  **0 arquivos .mp4/.wav** em `02-reels-shorts/deliveries/`.
- ffmpeg/ffprobe 9.0.2 (gyan.dev full build) no PATH da estacao.

## 4. Suite de testes

- Modulo alvo: `python -m unittest tools.tests.test_derivative_formats -v` ->
  **12/12 OK em 33.2 s** (0 falhas, 0 erros, 0 skips).
- Discover completo: `python -m unittest discover -s tools/tests -v` ->
  `Ran 270 tests in 269.4s — FAILED (failures=2, errors=34, skipped=59)`, exit 1.
  As 2 failures + 34 errors estao **todas** em modulos studio (`test_studio_*`,
  `test_campaign_studio_e2e`, `test_queue_process_restart`, `test_studio_work_backup`,
  `test_render_local` timeout) que exigem `platform/dist` compilado — condicao
  pre-existente desta worktree nova (sem build npm), **sem relacao com esta
  etapa** e identica ao baseline registrado na rodada 1; os 12 testes de
  `test_derivative_formats` estao todos `ok` no mesmo log
  (`.workspace/logs/etapa4-agente1/suite-discover-round2.log`).

## 5. Arquivos versionados neste commit (rodada 2)

- `tools/derivative_formats.py` (v2)
- `tools/tests/test_derivative_formats.py` (v2, 12 testes)
- `02-reels-shorts/deliveries/{estudio-flow,marca-salao,meu-salao,multitrack-hub}/*/derivatives.json`
  (8 manifestos v1 -> v2)
- `02-reels-shorts/deliveries/*/cover.png`, `thumb-16x9.png`, `preview-formats.png`
  (24 previews leves novos)

Permanecem somente no `.workspace/` local (por desenho): os 16 MP4s + 40 PNGs
derivados em `archives/<slug>/derivatives/`, fontes 9:16, relatorios JSON e este
devlog.

### Sessão 2026-11-18 — Etapa 4 (Agente 2): Portal de Revisão do Titular (`tools/review_dashboard.py` + `05-review-portal/`)
<!-- devlog-sync:etapa4-agente2.md -->

- **Branch de trabalho:** `codex/etapa4-agente2-review-portal` (baseada em `main` `823c416`).
- **Worktree isolada:** `C:/Repos/marcasalao-marketing/.workspace/worktrees/etapa4-agente2` (criada com `git worktree add -b`, dentro de `<RAIZ>/.workspace/worktrees/`).
- **Papel:** Engenheiro Full-Stack de Ferramentas Internas (Agente 2 de 4 da Etapa 4, paralelo).
- **Território respeitado:** alterações restritas a `tools/review_dashboard.py`, `tools/tests/test_review_dashboard.py`, `05-review-portal/**` e `.workspace/devlogs/etapa4-agente2.md`. `contexto_projeto.md` não foi alterado; nenhuma worktree histórica nem dos agentes 1, 3 e 4 foi tocada.

#### 1. Entregáveis criados

1. **`tools/review_dashboard.py`** — gerador e servidor do portal de revisão, stdlib pura (zero dependências externas), dois modos CLI:
   - **`--build [--output-dir 05-review-portal] [--json]`**: consolida, por tenant, o `tenants/<id>/brand-kit.json` (nome, monograma, domínio, tagline, paleta de 7 cores, `audioPolicy`) e `tenants/<id>/guardrails.json`; percorre as entregas `02-reels-shorts/deliveries/<tenantId>/<slug>/` (lendo `manifest.json`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png`), os pacotes `04-legendas/pacotes-publicacao/<tenantId>/<slug>/` (`checklist-publicacao.json` + `instagram-reels.md` / `youtube-shorts.md` / `facebook-reels.md`) e os vídeos `.workspace/archives/<slug>/` (hashes e bytes do manifesto, sem copiar os MP4s). Gera `05-review-portal/index.html`, `05-review-portal/portal-data.json` e `05-review-portal/README.md`.
   - **`--serve [--port 8765]`**: servidor HTTP local somente-leitura sobre `http.server` (bind `127.0.0.1`, `ThreadingHTTPServer`), com rotas whitelisted (`/`, `/index.html`, `/portal-data.json`, `/deliveries/<rest>` limitado a `.png/.srt/.txt/.json/.md`, `/archives/<rest>` limitado a `.mp4`), rejeição de `..`/`\`/NUL, contenção `realpath` contra a raiz, apenas `GET`/`HEAD` (POST/PUT/DELETE → 501), `Cache-Control: no-store` e suporte a HTTP Range para streaming/seek dos MP4s (206 com `Content-Range` e 416 com `bytes */<size>`).
   - **Interface (embutida no `index.html`, funciona via `file://` e via `--serve`):** filtros por tenant (4), por preset (`saas-demo` vs `shorts-completo`) e por política de áudio (`-an` vs `AAC`); cartões por campanha com paleta do tenant (monograma colorido, chips de preset/áudio/status); preview storyboard 2×2 e player `<video>` quando servido (com fallback automático para storyboard + nota quando o MP4 não existe na estação); abas Legenda `.srt`, Roteiro de Narração, Copy Instagram/YouTube/Facebook com botões Copiar (clipboard + fallback `execCommand`) e link UTM rastreado extraído do `.md` de cada canal; checklist interativo de aprovação humana com 7 itens por campanha, campo revisor e observações, persistido em `localStorage` (chave `reviewPortal.aprovacoes.v1`); botão **Exportar JSON de Aprovações** que baixa `aprovacoes-titular.json` (resumo + por campanha: `tenantId`, `slug`, `campaignId`, `preset`, `politicaAudio`, `aprovada`, `revisor`, `observacoes`, `itens` e `hashes` SHA-256 de vídeo/SRT/narração/storyboard).
2. **`tools/tests/test_review_dashboard.py`** — 18 testes `unittest` cobrindo: helpers de hash/UTM; build real (3 arquivos gerados com hashes/tamanhos conferidos; 4 tenants e 8 campanhas; campos por campanha; hashes SHA-256 contra disco e contra o `manifest.json`; zero vazamento de caminhos absolutos/UNC/`..` em qualquer string do `portal-data.json`; determinismo — dois builds produzem bytes idênticos; marcadores de UI no HTML; README documenta `--build`/`--serve`); servidor HTTP em raiz falsa com porta efêmera (`port=0`): 200 nas rotas válidas, Range 200/206/416 com `Content-Range` exatos, 9 casos de traversal/extensão/rota → 404 (incluindo `%2e%2e` e `..%5c`), POST/PUT/DELETE → 501, HEAD → 200; e servidor sobre a raiz real servindo portal, dados e storyboard.
3. **`05-review-portal/`** — portal gerado para os **4 tenants** (`estudio-flow`, `marca-salao`, `meu-salao`, `multitrack-hub`) e **8 campanhas**:
   - `estudio-flow`: `camp-saas-demo-estudio-flow-001` (`-an`)
   - `marca-salao`: `camp-saas-demo-marca-salao-001`, `camp-saas-demo-ns001-agenda-001` (`-an`)
   - `meu-salao`: `camp-saas-demo-meu-salao-001`, `camp-saas-demo-meu-salao-002` (`-an`)
   - `multitrack-hub`: `camp-shorts-completo-multitrack-001`, `camp-shorts-rateios-002`, `camp-shorts-stems-workflow-003` (`AAC`)

#### 2. Decisões técnicas

- **Determinismo entre estações:** `portal-data.json` não contém timestamps nem caminhos absolutos — dois builds produzem bytes idênticos (verificado por SHA-256), permitindo versionar `05-review-portal/` sem falsos diffs entre máquinas.
- **Independência de estação:** os MP4s vivem em `.workspace/archives/` (local por estação, fora do Git); o `portal-data.json` registra apenas hash/bytes/caminho relativo, e a disponibilidade é sondada em runtime pelo JS (via `--serve`, `<video>` com `onerror` → fallback storyboard + nota). Na worktree os 8 vídeos estão ausentes e o fallback foi exercitado no navegador; no checkout com archives o player streama via Range.
- **Segurança do servidor:** nenhuma escrita em disco, apenas `GET`/`HEAD`; rotas e extensões whitelisted; `realpath` + contenção contra a raiz; URLs decodificadas com `unquote` e rejeição explícita de `..`, `\` e NUL.
- **JSON embutido:** o `portal-data.json` é injetado no `index.html` como `<script type="application/json">` com escape de `</` → `<\/`, funcionando tanto via `file://` quanto via `--serve` sem fetch adicional.
- **Convenções do projeto:** `render_local.fs_path()` para caminhos longos no Windows, `render_local.contained()`/`rel()` para contenção, exceções com códigos MAIÚSCULOS (`RAIZ_INVALIDA`, `PORTAL_NAO_GERADO`, `ARQUIVO_NAO_ENCONTRADO`, `HASH_DIVERGENTE`, `PORTA_INDISPONIVEL`), saída `--json`, LF (`newline="\n"`), código sem acentos.

#### 3. Verificação (evidência bruta)

- **Build (`python tools/review_dashboard.py --build --json`):** `"ok": true`, `totalTenants: 4`, `totalCampaigns: 8`, `videosLocais: {encontrados: 0, ausentes: 8}` (worktree sem archives — esperado), arquivos com hashes:
  - `05-review-portal/portal-data.json` — `60d88279ea6d8668e5bb3cb13a331619425b523d9f0f421c503bf2ba3313c170` (49.435 B)
  - `05-review-portal/index.html` — `c6f9c18141ec580dcb1ab32b52babffc906a9f2173f0c9a35713724d47d2594c` (60.465 B)
  - `05-review-portal/README.md` — `0c6d229bd3a9ccab1b8237996ac95408eaf28344346bf7b0ac4c79fb4ee6f690` (3.102 B)
  - `sha256sum` em disco confere byte a byte com o resumo do build (rebuild determinístico).
- **Suíte:** `python -m unittest tools.tests.test_review_dashboard -v` → **18/18 OK em 2,154s**.
- **Prova no navegador (Playwright, servido em `http://127.0.0.1:8765/`):**
  - 8 cartões renderizados; filtros: tenant `multitrack-hub` → 3 cartões, preset `shorts-completo` → 3, áudio `AAC` → 3, reset → 8.
  - Aba "Copy Instagram" exibe o texto do `.md` e o link UTM `https://estudioflow.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow`.
  - Botão "Copiar" → `"Copiado!"` com reversão após 1,5s; botão "Copiar link UTM" → `"Copiado!"`.
  - Checklist com 7 itens: marcar todos → chip "Aprovada"; desmarcar um → "Em revisão 6/7"; campo revisor persistido ("Titular"); estado em `localStorage` chave `reviewPortal.aprovacoes.v1`.
  - "Exportar JSON de Aprovações" interceptado: arquivo `aprovacoes-titular.json`, `application/json`, `schemaVersion: 1`, `origem: "05-review-portal"`, `resumo {totalCampanhas: 8, aprovadas: 0, pendentes: 8}`, campanha com `revisor: "Titular"`, 6/7 itens e hash SHA-256 do vídeo presente.
  - Modo servido: `<video>` criado com `src="/archives/<slug>/<slug>.mp4"`; com MP4 ausente na worktree o `onerror` substituiu por storyboard + nota "MP4 não disponível nesta estação (.workspace/archives é local por estação)."
  - Console do navegador: apenas os 404 esperados dos MP4s ausentes; **zero erros de JavaScript**.
  - Screenshots: `.workspace/logs/etapa4-agente2/etapa4-agente2-portal-grid.png` e `.workspace/logs/etapa4-agente2/etapa4-agente2-checklist.png`.
- **Servidor encerrado após a prova** (porta 8765 livre).

#### 4. Escopo e limites

- O portal é ferramenta de revisão humana: nenhum dado é enviado a serviços externos, nada é publicado/agendado, `autoPublish` permanece `false` em todos os checklists consolidados.
- As aprovações ficam em `localStorage` do navegador (por estação/máquina) e o JSON exportado é o artefato de registro manual do fluxo existente.
- Não houve alteração em `contexto_projeto.md`, `tools/publish_pack.py`, `tools/devlog_sync.py` ou qualquer arquivo de outros agentes.
- **Nota para a consolidação (fora do território deste agente):** `.gitattributes` não cobre `05-review-portal/**`. Os blobs commitados são LF (determinísticos no Git), mas num checkout Windows com `core.autocrlf=true` a cópia de trabalho viraria CRLF até o próximo `--build` (ruído de diff apenas). Sugestão para o consolidador, seguindo o precedente da Etapa 3: adicionar `05-review-portal/** text eol=lf`.

- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `C:/Repos/marcasalao-marketing`.

---

# Etapa 4 — Agente 2 (Full-Stack de Ferramentas Internas) — devlog

- Data: 19/11/2026
- Branch: `codex/etapa4-agente2-review-portal`
- Worktree: `<RAIZ>/.workspace/worktrees/etapa4-agente2`
- Base: `f83fce3` (portal v1 — build + servidor somente leitura)
- Território exclusivo respeitado: `tools/review_dashboard.py`,
  `tools/tests/test_review_dashboard.py`, `05-review-portal/**`.
  `contexto_projeto.md` não foi tocado.

## Brief expandido — o que foi entregue

### 1. Modelo de dados expandido (`_collect_campaign`)

- `titulo` (primeira linha da copy Instagram; fallback `campaignId`).
- `cover` e `formats`: PNGs opcionais da entrega (`cover.png`,
  `preview-formats.png`), `None` quando ausentes.
- `derivatives`: leitura opcional de `derivatives.json` na entrega
  (`{variant, path, sha256, bytes}`, path relativo ao diretório do slug em
  `.workspace/archives/`); malformado aborta o build com
  `DERIVATIVOS_INVALIDOS` (fail-closed).
- `video.variants`: variante primária derivada da geometria
  (`9x16`/`16x9`/`1x1`) + derivadas declaradas.
- `pacote`: checklist de publicação (`guardrailsAudited`, `autoPublish`,
  `guardrailStatus`).

### 2. Resolução de `.workspace/` entre estações

- `resolve_workspace_dir(root)`: quando a raiz é o toplevel de uma worktree
  (`--git-dir` ≠ `--git-common-dir`), resolve a raiz principal via
  `git rev-parse` e usa o `.workspace/` dela (archives de vídeo e
  aprovacoes do titular ficam no checkout principal); raízes não-toplevel
  usam o próprio `<raiz>/.workspace`. `approvals_store_path` deriva de
  `resolve_workspace_dir` (`<workspace>/tmp/aprovacoes-titular.json`).

### 3. UI executiva (index.html v2)

- Painel de métricas (nichos, campanhas, vídeos -an × AAC, % guardrails
  conformes, aprovados/pendentes/ajustes dinâmicos).
- Filtros tenant (monograma + swatch da paleta), preset, áudio, status e
  busca textual (slug, título, legenda, roteiro, rotas, UTM).
- Cartões com player por variante (servido), storyboard com lightbox, abas
  SRT em blocos numerados, narração, copies por rede com contador e URL UTM,
  aba Guardrails & Hashes.
- Controle editorial v2: decisão (`aguardando`/`aprovado`/`ajuste`),
  conferência de locução externa (tenants `-an`) e observações; persistência
  em `localStorage` (`reviewPortal.aprovacoes.v2`) + sync debounced
  `POST /api/approvals` quando servido; exportar/importar
  `aprovacoes-titular.json`.
- Badge do servidor via `GET /api/health`.

### 4. Servidor HTTP v2

- Rotas novas: `GET /api/health`, `GET /api/data`,
  `GET /media/storyboard|cover|formats/<tenant>/<slug>`,
  `GET /media/video/<tenant>/<slug>/<variante>` (Range 200/206/416; derivadas
  via `derivatives.json` ou convenção `<stem>-<variante>.mp4`),
  `GET|POST /api/approvals`.
- Rotas legadas mantidas: `/deliveries/...` (extensões permitidas) e
  `/archives/<slug>/<arquivo>.mp4`.
- Escrita restrita: `POST /api/approvals` com validação estrita do schema v2
  (`JSON_INVALIDO`, `SCHEMA_INVALIDO`, `CHAVE_DESCONHECIDA`,
  `CAMPANHA_DESCONHECIDA`, `DECISAO_INVALIDA`, `TIPO_INVALIDO`), corpo
  limitado a 1 MB, persistência em `<workspace>/tmp/aprovacoes-titular.json`;
  demais métodos → 405. Traversal (`..`, `%2e%2e`, `\`, UNC) → 404; toda
  resolução confinada por `render_local.contained` com base explícita
  (raiz do portal × archives resolvidos).

### 5. CLI

- Três modos mutuamente exclusivos: `--build`, `--serve`
  (reconstrói antes de servir), `--export-aprovacoes` (stdout do documento
  persistido; sem arquivo → `APROVACOES_AUSENTES`, exit 1). `--host` novo.

### 6. Escape do JSON embutido

- `render_index_html` escapa `</` → `<\/` no bloco
  `<script id="portal-data">`; `json.loads` restaura o documento idêntico.

## TDD

- 26 testes escritos antes da implementação (RED confirmado: 25/26 falhando
  pelos motivos certos + 1 guarda).
- GREEN em uma única execução: `Ran 26 tests ... OK` (3.3 s), incluindo
  servidor efêmero (porta 0) sobre raiz falsa e sobre a raiz real da
  worktree, roundtrip de aprovacoes e rejeição de schemas inválidos.

## Suíte completa (regressão)

- Comando: `python -m unittest discover -s tools/tests -p "test_*.py"`
  na worktree. **Resultado final limpo: `Ran 413 tests ... OK`
  (2980 s)**, exit 0. Evidência: `<RAIZ>/.workspace/logs/etapa4-agente2/full-suite.log`.
- Pré-requisito descoberto: as suítes `test_studio_*`, `test_queue_process_restart`
  e `test_campaign_studio_e2e` exigem `platform/dist` (build TypeScript).
  Executado `npm ci` + `npm run build` com Node 22.23.2 na worktree
  (`platform/node_modules` e `platform/dist`, ambos ignorados pelo Git).
  Primeira passada (sem build): 34 erros + 1 falha e2e, todos atribuídos ao
  build ausente (`build da platform ausente; execute npm run build em platform/`).
  Re-execução das 9 suítes afetadas: 98 testes, OK.
- `test_render_local.test_render_timeout_preserves_delivery` falhou 1 vez na
  primeira passada (exit 2 ≠ 1) e passou isolado e na re-execução completa —
  transitório de ordem (não toca este módulo).
- Efeito colateral dos testes: 8 `checklist-publicacao.json` de
  `04-legendas/pacotes-publicacao/` são reauditados pelas suítes e gravam
  `sha256_disk_ok: false` (MP4s ausentes nesta estação). Restaurados com
  `git checkout --` **após** a suíte; não entraram no commit (fora do território).

## Prova no navegador (Playwright, servidor em 127.0.0.1:8791)

- Página carrega com título correto; único erro de console: `favicon.ico`
  404 (esperado, sem rota de favicon).
- Métricas: 4 nichos · 8 campanhas · 5 vídeos -an · 3 AAC · 100% conformes ·
  0 aprovados · 8 pendentes · 0 ajustes; badge
  "Servidor ativo · 4 tenants · 8 campanhas".
- Filtro tenant `marca-salao` → 2 cartões e swatch muda para `#F5C107`.
- Busca "rateios" → 3 cartões correspondentes.
- Decisão "Aprovado para Publicação Manual" no 1º cartão → chip atualizado,
  métricas 1/7 e documento persistido em
  `<RAIZ>/.workspace/tmp/aprovacoes-titular.json` (schemaVersion 2, 8 itens,
  resumo 1 aprovada) — confirma a resolução `git-common-dir` na prática.
- Lightbox abre/fecha; abas completas; aba Guardrails lista rotas
  autorizadas, claims bloqueados, `autoPublish: false`,
  `guardrailsAudited: true` e 4 hashes SHA-256.
- Player: MP4 ausente nesta estação (archives são locais por estação; só há
  `r002-video-local`) → 404 legítimo com fallback desenhado
  "MP4 não disponível nesta estação". O streaming em si (200/206/416,
  derivadas) está coberto pelo teste 17 sobre raiz falsa.
- Evidência: `<RAIZ>/.workspace/logs/etapa4-agente2/portal-proof.png`
  (captura full-page; cópia externa removida).

## Resíduos removidos

- Arquivo `aprovacoes-titular.json` gerado pela prova (decisão fictícia)
  removido de `<RAIZ>/.workspace/tmp/` ao final.
- Servidor de prova encerrado (porta 8791 livre).

## Arquivos alterados (versionados)

| Arquivo | Δ |
| --- | --- |
| `tools/review_dashboard.py` | +1320/-… (build v2, servidor v2, CLI v3 modos) |
| `tools/tests/test_review_dashboard.py` | 26 testes (hash, UTM, workspace, build, escape, servidor, CLI) |
| `05-review-portal/index.html` | UI v2 (painel, filtros, busca, lightbox, abas, aprovacao) |
| `05-review-portal/portal-data.json` | modelo expandido (titulo, cover, formats, derivatives, variants, pacote) |
| `05-review-portal/README.md` | documentação v2 (endpoints, aprovações, modo servido) |

## Pendências / observações para o próximo agente

- Os 8 MP4s de campanha não existem nesta estação (`.workspace/archives`
  contém apenas `r002-video-local`); o player cai no storyboard por desenho.
  Numa estação com os archives, o streaming funciona sem mudança de código.
- `portal-data.json` é determinístico; após qualquer mudança de dados nos
  deliveries, rodar `--build` novamente.

### Etapa 4 — Agente 3: Calendário Editorial & Matriz UTM (2026-11-18)
<!-- devlog-sync:etapa4-agente3.md -->

Branch: `codex/etapa4-agente3-calendario-utm` (worktree `.workspace/worktrees/etapa4-agente3`, base `main` @ 823c416).
Território respeitado: `tools/campaign_calendar.py`, `tools/tests/test_campaign_calendar.py`,
`04-legendas/calendario-editorial.md`, `04-legendas/calendario-editorial.json`, `docs/rastreio-utm.md`,
`.workspace/devlogs/etapa4-agente3.md`. `contexto_projeto.md` não foi tocado.

#### Tarefa 1 — Gerador de Calendário Editorial & Matriz UTM

- `tools/campaign_calendar.py`: módulo + CLI (`--start-date YYYY-MM-DD`, `--json`, `--root`).
  - Lê os 4 tenants via `tenant_validator.load_and_validate_tenant(strict=True)` e os pacotes em
    `04-legendas/pacotes-publicacao/<tenantId>/<slug>/checklist-publicacao.json` (8 campanhas).
  - Valida cada checklist: `TENANT_DIVERGENTE` (tenantId divergente) e `AUTO_PUBLICACAO_INVALIDO`
    (`autoPublish` != false) abortam antes de gravar.
  - Distribuição intercalada gulosa: até 2 campanhas/dia, uma por tenant por dia, tenants ordenados
    por (-campanhas restantes, tenantId) — garante a regra dura **nunca duas campanhas do mesmo
    tenant no mesmo dia**. Cada campanha cobre os 3 canais (Instagram Reels, YouTube Shorts,
    Facebook Reels): 8 × 3 = 24 slots.
  - Cada slot: `slotId` (slot-001..024), `dataSugerida`, `janelaHorario` (12:00-13:00 Instagram,
    18:00-19:00 YouTube, 19:00-20:00 Facebook), `tenantId`, `brandName`, `slug`, `canal`,
    `formato`, `audioPolicy` (do tenant: `-an` + locução externa para estudio-flow/marca-salao/
    meu-salao; faixa própria para multitrack-hub), `utmUrl` (fórmula idêntica ao publish_pack:
    `https://{domain}/?utm_source={source}&utm_medium={medium}&utm_campaign={slug}&utm_content={tenantId}`),
    `statusEditorial: "aguardando_aprovacao_titular"`, `autoPublish: false`.
  - Auditoria guardrails por tenant (`validate_text_against_guardrails(check_ui_elements=True)`)
    sobre brandName + tagline + CTA + URL + nota de áudio de cada slot; qualquer violação aborta
    antes de gravar (`GUARDRAIL_VIOLACAO`). Armadilha conhecida evitada: "meu salão" é
    forbiddenClaim de marca-salao — o texto consolidado nunca é auditado contra guardrails de
    outro tenant.
  - Saídas determinísticas (sem timestamps), UTF-8, LF (`newline="\n"`, `ensure_ascii=False`):
    `04-legendas/calendario-editorial.json` (estruturado) e `04-legendas/calendario-editorial.md`
    (cronograma visual, checklist pré-publicação de 10 itens — incluindo lembrete de locução
    externa para tenants `-an` — e matriz UTM consolidada de 24 URLs).

#### Tarefa 2 — Execução, rastreio-utm.md e testes

- Execução oficial: `python tools/campaign_calendar.py --start-date 2026-11-23 --json` →
  `ok: true`, 24 slots, 8 campanhas, 4 tenants, `guardrailViolations: []`, período
  2026-11-23 → 2026-11-26. Hashes: JSON
  `0c867e31fe8a930784d2e2230a27caf9e705694396b4d61cb966e508268bff14` (16719 bytes), MD
  `25d485a08b36055ed0a33f52201f96f6aa86184ad99afcbca7f531ee63319a6e` (11109 bytes).
  Distribuição por dia (2 campanhas de tenants distintos):
  - 2026-11-23: camp-shorts-completo-multitrack-001 + camp-saas-demo-marca-salao-001
  - 2026-11-24: camp-saas-demo-meu-salao-001 + camp-shorts-rateios-002
  - 2026-11-25: camp-saas-demo-estudio-flow-001 + camp-saas-demo-ns001-agenda-001
  - 2026-11-26: camp-saas-demo-meu-salao-002 + camp-shorts-stems-workflow-003
- `docs/rastreio-utm.md` atualizado (versão 1.0 → 1.2):
  - Seção 5 ganhou **5.1 Passo a passo de configuração (antes da primeira publicação)** com os
    três candidatos — GA4, Plausible, Umami — por domínio de tenant, teste de ponta a ponta com
    URL da matriz e checklist comum (decisão do titular; sem analytics validado, links UTM não
    são declarados ativos).
  - Seção 6: tabela de 9 URLs substituída pela **matriz consolidada de 24 URLs (8 campanhas ×
    3 canais)**, cobrindo estudio-flow, marca-salao (2 campanhas), meu-salao (2) e
    multitrack-hub (3). Verificação programática: 24/24 URLs idênticas entre o doc e o
    `calendario-editorial.json`.
  - Nova seção 7 documenta o `tools/campaign_calendar.py` (regras, CLI, saídas, cronograma
    vigente); Histórico renumerado para seção 8 com linha nova.
- `tools/tests/test_campaign_calendar.py` (8 testes, todos passando):
  1. distribuição sem colisão mesmo-tenant/mesmo-dia; 2. contagem de slots = 24;
  3. cada campanha cobre exatamente os 3 canais; 4. `autoPublish: false` e
  `statusEditorial` corretos em todos os slots; 5. integridade das URLs UTM (fórmula
  publish_pack); 6. `audioPolicy` por tenant; 7. idempotência (regeneração produz bytes
  idênticos); 8. data inválida aborta com erro.

#### Evidências de teste

- `python tools/tests/test_campaign_calendar.py` → Ran 8 tests, OK.
- Regressão: `test_publish_pack.py` (7 OK), `test_tenant_contracts.py` (7 OK),
  `test_devlog_sync.py` (4 OK).
- Verificação de documento: seções 1..8 em ordem, strings pt-BR com contagem exata,
  3 linhas de histórico, seções pré-existentes preservadas.

#### Observações para consolidação

- `test_publish_pack.py` regenera os checklists e, em worktree sem os `.mp4` das entregas
  (não rastreados pelo Git), marca `sha256_disk_ok: false`. Os 8 checklists foram restaurados
  ao HEAD antes do commit — a mudança era artefato do worktree, fora do território deste agente.
- Sugestão (arquivo `.gitattributes` fora do meu território): adicionar
  `04-legendas/calendario-editorial.json text eol=lf` e `04-legendas/calendario-editorial.md
  text eol=lf` para bytes estáveis entre estações, seguindo o padrão já aplicado a
  `04-legendas/pacotes-publicacao/**`.
- Suíte completa (studio/render) não foi executada: ~40 min com REQUIRE_RENDER e sem
  interseção com o território desta tarefa; a regressão cobriu os módulos consumidos
  (publish_pack, tenant_validator, devlog_sync).

---

### Etapa 4 — Agente 3: Calendário Editorial v2 & Matriz UTM expandida (2026-11-19)

Branch: `codex/etapa4-agente3-calendario-utm` (worktree `.workspace/worktrees/etapa4-agente3`,
base `main` @ f7298dc). Território v2: `tools/campaign_calendar.py`,
`tools/tests/test_campaign_calendar.py`, `04-legendas/calendario-editorial.md`,
`04-legendas/calendario-editorial.json`, `04-legendas/matriz-utm-consolidada.csv`,
`docs/rastreio-utm.md`, `.workspace/devlogs/etapa4-agente3.md`. `contexto_projeto.md` e
`.gitattributes` não tocados (sugestão de eol=lf para o CSV registrada abaixo).

#### Tarefa 1 — Motor de planejamento editorial v2 (campaign_calendar.py)

- CLI estendida: `--start-date YYYY-MM-DD`, `--weeks N` (padrão 4), `--json`; API programática
  `build_editorial_calendar(...)`.
- **Onda 1 (semanas 1-2, 24 slots 9:16):** 8 campanhas × 3 canais. Dias publicáveis
  segunda-sábado (domingo nunca publica); cada campanha ocupa uma lane com offsets de canal
  +0/+2/+4 dias na ordem interna youtube → instagram → facebook — única ordem que satisfaz o
  espaçamento ≥48h entre canais da mesma campanha com janelas fixas (yt 12:00 D → ig 18:30
  D+2 = 54,5h → fb 20:00 D+4 = 49,5h). Regra dura mantida: nunca duas publicações do mesmo
  tenant no mesmo dia. Janelas v2: YouTube 12:00-13:00, Instagram 18:30-19:30, Facebook
  20:00-21:00 (BRT).
- **Onda 2 (semanas 3-4, 8 slots):** 1 slot de reaproveitamento por campanha, alternando
  Instagram Feed 1:1 (`utm_content=repurpose-1x1`, `utm_medium=feed`) e YouTube Vídeo 16:9
  (`utm_content=repurpose-16x9`, `utm_medium=video`); o checklist do slot referencia a mídia
  derivada `<slug>-1x1.mp4` / `<slug>-16x9.mp4` e o `derivatives.json` da entrega (Agente 1);
  zero colisão tenant-dia também na Onda 2.
- **Hooks A/B:** `hookVarianteA` = abertura original da legenda do canal no pacote
  (`instagram-reels.md` / `youtube-shorts.md` / `facebook-reels.md`); `hookVarianteB` =
  abertura alternativa de clareza operacional por nicho (salão/agenda, link de agendamento,
  aulas/turmas em estúdio, stems/rateios multitrack).
- Auditoria guardrails obrigatória por slot sobre hooks A/B + títulos + notas operacionais +
  URLs UTM contra os guardrails do PRÓPRIO tenant (`check_ui_elements=True`); qualquer
  violação aborta com `GUARDRAIL_VIOLACAO` antes de gravar qualquer arquivo. Armadilha
  preservada: "meu salão" é forbiddenClaim de marca-salao mas brandName de meu-salao — texto
  de um tenant nunca é auditado contra guardrails de outro.
- Capacidade: `SEMANAS_INSUFICIENTES` (rc 1) quando weeks < onda1Weeks + ceil(campanhas/6).
- 3 artefatos sincronizados, determinísticos (sem timestamps), UTF-8, LF:
  - `calendario-editorial.json`: 32 slots com `slotId, onda, semana, dataSugerida, diaSemana,
    janelaHorarioBrt, tenantId, brandName, slug, preset, audioPolicy, canal, formatoVideo,
    hookVarianteA, hookVarianteB, utmParams, utmUrl, checklistPrePublicacao, statusEditorial,
    autoPublish` + metadados consolidados, regras aplicadas e métricas por tenant/canal.
  - `calendario-editorial.md`: resumo executivo por tenant e por canal, cronograma completo
    das 4 semanas, checklist de operação manual pré-publicação (11 itens — incl. locução
    externa para tenants `-an` e confirmação de analytics ativa) e tabela de URLs UTM por
    campanha.
  - `matriz-utm-consolidada.csv`: 32 linhas × 20 colunas padronizadas (`slot_id` …
    `auto_publish`), UTF-8 com fim de linha LF, pronta para Google Sheets/Excel/Looker Studio.

#### Tarefa 2 — docs/rastreio-utm.md (v1.2 → v1.3)

- Seção 2: nova subseção **Convenção multi-tenant (Etapa 4)** — tabela dos 4 tenants com
  domínios e nichos + regras de `utm_content` por onda; conteúdo Fase 1 preservado
  integralmente.
- Seção 5: nova subseção **5.2 Guia de leitura dos UTMs (antes da primeira publicação)** —
  como conferir source/medium/campaign/content em GA4, Plausible e Umami, com teste de ponta
  a ponta e conversão nomeada por tenant.
- Seção 6: nova subseção **6.1 Matriz de reaproveitamento — Onda 2** com as 8 URLs
  `repurpose-1x1` / `repurpose-16x9` (matriz completa = 24 + 8 = 32 URLs, casando com o CSV).
- Seção 7 reescrita para o calendário v2 (2 ondas, regras duras, CLI com `--weeks`, 3 saídas,
  cronograma vigente por semana). Histórico (seção 8) com linha nova de 2026-11-19.
- Verificação programática do doc: 32/32 URLs do calendário presentes verbatim; 8/8 Onda 2;
  strings pt-BR por contagem exata; zero caracteres de corrupção; 406 linhas.

#### Tarefa 3 — Execução oficial e testes

- `python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 4 --json` → `ok: true`,
  32 slots, 8 campanhas, 4 tenants, `guardrailsAudited: true`, `guardrailViolations: []`,
  período 2026-11-23 → 2026-12-15. Hashes: JSON
  `b7288f75d1bf5f4661aeec96d3bf796dfb55349b6fd9b40b4f34582b1e864ab1` (66647 bytes), MD
  `658ca3e3e1f6bed60e640fe2b4ae929ea0e399f986c3ba6ff42395025dda5f4f` (19888 bytes), CSV
  `609f186e44f7e30f658a2728985f182d058ce784d8b82294a4c95b8304dc70e3` (11983 bytes).
- Distribuição: semanas {1: 12, 2: 12, 3: 6, 4: 2}; ondas {1: 24, 2: 8}; tenants
  {estudio-flow: 4, marca-salao: 8, meu-salao: 8, multitrack-hub: 12}; canais
  {instagram: 12, youtube: 12, facebook: 8}.
- `tools/tests/test_campaign_calendar.py` reescrito: **14 testes, todos passando** —
  01 contagem 32 (24+8) cobrindo 4 tenants/8 campanhas; 02 anti-colisão mesmo-tenant/mesmo-
  dia; 03 ≥48h entre canais da mesma campanha na Onda 1; 04 validade sintática das 32 URLs
  (urlparse + 4 parâmetros UTM); 05 unicidade de slotId e (slug, canal, onda); 06 autoPublish
  false + statusEditorial em 100% dos slots; 07 guardrails dos hooks A/B nos 4 tenants;
  08 paridade JSON↔CSV (32 registros); 09 bloqueio com frase proibida injetada; 10 CLI
  `--start-date` + `--json` rc 0; 11 dias publicáveis e semanas; 12 alternância e formatos da
  Onda 2; 13 saídas operacionais do Markdown; 14 idempotência (regeneração byte a byte).
- Regressões: `test_publish_pack.py` (7 OK), `test_tenant_contracts.py` (7 OK),
  `test_devlog_sync.py` (7 OK), `test_release_audit.py` (11 OK) — 32 testes de regressão.

#### Observações para consolidação

- `test_publish_pack.py` voltou a regenerar os 8 checklists no worktree (sem os `.mp4`) e a
  inverter `sha256_disk_ok` para false; restaurados ao HEAD antes do commit (32× true).
- Sugestão mantida (`.gitattributes` fora do território): estender o padrão `text eol=lf` a
  `04-legendas/matriz-utm-consolidada.csv` (novo arquivo; `calendario-editorial.*` já foram
  cobertos pelo consolidador após a v1).
- Suíte studio/render completa não executada (sem interseção com o território; as regressões
  cobriram publish_pack, tenant_validator, devlog_sync, release_audit).

### Sessão 2026-11-18 — Etapa 4 (Agente 4): Gate de Release (`tools/release_audit.py`), Sync de Devlogs Multi-Etapa e Documentação Mestra
<!-- devlog-sync:etapa4-agente4.md -->

- **Branch de trabalho:** `codex/etapa4-agente4-release-gate-docs` (baseada em `main` `823c416`).
- **Worktree isolada:** `<RAIZ>/.workspace/worktrees/etapa4-agente4` (nesta estação: `C:/Repos/marcasalao-marketing/.workspace/worktrees/etapa4-agente4`).
- **Território respeitado:** alterações restritas a `tools/devlog_sync.py`, `tools/tests/test_devlog_sync.py`, `tools/release_audit.py` (novo), `tools/tests/test_release_audit.py` (novo), `docs/arquitetura-fabrica.md` (novo), `README.md` e `.workspace/devlogs/etapa4-agente4.md`. O `contexto_projeto.md` **não** foi editado diretamente (atualização via `devlog_sync.py` na consolidação); nenhum arquivo de outros agentes foi alterado.

#### 1. Evolução do `tools/devlog_sync.py` (multi-etapa)

- Novo parâmetro `--pattern` (padrão `etapa*-agente*.md`): traduz `*` do glob para captura numérica e extrai os números semanticamente do nome do arquivo, ordenando por `(etapa, agente)`; `--pattern` restritivo (ex.: `etapa4-agente*.md`) limita a descoberta.
- Retrocompatibilidade 100% comprovada: os testes 01–03 da Etapa 3 (consolidação única, idempotência e CLI) continuam idênticos byte a byte; marcadores `<!-- devlog-sync:etapa3-agente*.md -->` continuam válidos.
- Seção 1 do `contexto_projeto.md` agora distingue etapa única (formato histórico preservado) de multi-etapa ("Etapas 3 e 4 concluídas — Sync Multi-Agente (… Etapa 3: Agentes 1, 2 + Etapa 4: Agentes 1, 2, 10 …)").
- Resultado JSON reporta `pattern` e a chave `etapa` em `applied`/`skipped`/`discovered`.
- `tools/tests/test_devlog_sync.py`: 7 testes (3 de retrocompat + ordenação multi-etapa + idempotência multi-etapa + `--pattern` via API e CLI + CLI JSON/containment).

#### 2. Novo `tools/release_audit.py` (gate de release)

- Auditor final de prontidão em uma passada: `python tools/release_audit.py [--strict] [--json] [--root <raiz>]` (exit 0 aprovado / 1 reprovado / 2 erro de uso).
- **Tenants:** ≥ 4 válidos via `tenant_validator.load_and_validate_tenant(..., strict=False)` agregando erros (a API `validate_all_tenants` não existe; composição local, sem editar o `tenant_validator.py`).
- **Entregas:** para cada `tenants/*/campaigns/*.json`, confere `02-reels-shorts/deliveries/<tenant>/<slug>/` com `manifest.json`, `<slug>.srt`, `<slug>_narracao.txt` e `preview-storyboard.png`, validando SHA-256 e bytes contra o manifesto; o vídeo `<slug>.mp4` (não versionado) tem hash conferido quando presente e gera **aviso** quando ausente no disco.
- **Pacotes sociais:** `04-legendas/pacotes-publicacao/<tenant>/<slug>/checklist-publicacao.json` presente com `autoPublish: false` (ausência da chave também reprova).
- **Higiene Git:** `git ls-files "*.mp4" "*.wav"` vazio; regras `eol=lf` no `.gitattributes`; worktrees históricas `prova-campanha-conclusao` e `studio-package-verify2` preservadas (registrada sem diretório = falha; órfã ou ausente na estação = aviso).
- `--strict` promove avisos a reprovação: modo normal executável em qualquer estação/CI; `--strict` é o gate da estação de release (que possui os vídeos).
- `tools/tests/test_release_audit.py`: 11 testes — aprovação completa no repositório atual (4/4 tenants, 8 campanhas, 0 falhas), baseline de sandbox fiel (aprova normal, reprova `--strict`) e falhas simuladas (hash corrompido, storyboard ausente, diretório de entrega ausente, `autoPublish: true`, pacote ausente, `.mp4`/`.wav` rastreados, `.gitattributes` sem `eol=lf`, worktree órfã, worktree registrada sem diretório).
- Evidência CLI na worktree: `APROVADO` — Tenants 4/4, Campanhas 8 (0 entregas/pacotes reprovados), checks 11 ok / 10 aviso(s) / 0 falha(s); avisos esperados: vídeos não versionados ausentes no disco e worktrees históricas ausentes nesta estação.

#### 3. Documentação mestra

- **`docs/arquitetura-fabrica.md` (novo):** visão geral e invariante de entrega (tabela de artefatos com hashes), diagrama do pipeline, 10 seções de camadas (schemas, tenants com tabela dos 4, `tenant_validator`, `preset_runner`, `audio_tts`, `factory_cli`, `publish_pack`, `release_audit`, `devlog_sync` e módulos previstos), regras operacionais (vídeo sem áudio, publicação manual, portabilidade `<RAIZ>`, hashes estáveis `eol=lf`), fluxo operacional de ponta a ponta e seção de testes/CI.
- `derivative_formats`, `review_dashboard` e `campaign_calendar` estão **ausentes desta branch** (desenvolvimento paralelo dos Agentes 1–3) e foram documentados como "previstos", com instrução de atualização pós-integração — nada foi inventado sobre eles.
- **`README.md`:** nova seção executiva "Fábrica de vídeo multi-tenant (contratos → render → pacotes → release)" com tabela dos 4 tenants, comandos rápidos e checklist de operação manual; bullets `schemas/` e `tenants/` acrescentados à seção Estrutura. Conteúdo pré-existente preservado.
- Efeito colateral do `publish_pack` documentado: re-executar a ferramenta (ou sua suíte) em estação sem os `.mp4` regrava `sha256_disk_ok: false` nos checklists versionados; restaurar com `git checkout -- 04-legendas/`.

#### 4. Testes e evidências

- Suíte completa da fábrica nesta worktree: **53 testes em 7 módulos, `OK` em 142,5 s** (`test_tenant_contracts`, `test_preset_runner`, `test_factory_cli`, `test_audio_tts`, `test_publish_pack`, `test_devlog_sync`, `test_release_audit`), incluindo renders reais do `preset_runner`.
- A execução da suíte alterou 8 `checklist-publicacao.json` (flip `sha256_disk_ok: true → false`, efeito colateral conhecido do `test_publish_pack` em estação sem vídeos); diff auditado (apenas esse flip) e restaurado com `git checkout -- 04-legendas/` antes do commit.
- Ajustes de plataforma Windows nos testes do `release_audit`: caminhos curtos de sandbox (worktree profunda + `WinError 3` acima de ~248 caracteres) e `--no-checkout` no `git worktree add` do teste de worktree registrada (o checkout excederia `MAX_PATH` no arquivo mais profundo).
- Textos pt-BR dos documentos verificados por contagem exata de strings (título com acentos, "Marca Salão", "Estúdio Flow", links), não por inspeção visual.

#### 5. Pendências para a consolidação

- Acrescentar `tools/tests/test_release_audit.py` à etapa "Validar contratos multi-tenant e suites da fabrica" do CI (`.github/workflows/local-render-validation.yml`, linha 94) — workflow fora do território deste agente.
- Ao integrar `derivative_formats`, `review_dashboard` e `campaign_calendar` (Agentes 1–3), atualizar `docs/arquitetura-fabrica.md` (diagrama da Seção 1 e Seção 2.10).
- Rodar `python tools/devlog_sync.py` na consolidação para aplicar este devlog ao `contexto_projeto.md` (não executado aqui: aplicaria apenas a etapa 4 nesta worktree e o `contexto_projeto.md` é compartilhado entre agentes).
- Gate final de release: `python tools/release_audit.py --strict --json` na estação que possui os `.mp4` renderizados.
- Este devlog vive em `.workspace/` (local da estação, fora do Git por desenho): a consolidação precisa rodar nesta estação ou transferir o conteúdo antes de sincronizar.

---

## Continuação — Etapa 4, Agente 4 (gate de release 7 domínios + CI + docs), 2026-11-19

Base: main `f7298dc`. Branch `codex/etapa4-agente4-release-gate-docs` re-apontada de `01d6c22` para a main com `git branch -f` (sem perda: o conteúdo da fase 1 já estava consolidado como `bad5063`); worktree isolada criada em `.workspace/worktrees/etapa4-agente4`. Nenhuma worktree histórica ou de outro agente foi tocada.

### Tarefa 1 — devlog_sync multi-etapa (verificação)

Já consolidado na main (fase 1 absorvida). `python -m unittest tools/tests/test_devlog_sync.py` → 7 testes OK: ordenação numérica por `(etapa, agente)`, atualização da linha "Fase atual" na Seção 1, idempotência byte a byte, filtro `--pattern`, `PATH_OUTSIDE_ROOT`. `contexto_projeto.md` não foi editado diretamente.

### Tarefa 2/5 — release_audit em 7 domínios (TDD RED→GREEN)

`tools/release_audit.py` reescrito: relatório `schemaVersion: 2` com `domains[]` (ids e nomes na ordem do briefing) e `summary`; problemas tipados `{severity: error|warning, code, message}`; API pública `run_release_audit(root=".", strict=False)` (renomeada de `run_audit`, sem alias — nenhum outro chamador no repositório, confirmado por grep); CLI `[--strict] [--json] [--report-out <arquivo>] [--root <raiz>]`; exit 0/1/2 inalterados.

Domínios: 1 `contratos_tenants`, 2 `entregas_video`, 3 `pacotes_sociais`, 4 `derivados_multiformato`, 5 `calendario_utm`, 6 `portal_revisao`, 7 `higiene_git`.

Severidades: mídia local da estação ausente (`<slug>.mp4` da entrega e derivados em `.workspace/archives/`) NÃO gera problema — os avisos antigos `VIDEO_NAO_VERSIONADO_AUSENTE_NO_DISCO` e `WORKTREE_AUSENTE_NA_ESTACAO` foram removidos; presente em disco, o SHA-256 é conferido. Isso torna o `--strict` executável em checkout novo/CI. Artefatos de consolidação ausentes (`derivatives.json`, `calendario-editorial.*`, `matriz-utm-consolidada.csv`, arquivos do portal) = warning; defeitos de conteúdo (hash divergente, `autoPublish: true`, `guardrailsAudited: false`, caminho absoluto vazado, política de áudio violada, declaração de derivado incompleta, mídia rastreada, `.gitattributes` sem cobertura `eol=lf`, worktree registrada sem diretório) = error sempre. `domain.ok` = sem erros; `ok` global = sem erros e, no `--strict`, sem avisos.

Política de áudio simétrica, validada contra os 8 manifestos reais: `allowAudioTrack: false` ⇒ `ffprobe.audioStreams == 0` (`-an`); `true` ⇒ `>= 1` (aac). 5 campanhas saas-demo com 0 stream; 3 multitrack com 1 stream aac.

`.gitattributes` conferido por extensão: cada uma de `.json`/`.srt`/`.md`/`.html` precisa de ao menos uma regra `eol=lf` (`GITATTRIBUTES_EXT_SEM_EOL_LF`). Varredura de vazamento no portal: regex `(?<![A-Za-z0-9])[A-Za-z]:[/\\]|/users/` (o lookbehind evita falso positivo em `https://`), aplicada só a `index.html` e `portal-data.json`.

Testes: `tools/tests/test_release_audit.py` reescrito com 22 testes. RED observado (21 erros): `AttributeError: module 'release_audit' has no attribute 'run_release_audit'` e `SystemExit: 2` do argparse sem `--report-out`. GREEN: 22/22 OK. Bug adicional encontrado e corrigido por TDD (`test_22_cli_json_stdout_is_utf8`, RED com `UnicodeDecodeError: 0xed`): a saída do CLI no Windows saía em cp1252 por causa dos nomes de domínio acentuados, corrompendo o relatório para qualquer consumidor UTF-8 (inclusive o runner `windows-latest`); corrigido com `sys.stdout.reconfigure(encoding="utf-8")` sob guarda `getattr` (os testes capturam via `StringIO`, que não tem `reconfigure`). `--report-out` já gravava UTF-8 explícito.

Evidência do estado real desta branch (worktree sobre `f7298dc`):

- `release_audit --json` → exit 0, `ok: true`, 6 domínios ok, 1 aviso `MATRIZ_UTM_AUSENTE: 04-legendas/matriz-utm-consolidada.csv`, 0 erros, tenants 4/4 válidos, 8 campanhas, 0 entregas/pacotes/derivados reprovados.
- `release_audit --strict --json` → exit 1, bloqueado apenas por esse aviso (gate honesto).

### Tarefa 3 — CI

`.github/workflows/local-render-validation.yml`: 4 paths novos nos gatilhos `push` e `pull_request` (`05-review-portal/**`, `04-legendas/calendario-editorial.*`, `04-legendas/matriz-utm-consolidada.csv`, `docs/**`); step renomeado para "(Etapas 2, 3 e 4)" com a suíte consolidada de 16 módulos (todos confirmados presentes em `tools/tests/`) + `python tools/release_audit.py --strict --json`. YAML validado por parse; paths de `push` e `pull_request` idênticos.

PENDÊNCIA PARA O TITULAR: com `--strict` no CI, o gate fica vermelho até a `matriz-utm-consolidada.csv` do Agente 3 chegar na main (o `campaign_calendar` atual grava a matriz dentro do `.md`, não o CSV separado). Remover `--strict` daquela linha é a alternativa de uma palavra, se preferir CI verde antes dessa consolidação.

### Tarefa 4 — Documentação

`docs/arquitetura-fabrica.md`: tabela de invariantes com `derivatives.json`; diagrama ASCII ponta a ponta (schemas/tenants → tenant_validator → preset_runner (+audio_tts) → derivative_formats → publish_pack → campaign_calendar → review_dashboard → release_audit; devlog_sync transversal); §2.8 reescrita com a tabela dos 7 domínios, severidades, `--report-out` e a regra de mídia local; §2.10/2.11/2.12 novas (derivative_formats, campaign_calendar com a pendência do CSV, review_dashboard); §4 com 10 passos; §5 com a suíte de 16 módulos e a dependência de consolidação.

`README.md`: `05-review-portal/` na estrutura; status (4 tenants, 8 campanhas, 16 módulos); declaração explícita de que nenhuma ferramenta publica, agenda ou cria rascunho; referência rápida de todos os CLIs (incluindo `derivative_formats`, `campaign_calendar`, `review_dashboard --build/--serve`, `release_audit --report-out`); protocolo de revisão humana e publicação manual.

### Handoff de armazenamento

Raiz usada: `D:/Mega/Marketing/marcasalao-marketing` (worktree `.workspace/worktrees/etapa4-agente4`). Versionados e alterados: `tools/release_audit.py`, `tools/tests/test_release_audit.py`, `.github/workflows/local-render-validation.yml`, `docs/arquitetura-fabrica.md`, `README.md`. Somente em `.workspace/` (não versionado): este devlog, `.workspace/tmp/suite-16.log`, `.workspace/tmp/audit-*.json`, `.workspace/tmp/devlog-contin.md` e `.workspace/tmp/commit-msg.txt` (auxiliares desta sessão, removíveis), sandboxes `.workspace/tmp/rel-audit` (removidos pelo tearDown). Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/Mega/Marketing/marcasalao-marketing`.
- Evidência da suíte consolidada de 16 módulos (rodada definitiva, com a ponte TypeScript compilada na worktree — Node v22.23.2, npm 10.9.8, npm ci + npm run build exit 0, package-lock.json intacto): Ran 215 tests in 1407.353s — OK, 0 falhas, 0 erros, 0 skips, exit 0. Rodada anterior, sem o build da platform na worktree: Ran 165 tests, 33 skips e 1 falha em test_render_local.TimeoutAndInspectionTest.test_render_timeout_preserves_delivery (2 != 1) — causa ambiental (platform/dist ausente faz render_local.main sair com código 2 antes do caminho de timeout); revalidada isoladamente OK após o build. O CI compila a ponte antes da suíte, logo reproduz a rodada definitiva.
- Evidência do release_audit nesta branch (estado commitado 6c58cc9): modo normal ok=True | dominios ok=6 warn=1 fail=0 | erros=0 avisos=1 | tenants=4/4 | campanhas=8 (entregas=0 pacotes=0 derivados=0), exit 0; --strict exit 1, bloqueado apenas por: [warning] MATRIZ_UTM_AUSENTE: 04-legendas/matriz-utm-consolidada.csv.

## 1. Gerador modular de áudio — `tools/audio_tts.py`

Módulo CLI + programático, sem APIs pagas. Resolve FFmpeg por
`build_video.get_ffmpeg()` (PATH ou `.workspace/tools/ffmpeg`).

**Trava de segurança (sempre, antes de render):**
`tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)`
e recusa imediata com `AudioTtsError("AUDIO_NAO_PERMITIDO")` quando
`guardrails.audioPolicy.allowAudioTrack == false` (marca-salao, meu-salao).

**Modos:**
- `ambient-bed`: cama sonora sintetizada via FFmpeg `lavfi` (`aevalsrc` com acorde
  A maior+9a), `tremolo` (pulso suave 1.6 Hz / 0.22), `afade` in/out e
  `loudnorm=I=-22:TP=-2:LRA=11` (aplicado quando duração ≥ 3 s). Saída
  `pcm_s16le`, 44100 Hz, stereo. Medido: **-21.8 LUFS** (meta -22).
- `narration-bed`: tenta TTS local (1º `pyttsx3`, 2º Windows SAPI via PowerShell
  `System.Speech`), mistura sobre a cama (`amix duration=first`, voz realçada) e
  normaliza em -22 LUFS. **Fallback automático e seguro** para `ambient-bed`
  (flag `ttsEngine="fallback-ambient-bed"`) se nenhum motor existir. Neste ambiente
  o motor **windows-sapi** estava disponível e foi usado.

**API:** `generate_audio(tenant_id, output_path, duration=30.0, mode=..., root=...,
text=None, sample_rate=44100, channels=2, prefer_engine=None) -> dict`
(metadados: path, sha256, bytes, duration, sampleRate, channels, codec, ttsEngine...).

**CLI:**
```
python tools/audio_tts.py --tenant multitrack-hub --output <wav> --duration 30 --mode ambient-bed
python tools/audio_tts.py --tenant multitrack-hub --output <wav> --duration 30 --mode narration-bed --text "..."
```

## 2. Duas campanhas Shorts (`multitrack-hub`, preset `shorts-completo`)

Ambas 1080×1920 @ 30 fps, 30.0 s, 5 cenas, dentro dos guardrails (sem
whatsapp/telefone comercial/checkout; sem claims proibidos).

- `tenants/multitrack-hub/campaigns/camp-shorts-rateios-002.json`
  (`SHORTS-RATEIOS-MULTITRACK-002`) — foco em **organização de rateios**
  (cotas, faixas inclusas, vagas). Rotas `/` e `/rateios`.
- `tenants/multitrack-hub/campaigns/camp-shorts-stems-workflow-003.json`
  (`SHORTS-STEMS-WORKFLOW-MULTITRACK-003`) — foco em **organização de stems
  Click/Guide/Banda** e ordem de trabalho. Rotas `/`.

README de campanhas atualizado com a tabela das 3 campanhas e exemplo de render
com `--audio`.

## 3. Render com áudio real + prova por ffprobe

Trilhas geradas em `.workspace/tmp/audio-mth/`:
- `bed-rateios-002-30s.wav` (ambient-bed)
- `narracao-stems-workflow-003-30s.wav` (narration-bed / windows-sapi)

Renderização via `tools/preset_runner.py` (motor `run_preset_pipeline`,
`--audio`/`audio_path`), saída em
`02-reels-shorts/deliveries/multitrack-hub/<slug>/` + cópia `.mp4` em
`.workspace/archives/<slug>/`:

| Campanha | Vídeo | Áudio | Duração | source |
| --- | --- | --- | --- | --- |
| camp-shorts-rateios-002 | h264 1080×1920 30/1 yuv420p | **aac 44100 Hz 2 ch** | 30.000 s | external |
| camp-shorts-stems-workflow-003 | h264 1080×1920 30/1 yuv420p | **aac 44100 Hz 2 ch** | 30.000 s | external |

`ffprobe` confirmou `nb_streams=2` (1 vídeo + 1 áudio AAC 44100 Hz stereo) em
ambos. Manifestos registram `guardrails.audioPolicy.allowAudioTrack=true`,
`audio.source=external`, `audioStreams=1`.

## 4. Testes — `tools/tests/test_audio_tts.py`

9 testes (unittest), todos aprovados:
1. ambient-bed: WAV 30.0 s / 44100 Hz / stereo / pcm_s16le exato (probe + disco).
2. narration-bed: saída válida (motor TTS ou fallback) com duração exata.
3. bloqueio `marca-salao` (AUDIO_NAO_PERMITIDO, sem arquivo).
4. bloqueio `meu-salao` (AUDIO_NAO_PERMITIDO, sem arquivo).
5. duração parametrizada respeitada (12.5 s).
6. rejeição de saída fora da raiz (OUTPUT_FORA_DA_RAIZ).
7. rejeição de modo inválido (MODO_INVALIDO).
8. integração: WAV alimenta `preset_runner` e vira 1 stream AAC 44100/2ch.
9. retrocompatibilidade: 3 tenants continuam carregáveis.

**Suíte consolidada (10 módulos):** `Ran 74 tests in 103.532s — OK (skipped=1)`,
exit code 0. O skip é pré-existente (não pertence a `test_audio_tts`, que rodou
9/9). Log bruto: `.workspace/devlogs/suite-agente2.log`.

## Observação (fora do meu território — não corrigido)

`tools/preset_runner.py` (linhas 1002-1005) imprime o resumo de sucesso via
`manifest['artifacts']['video']['width'|'height']`, chaves inexistentes (largura/
altura vivem em `manifest['format']`). Isso faz o **CLI** encerrar com `KeyError`
e código 1 **após** a renderização já ter sido promovida/arquivada com sucesso.
Os artefatos ficam íntegros; afeta apenas a linha de status do CLI. Como
`preset_runner.py` é território de outro agente (Etapa 2), a renderização do
`stems-workflow-003` foi feita pela API programática `run_preset_pipeline`
(entrada documentada), e o `rateios-002` pelo CLI (artefatos íntegros apesar do
exit 1). Correção do print sugerida para o dono do arquivo: usar
`manifest['format']['width'|'height']`.

## Handoff / limpeza

- Worktree criada: `.workspace/worktrees/etapa3-agente2` (mantida até o merge).
- Arquivos permanentes versionados (commit):
  `tools/audio_tts.py`, `tools/tests/test_audio_tts.py`,
  `tenants/multitrack-hub/campaigns/camp-shorts-rateios-002.json`,
  `tenants/multitrack-hub/campaigns/camp-shorts-stems-workflow-003.json`,
  `tenants/multitrack-hub/campaigns/README.md` (modificado),
  `02-reels-shorts/deliveries/multitrack-hub/camp-shorts-rateios-002/*` (srt,
  narration, manifest, storyboard), `.../camp-shorts-stems-workflow-003/*`.
- Mantidos só em `.workspace/` (não versionados, gitignored): WAVs em
  `.workspace/tmp/audio-mth/`, MP4 em `.workspace/archives/<slug>/` e
  `.workspace/devlogs/` (este log + `suite-agente2.log`).
- Ferramentas portáteis: FFmpeg/FFprobe do checkout principal
  (`<RAIZ>/.workspace/tools/ffmpeg`), usados via PATH do processo (não alterado
  permanentemente).
- Temporários de staging do preset_runner e áudio-tts são removidos
  automaticamente; `__pycache__` não é adicionado ao Git.

**Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.**

### Sessão 2026-11-18 — Etapa 3 (Agente 3): Gerador de Pacotes de Publicação Sociais e UTMs (`tools/publish_pack.py`)
<!-- devlog-sync:etapa3-agente3.md -->

- **Branch / Commit:** `codex/etapa3-agente3-publish-utm` (`0383006`, integrada em `main` via `a77efe5`).
- **Papel:** Engenheiro de Distribuição & Analytics (Agente 3 de 4, paralelo).

#### Entregáveis criados e atualizados

1. **`tools/publish_pack.py`:** gerador CLI (`--all`, `--tenant <id> --slug <slug>`, `--json`) e programático que lê `manifest.json`, `<slug>.srt` e `<slug>_narracao.txt` de `02-reels-shorts/deliveries/<tenantId>/<slug>/` junto com `brand-kit.json` e `guardrails.json`, gera pacotes por rede social em `04-legendas/pacotes-publicacao/<tenantId>/<slug>/` (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`, `checklist-publicacao.json`), aplica URLs com parâmetros UTM por canal (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`), audita obrigatoriamente todas as cópias contra `forbiddenClaims` e `forbiddenUiElements` antes de gravar e registra `autoPublish: false` + hashes SHA-256.
2. **`tools/tests/test_publish_pack.py`:** 7 testes unitários cobrindo geração por tenant/campanha, hashes e tamanhos em disco, formatação das URLs UTM por canal, CTA de Instagram (`link na bio`), bloqueio preventivo de frases proibidas e integridade de `checklist-publicacao.json`.
3. **`docs/rastreio-utm.md`:** documentação atualizada com os parâmetros e convenções do gerador de pacotes sociais.
4. **Pacotes iniciais em `04-legendas/pacotes-publicacao/`:** gerados inicialmente para os 3 tenants base (`marca-salao`, `meu-salao`, `multitrack-hub`) e expandidos na consolidação pós-merge para todas as 8 campanhas dos 4 tenants.

### Sessão 2026-11-18 — Etapa 3 (Agente 4): Onboarding do 4º Nicho (`estudio-flow`) e Consolidador de Devlogs (`tools/devlog_sync.py`)
<!-- devlog-sync:etapa3-agente4.md -->

- **Branch de trabalho:** `codex/etapa3-agente4-novo-nicho-sync` (baseada em `main` `ccea4321871d9551484b8ed125b280a84857f1c9`).
- **Worktree isolada:** `D:/MEGA/Marketing/marcasalao-marketing/.workspace/worktrees/etapa3-agente4`.
- **Território respeitado:** alterações restritas a `tenants/estudio-flow/**`, `02-reels-shorts/deliveries/estudio-flow/**`, `tools/devlog_sync.py`, `tools/tests/test_devlog_sync.py`, `docs/guia-novo-nicho.md` e `.workspace/devlogs/etapa3-agente4.md`; `contexto_projeto.md` e `02-reels-shorts/deliveries/factory-report.json` não foram alterados.

#### 1. Onboarding do 4º Nicho (`tenants/estudio-flow/`)

- `tenants/estudio-flow/brand-kit.json`: `tenantId: "estudio-flow"`, `brandName: "Estúdio Flow"`, `displayTitle: "ESTUDIO FLOW"`, `monogram: "EF"`, `domain: "estudioflow.com.br"`, paleta terracota (`#C86D51`), sálvia (`#6B8E78`) e areia (`#E6D5B8`), `headerOverlay.label: "ESTUDIO FLOW"`, `defaultPreset: "saas-demo"`, `utmDefaults` (`instagram` / `reels` / `ef`).
- `tenants/estudio-flow/guardrails.json`: bloqueia promessas de cura clínica, tratamento médico, emagrecimento garantido, resultado imediato, mensagens automáticas WhatsApp/SMS/lembretes 24h e redução/zero faltas; separa `/aulas/[studioId]` (`public-booking`) e `/gestor/turmas` (`manager-agenda`); impõe `allowAudioTrack: false` (`-an`).
- `tenants/estudio-flow/fixtures/fixture-editorial-estudio-flow.json`: 4 instrutores fictícios (`inst-ef-001..004`), 5 modalidades com duração, aula avulsa e mensalidade em BRL (`mod-ef-001..005`), grade de horários `turma-ef-001..005` e chaves de compatibilidade (`profissionais`, `servicos`, `agenda.atendimentos`, `booking.rota`).
- `tenants/estudio-flow/campaigns/camp-saas-demo-estudio-flow-001.json`: 6 cenas (`30.0s`), `Beatriz Alencar`, demonstrando reserva de aula experimental em `/aulas/estudio-flow-jardins` e visualização/status manual em `/gestor/turmas`.

#### 2. Renderização e Auditoria (`camp-saas-demo-estudio-flow-001`)

- **Validação de contrato:** `python tools/tenant_validator.py --tenant estudio-flow --json` → `"ok": true`, `"errors": []`.
- **Descoberta global (4 tenants):** `python tools/tenant_validator.py --all --json` → `"ok": true` (`estudio-flow`, `marca-salao`, `meu-salao`, `multitrack-hub`); `python tools/factory_cli.py list --json` → `totalTenants: 4`, `totalCampaigns: 4`.
- **Render e `ffprobe`:** `1080x1920`, `30/1` fps, `h264`, `yuv420p`, `30.000000s`, `nb_streams: 1` (**0 streams de áudio / `-an`**), `438290` bytes.
- **Hashes SHA-256 observados (`02-reels-shorts/deliveries/estudio-flow/camp-saas-demo-estudio-flow-001/manifest.json`):**
  - Vídeo (`.workspace/archives/camp-saas-demo-estudio-flow-001/camp-saas-demo-estudio-flow-001.mp4`): `438290` B, `b21504d50e63d044ee71ed0a0f1d58f365c49769ceeca4ae54a6f60e0a835a19`
  - SRT: `572` B, `b2c4024267176f4da912a99396b0a74703fccf49bbfeeb75c4d423e1f2645a4f`
  - Narração: `923` B, `476a19bac49333ab030d02975f57c612e75b234f6ee8d157ccc1801aa7f71760`
  - Storyboard: `591280` B, `d50ca37f53a2445a224d68c9492bdd5ec4a128686469245dc2fcd19603ea828a`

#### 3. Consolidador `tools/devlog_sync.py`, Guia e Testes

- **`tools/devlog_sync.py`:** descobre `etapa3-agente-*.md` / `etapa3-agente*.md` em ordem numérica (`re` pelo índice do agente), garante idempotência por marcador `<!-- devlog-sync:<arquivo> -->` e título `### ...`, atualiza data/status na Seção 1 e anexa novas sessões ao final da Seção 7 com LF e validação estrita de contenção de caminho.
- **`docs/guia-novo-nicho.md`:** refinado com mapeamento de compatibilidade (`profissionais`/`servicos`/`agenda.atendimentos`/`booking.rota`), flag `--report` para render em worktrees paralelas, referência ao `tenants/estudio-flow/` e nota sobre testes globais com contagem fixa `3`.
- **Suíte executada na worktree (`test_devlog_sync.py` 4 + `test_preset_runner.py` 7 + `test_ns002_pilot.py` 5):** **16/16 aprovados em `55.759s` (`OK`)**.
- **Nota de integração pós-merge:** na execução exploratória de `test_tenant_contracts.py`, os testes `test_01..test_06` passaram (`6/7`) e `test_07_cli_exit_codes` retornou `AssertionError: 4 != 3` por esperar contagem fixa de `3` tenants (idem `test_factory_cli.py::test_01`/`test_03` com `totalTenants == 3`). Como esses testes estão fora do território do Agente 4, a atualização das asserções (`>= 3` ou `4`) e `factory_cli.py render --all` deve ocorrer na consolidação da Etapa 3.

### Sessão 2026-11-18 — Consolidação Pós-Merge da Etapa 3 (4 Tenants, 8 Campanhas e Push Remoto)

- **Branch:** `main` (consolidando as entregas dos 4 agentes paralelos da Etapa 3: `ad95adc`, `d55b291`, `a77efe5`, `d70dd93`).
- **Tenants e campanhas consolidados:** **4 tenants** e **8 campanhas** em `02-reels-shorts/deliveries/factory-report.json` e `04-legendas/pacotes-publicacao/`:
  1. `estudio-flow`: `camp-saas-demo-estudio-flow-001` (`-an`, 0 áudio)
  2. `marca-salao`: `camp-saas-demo-marca-salao-001`, `camp-saas-demo-ns001-agenda-001` (`-an`, 0 áudio)
  3. `meu-salao`: `camp-saas-demo-meu-salao-001`, `camp-saas-demo-meu-salao-002` (`-an`, 0 áudio)
  4. `multitrack-hub`: `camp-shorts-completo-multitrack-001`, `camp-shorts-rateios-002`, `camp-shorts-stems-workflow-003` (`aac`, 1 áudio)
- **Ajustes de integração e CI aplicados na `main`:**
  - `.workspace/devlogs/etapa3-agente3.md` criado e todos os 4 devlogs consolidados em ordem (`1 -> 2 -> 3 -> 4`) via `tools/devlog_sync.py`.
  - `.gitattributes` estendido com `text eol=lf` para `04-legendas/pacotes-publicacao/**/*.json` e `**/*.md`.
  - `tools/tests/test_tenant_contracts.py`, `tools/tests/test_factory_cli.py` e `tools/tests/test_publish_pack.py` atualizados para 4 tenants / 8 campanhas.
  - `.github/workflows/local-render-validation.yml` atualizado com filtro `04-legendas/pacotes-publicacao/**` e execução explícita de `test_audio_tts.py`, `test_publish_pack.py` e `test_devlog_sync.py`.
- **Validações e suíte completa na `main`:**
  - `python tools/tenant_validator.py --all --json` → `ok: true` (4 tenants).
  - `python tools/factory_cli.py list --json` → `ok: true`, `totalTenants: 4`, `totalCampaigns: 8`.
  - `python tools/publish_pack.py --all --json` → pacotes e UTMs gerados/auditados para as 8 campanhas (`autoPublish: false`).
  - Suíte consolidada completa (**12 módulos**): **85/85 testes aprovados em `107.194s` (`OK`)** (`test_tenant_contracts`, `test_preset_runner`, `test_factory_cli`, `test_audio_tts`, `test_publish_pack`, `test_devlog_sync`, `test_ns002_pilot`, `test_srt_validate`, `test_build_video`, `test_r002_pilot`, `test_delivery_verify`, `test_campaign_proof`).
- **Worktrees preservadas:** `.workspace/worktrees/etapa3-agente1`, `.workspace/worktrees/etapa3-agente2`, `.workspace/worktrees/etapa3-agente4`, `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2` mantidas sem alterações.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

---

### Sessão 2026-11-18 — Correção Pós-Consolidação da Etapa 3 (KeyError no CLI, Teste de Regressão e Limpeza de Worktrees)

- **Executor:** Engenheiro de Software Sênior (manutenção corretiva na `main`).
- **Branch:** `main` (HEAD `af1e15f`, consolidada da Etapa 3), sem push remoto.
- **Escopo:** correções técnicas pendentes após a consolidação da Etapa 3, restritas a `tools/preset_runner.py`, `tools/tests/test_preset_runner.py` e `contexto_projeto.md`; worktrees históricas `prova-campanha-conclusao` e `studio-package-verify2` preservadas intactas.

#### 1. Correção do `KeyError` no resumo do CLI (`tools/preset_runner.py`)

- **Bug:** o resumo final do CLI (`main()`, linhas ~1002-1005) lia `manifest['artifacts']['video']['width'|'height'|'fps'|'audioStreams']`, chaves inexistentes (largura/altura/fps vivem em `manifest['format']`; a contagem de áudio vive em `manifest['artifacts']['video']['ffprobe']['audioStreams']`). O pipeline concluía e promovia/arquivava os artefatos, mas o CLI encerrava com `KeyError` e código `1`.
- **Correção:** o resumo passa a ler `manifest['format']['width'|'height'|'fps']` e a contagem de áudio de `manifest['artifacts']['video']['ffprobe']['audioStreams']`, com fallback seguro via `.get(...)` para `manifest['audio']['audioStream']`. O CLI encerra com código `0` após concluir o pipeline.
- **Verificação:** `python tools/preset_runner.py --tenant multitrack-hub --config tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json --output-dir <tmp>` → `Preset 'shorts-completo' renderizado ... (1080x1920 @30fps, 1 stream(s) de audio)`, `RC=0`, sem `KeyError`.

#### 2. Teste de regressão do CLI (`tools/tests/test_preset_runner.py`)

- **`test_08_cli_exits_zero_after_pipeline`:** executa o CLI como subprocesso (`sys.executable tools/preset_runner.py ... --output-dir <tmp>`) e valida `returncode == 0`, ausência de `KeyError`/`Traceback` em `stderr` e `manifest.json` íntegro (`format.width=1080`, `height=1920`, `fps=30`, `artifacts.video.ffprobe.audioStreams=1`). Passou isoladamente (`Ran 1 test ... OK`).

#### 3. Limpeza das worktrees temporárias da Etapa 3

- Removidas via `git worktree remove` + `git worktree prune` as worktrees já integradas: `.workspace/worktrees/etapa3-agente1`, `.workspace/worktrees/etapa3-agente2` e `.workspace/worktrees/etapa3-agente4` (a `etapa3-agente3` não estava registrada).
- **Preservadas intactas:** `.workspace/worktrees/prova-campanha-conclusao` e `.workspace/worktrees/studio-package-verify2`.
- **Handoff:** `git worktree list` passou a listar apenas `main` + as duas worktrees históricas; `git ls-files "*.mp4"` e `git ls-files "*.wav"` permanecem vazios; nenhum `git clean` destrutivo foi executado (`.workspace/archives/` e `.workspace/tools/` preservados). Restou apenas o diretório **vazio** e **desregistrado** `.workspace/worktrees/etapa3-agente1` (gitignored), preso como CWD por um shell interativo do Kilo; pode ser apagado após fechar esse terminal.

#### 4. Validação completa da fábrica e suíte de testes (na `main`)

- `python tools/tenant_validator.py --all --json` → `ok: true` (4 tenants: `estudio-flow`, `marca-salao`, `meu-salao`, `multitrack-hub`; `errors: []`).
- `python tools/factory_cli.py list --json` → `ok: true`, `totalTenants: 4`, `totalCampaigns: 8`.
- `python tools/publish_pack.py --all --json` → 8 pacotes auditados, todos `autoPublish: false`, `guardrailsAudited: true`, `guardrailStatus` `srt/narration: ok`, `sha256_disk_ok: true` (0 violações).
- Suíte funcional consolidada (**12 módulos**, incluindo o novo `test_08`): **86/86 testes aprovados em `111.456s` (`OK`, exit 0)** (`test_tenant_contracts`, `test_preset_runner`, `test_factory_cli`, `test_ns002_pilot`, `test_srt_validate`, `test_build_video`, `test_r002_pilot`, `test_delivery_verify`, `test_campaign_proof`, `test_audio_tts`, `test_publish_pack`, `test_devlog_sync`).
- **Nota:** o `python -m unittest discover -s tools/tests` (usado no CI com `REQUIRE_RENDER=1`, após build da ponte TypeScript) inclui ainda as suítes de estúdio/e2e (`test_studio_*`, `test_recording_cuts`, `test_multi_format`, `test_video_studio`, `test_campaign_studio_e2e`, `test_studio_astryx_frontend`), mais pesadas (servidor HTTP + render por teste); a suíte funcional de 86 é o gate consolidado "Etapas 2 e 3" do workflow `local-render-validation.yml`.
- **Frase de encerramento:** Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de `D:/MEGA/Marketing/marcasalao-marketing`.

### 21/11/2026 — CI de render da Etapa 6

O GitHub Actions aprovou o commit `9a800d1` no Windows e no Ubuntu, com a suíte Python de render obrigatório, a prova de `TextOverlayPlan` (`--text-overlays`) e a prova HTTP de clipes na porta `8808`. Consulte o [run 44904714554](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/44904714554).

O ajuste final tornou as fixtures de FFmpeg e FFprobe do `workspace_doctor` portáveis entre Windows e Ubuntu. As entregas versionadas permaneceram intactas.

### 21/11/2026 — Validação pós-merge da Etapa 7 (Release Manager, estação Windows)

**Base validada:** `main` @ `227e939`, com 3 commits locais ainda não enviados ao remoto (`899d36b` E2E da fábrica no CI + pacote documental das decisões do titular; `19e74c0` cruzamento bidirecional manifestos/archives, snapshot local e gate de mídia; `227e939` 3 campanhas novas e calendário de 7 semanas). Portfólio vigente: **5 tenants / 14 campanhas**. Nenhum devlog da Etapa 7 existe em `.workspace/devlogs/` (nada para o `devlog_sync` sincronizar). A árvore contém trabalho não commitado de outra sessão (`platform/src/tenant-policy-*`, `platform/src/validate-*`, `tools/preset_runner.py`, `tools/static_cards.py`, `tools/video_studio.py` e testes correspondentes) — preservado, não tocado.

**Script de validação recebido:** executado tal como enviado, a partir de `.workspace/tmp/etapa7/validate_etapa7.py`. Resultado do script: FALHOU com 5 pendências, sendo 3 incompatibilidades do script com as CLIs reais e 2 reais:

- `tools/tenant_validator.py` sem argumentos encerra com código 2 — exige `--tenant <id>` ou `--all`.
- `tools/factory_cli.py handoff --dry-run` não existe — as opções são `--date`, `--all-approved`, `--include-pending`, `--approvals-file`, `--output-dir`.
- `pytest` não está instalado e o repositório usa `unittest`; `tests/e2e` documenta `python -m unittest discover -s tests/e2e -v`.
- `ARCHIVE_HASH_DIVERGENTE` em masters locais de `.workspace/archives/` (não versionados).

**Correção aplicada nos masters locais:** restaurados a partir dos `.mp4` das entregas, cujos hashes conferem com os manifestos — `camp-saas-demo-marca-salao-001`, `camp-saas-demo-meu-salao-001` e `camp-shorts-completo-multitrack-001`. Causa conhecida: os testes de render com áudio do `preset_runner` sobrescrevem os masters compartilhados em `.workspace/archives/`; isso se repete a cada execução da suíte. Após a restauração, `workspace_doctor` e `release_audit` voltam a verde e os dois testes de pipeline do `factory_cli` passam.

**Expectativas de teste atualizadas para o novo portfólio (14 campanhas / calendário de 7 semanas):** `test_campaign_calendar` (`WEEKS` 5→7, 44→56 slots, ondas 33/11→42/14, 56 URLs, ids `slot-001..056`, 57 linhas no CSV, distribuição semanal `{1:12, 2:12, 3:12, 4:6, 5:6, 6:6, 7:2}`, formatos 42/7/7, cabeçalhos de Semana 5 e nova Semana 7, CLI `--weeks 7`, 14 campanhas esperadas), `test_review_dashboard` (11→14 e 3 campanhas novas), `test_static_cards` (11→14 e mapa por tenant), `test_editorial_qa` (11→14; filtro `meu-salao` 2→3) e `test_approval_cli` (11→14).

**Gates executados com as flags corretas:**

- `platform: npm run build` e `npm test` → OK (1003 testes, 0 falhas, 7 skips).
- `python tools/tenant_validator.py --all --json` → 5/5 tenants.
- `python tools/editorial_qa.py` → 14 campanhas, 7 lentes, 0 erros e 0 avisos.
- `python tools/factory_cli.py handoff --json` → ok (0 aprovadas, nenhum empacotamento automático).
- `python -m unittest discover -s tests/e2e -v` → 4 testes OK.
- `python tools/workspace_doctor.py --check --json` → ok, 0 erros.
- `python tools/release_audit.py --strict --json` → 7/7 domínios OK.
- 5 módulos de teste corrigidos, isolados → 89 testes OK.

**Suíte canônica do CI (25 módulos, `unittest`):**

- Primeira execução: 366 testes, **11 falhas + 1 erro** — expectativas presas a 11 campanhas e calendário de 5 semanas, mais os masters corrompidos em `.workspace/archives/`.
- Após as correções acima: **380 testes, 2 falhas** (`test_05_pipeline_filtered_skip_render_reports_each_stage` e `test_06_pipeline_all_skip_render_consolidates_factory`). As duas falham somente porque os testes de render com áudio sobrescrevem os masters compartilhados durante a própria execução; depois de restaurar os 3 masters a partir das entregas, os 2 testes passam (`OK`) e `workspace_doctor --check` e `release_audit --strict` voltam a 7/7.
- **Pendência registrada para a próxima etapa:** `preset_runner`/testes de render não devem escrever masters em `.workspace/archives/<slug>/` durante a suíte — ou precisam de um diretório de archives isolado por execução, para que o gate de mídia não dependa de restauração manual.

**Nada foi commitado nesta sessão de validação**: `contexto_projeto.md`, os 5 módulos de teste corrigidos e as alterações geradas pela suíte permanecem na árvore de trabalho, aguardando decisão do titular.

### 21/11/2026 — Integração de `codex/utm-ab-recommendations`: comparativo Hook A/B híbrido

**Situação encontrada:** a branch `codex/utm-ab-recommendations` (`533cc4c`, base `02c57a5`, anterior à Etapa 7) e a `main` continham **duas implementações independentes do mesmo recurso** — o comparativo Hook A × Hook B. Na main: `_compare_hooks` com lift e classificação, agregação por tenant/campanha e integração ao calendário via `--utm-report` (já publicada e com gates verdes). Na branch: `compare_hook_variants` com teste z de duas proporções, desfechos e recomendações, mais API própria de calendário. Decisão do titular: **híbrido — estrutura da main + rigor estatístico da branch**.

**O que foi incorporado (merge `--no-ff` da branch):**

- `_two_proportion_z()` — teste z de duas proporções com p-valor bilateral via `math.erfc`, 100% biblioteca padrão (sem scipy, sem rede), determinístico entre estações.
- `_classify_hook()` — regra única de classificação usada por campanha e por tenant: `amostra_insuficiente` abaixo de sessões ou conversões mínimas; `empate_tecnico` com taxas iguais **ou** quando a diferença não atinge 95% de confiança; `vencedor_A`/`vencedor_B` somente com `|z| >= 1,96` e `p < 0,05`.
- Novos campos em `rankings.hookComparison.byCampaign`/`byTenant`: `zScore`, `pValue`, `significant`, `classificationReason`; bloco `statistics` (`method: two_proportion_z`, `alpha`, `zThreshold`, `minSessions`, `minConversions`).
- Limiar configurável de conversões: parâmetro `min_conversions` e CLI `--min-hook-conversions` (padrão 5), em paridade com `--min-hook-sessions`.
- `campaign_calendar._recommendation()` passa a citar `z`/`p` na justificativa e a registrar explicitamente a ausência de significância; o comportamento segue **apenas recomendatório** (datas, canais, UTMs e textos inalterados).

**O que não entrou (superado pela implementação da main):** `compare_hook_variants`, `load_analytics_report`, `build_hook_priorities` e `apply_analytics_recommendations`, junto com as 184 linhas de testes de calendário da branch baseadas no contrato `analytics-report.json` — a integração equivalente já é coberta por `test_22` a `test_24` de `tools/tests/test_utm_report_importer.py` (contrato `utm-performance-report.json` + `--utm-report`).

**Testes:** nova classe `HookSignificanceTest` (6 casos: determinismo/simetria do z, vencedor com significância, diferença sem significância vira empate, conversões abaixo do mínimo, metadados estatísticos e agregação por tenant) e `test_19_hook_comparison_min_sessions_threshold_configurable` reescrito para a nova semântica (60 sessões com 3 × 6 conversões agora é empate técnico, não vencedor).

**Documentação:** `docs/analytics-utm-playbook.md`, seção 8.5 (critério estatístico, limiares, campos e consumo pelo calendário).

**Validação:** `editorial_qa --all --strict` → 14 campanhas, 7 lentes, 0 erros/0 avisos; `release_check.py` → **APROVADO 7/7 gates**; `test_utm_report_importer` + `test_campaign_calendar` → 44 testes OK.

**Suíte canônica do CI (25 módulos) sobre o merge:** 396 testes, **2 falhas** — `test_05_pipeline_filtered_skip_render_reports_each_stage` e `test_06_pipeline_all_skip_render_consolidates_factory`, ambas porque o estágio de release gate dentro do pipeline reprova com os masters locais divergentes (efeito colateral já documentado: os testes de render com áudio sobrescrevem `.workspace/archives/<slug>/<slug>.mp4`). Após restaurar os 2 masters afetados a partir dos `.mp4` das entregas, **os 2 testes passam** (`OK`), ou seja, 396/396 efetivos. O merge `babfc60` foi enviado ao remoto; a correção do cabeçalho desta Seção 1 está em `76cbd83`.
