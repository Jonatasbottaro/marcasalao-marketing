# Etapa 5B — Agente 3: Onboarding do 5º tenant (`clinica-vital`, nicho regulado de saúde)

Data: 2026-11-20
Branch isolada: `codex/etapa5b-agente3-novo-nicho-clinica`
Worktree: `<RAIZ>/.workspace/worktrees/etapa5b-agente3` (criada a partir de `main` em `edd56e8`)
Base: `main` @ `edd56e8` — "chore(etapa5-parcial): pipeline consolidado, 4 tenants/8 campaigns (audit 7/7 OK)"

## 1. Objetivo

Onboardar o 5º tenant multi-tenant (`tenants/clinica-vital/`) como referência de **nicho regulado (saúde/clínicas)**, com contratos validados, fixture editorial fictícia, duas campanhas `saas-demo` completas, documentação do padrão e testes de contrato, atuando em paralelo e sem tocar no território dos Agentes 1, 2 e 4.

## 2. Isolamento de ambiente

- Worktree criada com `git worktree add -b codex/etapa5b-agente3-novo-nicho-clinica .workspace/worktrees/etapa5b-agente3 main`.
- O primeiro checkout falhou por `Filename too long` (caminho longo de `platform/examples/execution-packages/...` no Windows) e reverteu o diretório, mantendo a branch criada. A repetição com suporte por comando (`git -c core.longpaths=true worktree add ... <branch>`) concluiu o checkout sem alterar configuração global do Git.
- Todos os comandos e edições desta sessão ocorreram dentro da worktree.
- Worktrees `etapa5b-agente1` e `etapa5b-agente2` não foram abertas, editadas nem removidas.

## 3. Arquivos criados/alterados (somente território autorizado)

### Novos — `tenants/clinica-vital/`

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
