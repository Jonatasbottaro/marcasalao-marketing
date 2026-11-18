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
| Branch de trabalho ativa | `codex/fase1-conformidade-editorial` |
| Worktrees de outros agentes | preservadas — ver seção 3 |
| Fase atual | Fase 1 — Desbloqueio de Base e Conformidade Editorial |
| Status das 5 tarefas | ver seção 2 |

---

## 2. Fase 1 — Resumo de execução (2026-11-18)

### Tarefa 1 — Auditoria de identidade visual ("Meu Salão" vs "Marca Salão")

**Resultado: Nenhuma substituição automática realizada. Problema é de responsabilidade do produto externo.**

**Arquivos com ocorrências de "Meu Salão" (busca em toda a árvore rastreada, excluindo `.workspace/`, `.git/`, `node_modules/`):**

| Arquivo | Linha | Tipo de ocorrência | Ação |
|---------|-------|-------------------|------|
| `00-briefings/campanhas/NS-001/briefing.md` | 292 | Descrição de diferença pendente na interface | ✅ Manter — é documentação de divergência conhecida |
| `00-briefings/campanhas/NS-001/briefing.md` | 145, 231, 257, 269, 279 | Alertas editoriais sobre o nome na interface | ✅ Manter — são alertas necessários |
| `00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md` | 8, 83, 97 | Namespace E2E técnico ("Meu Salão E2E") e divergência documentada | ✅ Manter — dado técnico de teste, não tocar |
| `02-hooks/campanhas/NS-001/hooks.md` | 20 | Alerta editorial de diferença | ✅ Manter |
| `00-briefings/campanhas/NS-002/APROVEITAMENTO-NS-002.md` | 42 | Tabela de pendências editoriais | ✅ Manter |
| `03-roteiros/campanhas/NS-002/stories-001.md` | — | Texto: "diferença para Meu Salão na interface permanece sinalizada" | ✅ Manter |
| `03-roteiros/campanhas/NS-002/roteiro-001.md` | — | Texto: "Interface capturada mostra Meu Salão; textos usam Marca Salão" | ✅ Manter |
| `02-reels-shorts/r002-agenda-ficticia/README.md` | 11 | "06_meu_salao.png - Meu Salão" (nome de arquivo de captura) | ✅ Manter — é nome de arquivo de captura histórica, não texto editorial |
| `contexto_repo.txt` / `contexto_projeto.txt` | múltiplas | "Facebook Meu salão" (nome oficial da Página Facebook da marca) | ✅ Manter — é o nome oficial da Página |

**Conclusão da auditoria:**
- "Meu Salão" na interface do Salao02 é o nome de produto exibido pelo sistema externo (`Jonatasbottaro/Salao02`). **Não está neste repositório para ser alterado aqui.**
- "Facebook Meu salão" é o nome oficial da Página do Facebook — não é uma inconsistência de marca.
- Todos os arquivos editoriais (briefings, roteiros, hooks) já documentam a divergência corretamente como pendência a resolver **antes das capturas finais**, não antes da aprovação do roteiro.
- **Ponto de atenção para o titular:** confirmar, antes das capturas finais, qual nome será exibido na interface do produto (Salao02) ou se as capturas serão feitas com overlay de texto cobrindo o nome exibido.

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

---

### Tarefa 5 — `contexto_projeto.md`

**Este arquivo.** Criado em `contexto_projeto.md` na raiz do projeto.

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
| `contexto_projeto.md` | Criado | `codex/fase1-conformidade-editorial` |

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
