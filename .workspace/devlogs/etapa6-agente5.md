# Etapa 6 — Agente 5 de 8: campanha 002 do tenant `estudio-flow` (gestão interna)

Data: 2026-11-20
Branch isolada: `codex/etapa6-agente5`
Worktree: `<RAIZ>/.workspace/worktrees/etapa6-agente5` (já existia; **não** foi recriada)
Base: `main` @ `8a1b361` — "chore(release): conclui Etapa 5B (5 tenants, 10 campanhas, 8 agentes paralelos)"
Raiz real desta estação: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

## 1. Isolamento e protocolo de contexto

- `git fetch origin --prune --no-tags` executado no início, sem trocar branch ou HEAD.
- A worktree `etapa6-agente5` já estava registrada no commit `8a1b361`, na branch
  `codex/etapa6-agente5`. A regra 1 ("criar se não existir") não se aplicou: nenhuma worktree
  foi criada, movida ou removida.
- Território respeitado: `tenants/estudio-flow/campaigns/**`,
  `02-reels-shorts/deliveries/estudio-flow/camp-saas-demo-estudio-flow-002/**` e este devlog.
  Não houve escrita em `contexto_projeto.md`, `factory-report.json`, schemas, ferramentas,
  fixtures, brand-kit/guardrails ou outros tenants.
- **Protocolo `contexto_projeto.md`:** o arquivo não foi editado. Este devlog é o relatório
  completo destinado ao `tools/devlog_sync.py` da consolidação, que o transferirá para a Seção 7
  do contexto. O documento usa um título `#` único e seções `##`, sem cabeçalhos `###`, para que
  o sincronizador reconheça o título correto.

## 2. Referências lidas

- `tenants/estudio-flow/brand-kit.json` — preset `saas-demo`, paleta `#C86D51` / `#6B8E78` /
  `#E6D5B8` / `#1C1917`, `headerOverlay` e `subtitleStyle` replicados na campanha.
- `tenants/estudio-flow/guardrails.json` — `forbiddenClaims`, `forbiddenUiElements`,
  `routeRules` (`/aulas/[studioId]` = `public-booking`; `/gestor/turmas` = `manager-agenda`)
  e `audioPolicy` com `allowAudioTrack: false` e `ffmpegFlag: "-an"`.
- `tenants/estudio-flow/fixtures/fixture-editorial-estudio-flow.json` — instrutoras
  (`inst-ef-003` Clara Nogueira), turmas (`turma-ef-001`, `turma-ef-003`, `turma-ef-004`)
  e alunas fictícias (Andréia Silveira).
- `tenants/estudio-flow/campaigns/camp-saas-demo-estudio-flow-001.json` — padrão de estrutura,
  metadados de artefatos, estilo de legenda e cronograma de 6 cenas.

## 3. Arquivos criados/alterados

### Novo — `tenants/estudio-flow/campaigns/camp-saas-demo-estudio-flow-002.json`

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
