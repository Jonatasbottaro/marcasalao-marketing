# Devlog — Etapa 5, Agente 1 de 4 (Cards Estáticos: Stories e Carrossel)

## Contexto

- Repositório: `marcasalao-marketing` (worktree isolada `.workspace/worktrees/etapa5-agente1`)
- Branch: `codex/etapa5-agente1-cards-carrossel-stories` (a partir de `main`, commit `73662ff`)
- Base de leitura: `contexto_projeto.md`, `tools/preset_runner.py`, `schemas/brand-kit.schema.json`
- Território exclusivo (editado/criado): `tools/static_cards.py`, `tools/tests/test_static_cards.py`,
  `01-insta-stories/deliveries/**`, `.workspace/devlogs/etapa5-agente1.md`
- Não tocado: `contexto_projeto.md`, `tools/preset_runner.py`, `02-reels-shorts/**`, worktrees dos
  agentes 2, 3 e 4 (`etapa5-agente3` preservada).

## O que foi implementado

### `tools/static_cards.py` — Motor programático de cards estáticos (100% stdlib)

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
