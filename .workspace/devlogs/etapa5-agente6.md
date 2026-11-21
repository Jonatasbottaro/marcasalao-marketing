# Etapa 5B — Agente 5 de 8: auditoria, validação e render do 5º tenant (`clinica-vital`)

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
