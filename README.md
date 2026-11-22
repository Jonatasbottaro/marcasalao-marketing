# Marca Salão Marketing

Repositório de marketing do Marca Salão, com fluxos também organizados para a Multitrack
Hub e um núcleo reutilizável de produção de conteúdo. **A documentação tem um ponto de
entrada central: [docs/README.md](docs/README.md).** Este README é apenas a apresentação
curta do repositório.

- Regras operacionais e autorizações: [AGENTS.md](AGENTS.md).
- Fluxo de marketing e regra de vídeo sem áudio: [WORKFLOW.md](WORKFLOW.md).
- Estado técnico verificado, backlog e retomada: [docs/contexto/](docs/contexto/README.md).
- Inventário e manutenção documental: [docs/governanca/](docs/governanca/MAPA-DOCUMENTAL.md).

## As quatro frentes do projeto

1. **Fluxo editorial de campanhas** (`00-briefings/` a `06-validacao-destinos/`): evidência,
   briefing, hooks, roteiro, legendas, aprovação e mensuração.
2. **Fábrica multi-tenant** (`tenants/` + `tools/` + `schemas/`): contratos → render →
   pacotes → calendário → portal → gates, para N marcas sem alterar o motor.
3. **Núcleo reutilizável** (`platform/`): contratos puros, validação e CLIs internas em
   TypeScript; e **orquestração experimental** (`orchestration/temporal/`), piloto local.
4. **Video Studio local** (`tools/video_studio.py` + `tools/studio/`): criação, revisão e
   entrega interativas, com biblioteca de mídia e fila de produção.

As integrações de marca (ComfyUI/Postiz/Hermes) são uma camada à parte, com escopo e
estação próprios: [docs/hermes/README.md](docs/hermes/README.md). Mapa completo e fontes
canônicas por assunto: [docs/README.md](docs/README.md).

## Estrutura

- `00-briefings/` — briefings de campanha: dor, impacto, evidência e limites de promessa.
- `01-insta-stories/`, `02-reels-shorts/`, `02-hooks/`, `03-roteiros/`, `03-youtube-pdf/`,
  `04-legendas/` — conteúdo editorial e entregas por formato.
- `05-review-portal/` — portal estático de revisão humana (**gerado** por
  `tools/review_dashboard.py`).
- `05-mensuracao/`, `06-validacao-destinos/` — guias de mensuração e destinos (ensaios
  fictícios declarados).
- `schemas/`, `tenants/` — contratos multi-tenant (brand-kit, guardrails, fixtures, campanhas).
- `marcas/` — materiais e integrações específicas de Marca Salão e Multitrack Hub.
- `platform/` — núcleo TypeScript de contratos, validação e CLIs internas.
- `orchestration/temporal/` — piloto local de orquestração (sem deploy).
- `tools/` — fábrica Python, Video Studio local, render, pacotes, gates e auditorias.
- `docs/` — documentação canônica por assunto; `docs/auditorias/` — auditorias e consolidações.

## Fábrica de vídeo multi-tenant

Pipeline programático que transforma contratos JSON versionados em pacotes de vídeo para
publicação **manual**, para N marcas sem alterar o motor de render. Estado verificado em
22/11/2026 na base `main` @ `05ca7fa` (leitura de código; sem execução de testes):
**5 tenants, 14 campanhas**, calendário de 7 semanas / 56 slots com
`statusEditorial: "aguardando_aprovacao_titular"`, suíte Python em **4 faixas / 51 módulos**
(`smoke` 25, `fast` 29, `render` 22, `all` 51), **9 gates** no `release_check`,
**8 domínios** no `release_audit` e **7 lentes** no `editorial_qa`.
Cada campanha entrega MP4 1080×1920@30 (sem faixa de áudio quando o tenant proíbe), SRT,
narração TXT, storyboard, `manifest.json` com SHA-256 e `derivatives.json`; o pacote social
sai com `autoPublish: false`. **Nenhuma ferramenta da fábrica publica, agenda ou cria
rascunho nas redes.** Arquitetura, gates e manifests:
[docs/arquitetura-fabrica.md](docs/arquitetura-fabrica.md); rotina do titular:
[docs/guia-operacional-titular.md](docs/guia-operacional-titular.md).

| Tenant | Marca | Preset | Domínio | Áudio | Campanhas |
| --- | --- | --- | --- | --- | --- |
| `marca-salao` | Marca Salão | `saas-demo` | marcasalao.com.br | Proibido (`-an`) | 2 |
| `multitrack-hub` | Multitrack Hub | `shorts-completo` | multitrackhub.com.br | Permitido (opcional) | 4 |
| `meu-salao` | Meu Salão | `saas-demo` | meusalao.com.br | Proibido | 3 |
| `estudio-flow` | Estúdio Flow | `saas-demo` | estudioflow.com.br | Proibido | 2 |
| `clinica-vital` | Clínica Vital | `saas-demo` | clinicavital.com.br | Proibido | 3 |

Verificação de release em um comando (orquestra os 9 gates; não publica nada):

```bash
python tools/release_check.py            # todos os gates oficiais
python tools/release_check.py --skip-ts  # quando platform/ já foi compilado
python tools/release_check.py --json     # relatório JSON no stdout
```

## Video Studio local e produção por entrada única

Painel HTTP somente em `127.0.0.1` para criar, revisar, retomar e exportar Vídeo, Carrossel
e Motion, com biblioteca de mídia por trabalho, fila de produção persistente, revisão
editorial por versão e pacote ZIP verificado por SHA-256. Guia canônico (CLI, painel,
multiformato, cortes, Motion, biblioteca, ZIP, adaptadores e configuração Gemini):
[tools/produce/README.md](tools/produce/README.md). Render local e limites de determinismo:
[tools/render/README.md](tools/render/README.md).

```bash
python tools/video_studio.py --check
python tools/video_studio.py --port 8765   # abra http://127.0.0.1:8765
```

Matriz de formatos comprovada por render real + FFprobe + navegador nos aceites de
14/11/2026 (registro histórico em
[docs/historico/2026-11-14-exportacao-multiformato-aceite.md](docs/historico/2026-11-14-exportacao-multiformato-aceite.md);
não reexecutada nesta consolidação):

| Módulo | Perfil | Geometria | FPS | Áudio |
| --- | --- | --- | --- | --- |
| Vídeo | `instagram-reels-video`, `facebook-reels-video`, `youtube-shorts` | 1080×1920 (9:16) | 30 | 0 faixas |
| Vídeo | `youtube-video-horizontal` | 1920×1080 (16:9) | 30 | 0 faixas |
| Carrossel | `instagram-feed-image-square`, `facebook-feed-image-square` | 1080×1080 (1:1) | — | — |
| Carrossel | `instagram-feed-image-portrait`, `facebook-feed-image-portrait` | 1080×1350 (4:5) | — | — |
| Motion | perfis de vídeo 9:16 | 1080×1920 | 30 | 0 faixas (horizontal bloqueado com diagnóstico) |

## Editorial, integrações e demonstração

- Fluxo editorial: [00-briefings/README.md](00-briefings/README.md) → hooks → roteiros →
  legendas → aprovação do titular → publicação manual → mensuração.
- Integrações de marca (ComfyUI/Postiz/Hermes), com guard de proveniência e escopo por
  estação: [docs/hermes/README.md](docs/hermes/README.md) e
  [marcas/marcasalao/comfyui/README.md](marcas/marcasalao/comfyui/README.md).
- Demonstração: https://marcasalao.com.br/gestor — credenciais **não** ficam neste
  repositório; solicite acesso ao responsável.
- Ferramentas de apoio: CapCut, Drift (https://cutwire.org/drift), FFmpeg.

## Padrão de entrega

Vídeos sem áudio, com legendas nas cenas, arquivo SRT e texto de narração separado para
geração de áudio em ferramenta externa. Não preservar o áudio original nem gerar áudio no
editor. Vídeos de teste não são campanhas finais aprovadas. Regra completa e verificações:
[WORKFLOW.md](WORKFLOW.md).

## Releases e contribuição

GitHub Releases para distribuir pacotes de vídeo completos
([.github/RELEASE_TEMPLATE.md](.github/RELEASE_TEMPLATE.md)). Artes nas pastas
correspondentes, legendas em `04-legendas/`; commit e push exigem autorização própria e
alinhamento por Git entre estações ([AGENTS.md](AGENTS.md)).