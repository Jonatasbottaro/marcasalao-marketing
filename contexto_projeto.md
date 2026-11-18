# contexto_projeto.md — Devlog acumulativo — Marca Salão Content Factory

> Este arquivo é um devlog permanente. **Nunca apagar entradas anteriores.**
> Novas sessões adicionam entradas ao final da seção "Histórico de sessões".
> O topo (seção 1) é sempre atualizado para refletir o estado atual.

---

## 1. Estado atual (atualizado em 2026-11-18)

| Item | Valor |
|------|-------|
| Raiz oficial | `D:/MEGA/Marketing/marcasalao-marketing` |
| HEAD main | `584f8429442c5236db0dbfea5d0bbeca64ec180a` (Merge PR #28) |
| Branch de trabalho ativa | `codex/etapa2-agente1-arquitetura-tenants` (criada a partir de `codex/etapa1-piloto-ns002` `da7d565`) |
| Worktrees de outros agentes | preservadas — ver seção 3 |
| Fase atual | Etapa 2 — Agente 1: Arquitetura Multi-Tenant e Contratos de Marca (Concluída) |
| Status das 5 tarefas | Fase 1, Etapa 1 e Etapa 2 (Agente 1) concluídas — ver seções 2 e 7 |

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
