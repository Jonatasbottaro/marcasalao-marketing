# contexto_projeto.md — Devlog acumulativo — Marca Salão Content Factory

> Este arquivo é um devlog permanente. **Nunca apagar entradas anteriores.**
> Novas sessões adicionam entradas ao final da seção "Histórico de sessões".
> O topo (seção 1) é sempre atualizado para refletir o estado atual.

---

## 1. Estado atual (atualizado em 2026-11-18)

| Item | Valor |
|------|-------|
| Raiz oficial | `D:/MEGA/Marketing/marcasalao-marketing` |
| HEAD main (base / integração) | `af1e15f` (consolidação da Etapa 3 na `main`: 4 tenants, 8 campanhas, pacotes sociais, `devlog_sync` e suíte de CI), linear após `ad95adc → d55b291 → a77efe5 → d70dd93`, sem push remoto |
| Branch de trabalho ativa | `main` (Etapa 3 consolidada a partir dos 4 agentes paralelos: `ad95adc` agente1 → `d55b291` agente2 → `a77efe5` agente3 → `d70dd93` agente4 → `af1e15f` consolidação; sem push remoto) |
| Worktrees de outros agentes | preservadas — ver seção 3 |
| Fase atual | Etapa 3 concluída — Plataforma Multi-Tenant + Sync Multi-Agente (4 agente(s): 1, 2, 3, 4) |
| Status das 5 tarefas | Fase 1, Etapa 1, Etapa 2 e Etapa 3 (Agentes 1, 2, 3, 4) concluídas — ver seções 2 e 7 |
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
