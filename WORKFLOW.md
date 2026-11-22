# Workflow de Marketing Marca Salão

## Ferramentas
- **Antigravity AI Agent**: Edição conversacional automatizada, raciocínio de cortes e renderização
- **HyperFrames (HeyGen)**: Renderização gráfica determinística em HTML/CSS/GSAP para overlays e motion graphics
- **video-use**: Pipeline de cortes cirúrgicos, legendagem (recursos de áudio não usados neste projeto)
- **FFmpeg**: Automação e composição de vídeo e legendas, sem áudio
- **CapCut / Drift**: Editores manuais de apoio (opcionais)

## Regra de produção: vídeo sem áudio

- Gerar vídeos com legendas visíveis e sincronizadas às cenas.
- Não preservar o áudio original das gravações.
- Não gerar nem inserir narração, música, efeitos sonoros ou qualquer outro áudio no editor.
- Entregar o texto de narração separado em `04-legendas/`, em português brasileiro, organizado por cenas e tempos, pronto para copiar para uma ferramenta externa.
- Entregar também o arquivo `.srt` correspondente às legendas do vídeo.
- O usuário gera o áudio fora do editor de vídeo; essa etapa não é requisito para entregar o vídeo legendado.
- Preferir exportação sem faixa de áudio; não confundir faixa silenciosa com narração gerada.
- Só mudar essa política mediante pedido explícito do usuário.
- Os vídeos existentes de demonstração/teste não devem ser apresentados como campanhas finais aprovadas.

### Aplicação às ferramentas

Esta regra específica do Marca Salão orienta o uso das skills e templates genéricos: não seguir etapas de TTS, música ou preservação de áudio nesses fluxos. Nas composições, manter vídeos mudos e não adicionar elementos de áudio. Na exportação com FFmpeg, mapear somente vídeo e usar `-an`.

### Verificação da entrega

- Conferir as legendas, legibilidade e correspondência com as cenas.
- Conferir a duração do vídeo, do SRT e dos tempos indicados no roteiro.
- Conferir com `ffprobe` se há faixas de áudio; a exportação preferida não contém nenhuma.
- Entregar vídeo legendado + SRT + texto de narração separado, sem gerar áudio.

## Fluxo completo

### Fluxo atual ponta a ponta (fábrica multi-tenant e Video Studio)

1. **Briefing, hooks e roteiro** (`00-briefings/` → `02-hooks/` → `03-roteiros/`): a dor, a
   evidência e os limites de promessa vêm antes de qualquer produção; sem briefing aprovado
   não se produz.
2. **Produção**: programática pela fábrica multi-tenant (`tools/factory_cli.py render`,
   `tools/preset_runner.py`, contratos em `tenants/`) ou interativa pelo Video Studio
   (`python tools/video_studio.py --port 8765`, guia em `tools/produce/README.md`). Sempre
   MP4 sem faixa de áudio para tenants `-an`, com legendas queimadas.
3. **Legendas, pacotes e calendário** (`04-legendas/`): `.srt` sincronizado,
   `<slug>_narracao.txt` separado, pacotes sociais por rede com `autoPublish: false`
   (`tools/publish_pack.py`) e calendário editorial proposto (`tools/campaign_calendar.py`).
4. **Revisão e aprovação humana** (`05-review-portal/` via `tools/review_dashboard.py`,
   ou `tools/approval_cli.py`): o titular decide `aprovado` / `ajuste`; para tenants `-an`,
   confere a locução externa.
5. **Validação de destinos e publicação manual** (`06-validacao-destinos/`): a ficha
   `POSTAGEM-MANUAL.md` e a `copy-pronta.txt` saem de `tools/factory_cli.py handoff
   --all-approved`; a publicação nas redes é feita manualmente pelo titular.
6. **Mensuração e higiene** (`05-mensuracao/`): importação semanal de métricas UTM
   (`tools/utm_report_importer.py`), relatório executivo por tenant
   (`tools/executive_summary.py`) e saúde do checkout (`tools/workspace_doctor.py --check`).

Detalhes operacionais, comandos e gates: [docs/arquitetura-fabrica.md](docs/arquitetura-fabrica.md),
[docs/guia-operacional-titular.md](docs/guia-operacional-titular.md) e
[docs/governanca/CI-E-PRS.md](docs/governanca/CI-E-PRS.md).

### Caminho manual legado (CapCut / Drift / FFmpeg)

#### 1. Captura
- Painel de demonstração: https://marcasalao.com.br/gestor. As credenciais não ficam neste repositório; solicite acesso ao responsável pelo projeto.
- Navegue nas seções e capture telas via browser

#### 2. Artes
- Salve PNG 1080x1920 em `01-insta-stories/`
- Adicione README por pasta

#### 3. Legendas
- Escreva textos curtos em `04-legendas/`
- Formato: título + 3-5 bullets + CTA
- Entregue `.srt` sincronizado e texto de narração separado por cenas e tempos, para geração de áudio fora do editor

#### 4. Edição
##### CapCut
- Importe imagens e vídeos, sem áudio original e sem adicionar áudio
- Adicione texto dinâmico
- Exporte 1080x1920, 30fps

##### Drift
- Importe mídia via UI ou MCP Agent
- Use Look Templates para consistência
- Exporte vertical e horizontal, sem áudio

##### FFmpeg
- Automação de lote
- Sobreposição de texto e exportação sem áudio (`-an`)

#### 5. Publicação
- Instagram/Reels: `02-reels-shorts/`
- YouTube/PDF: `03-youtube-pdf/`
- GitHub Releases para distribuição

## Checklist
- [ ] Capturas sem dados sensíveis
- [ ] Legendas revisadas
- [ ] Texto de narração separado e pronto para ferramenta externa
- [ ] SRT sincronizado com as cenas
- [ ] Vídeo sem áudio original, narração, música ou efeitos
- [ ] Vídeo exportado
- [ ] Commit + push no repo

## Fontes canônicas deste fluxo

Este arquivo mantém as regras essenciais do fluxo de marketing; o detalhe operacional vive
nas fontes canônicas, indexadas em [docs/README.md](docs/README.md):

- Regras de operação, autorizações e armazenamento: [AGENTS.md](AGENTS.md).
- Briefing → hooks → roteiro → legendas: [00-briefings/README.md](00-briefings/README.md),
  [02-hooks/README.md](02-hooks/README.md), [03-roteiros/README.md](03-roteiros/README.md).
- Produção programática (fábrica multi-tenant): [docs/arquitetura-fabrica.md](docs/arquitetura-fabrica.md).
- Produção pelo painel/CLI (Video Studio, carrossel, Motion, cortes, ZIP):
  [tools/produce/README.md](tools/produce/README.md).
- Aprovação, handoff e publicação manual: [docs/guia-operacional-titular.md](docs/guia-operacional-titular.md).
- Mensuração e UTM: [docs/analytics-utm-playbook.md](docs/analytics-utm-playbook.md).
- Estado verificado e pendências: [docs/contexto/ESTADO-ATUAL.md](docs/contexto/ESTADO-ATUAL.md).
