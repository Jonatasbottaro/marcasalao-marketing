# Workflow de Marketing Marca Salão

## Ferramentas
- **HyperFrames (HeyGen)**: **Motor principal de composição e renderização audiovisual** (decisão [MKT-VIDEO-003](docs/decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md), 27/11/2026) — runtime pinado 0.9.103 em `renderers/hyperframes/`, operado pelos wrappers (`hf.sh`/`hf-project.sh`); migração documentada em [docs/migracao-hyperframes/](docs/migracao-hyperframes/README.md)
- **Antigravity AI Agent**: Edição conversacional automatizada, raciocínio de cortes e renderização
- **video-use**: Pipeline de cortes cirúrgicos, legendagem (recursos de áudio não usados neste projeto)
- **FFmpeg**: Infraestrutura e fallback do render (composição local `--clean` permanece instalada e testada); fábrica legada (`preset_runner`/`factory_cli`) congelada
- **CapCut / Drift**: Editores manuais de apoio (opcionais)

## Regra de produção: VIDEO CLEAN / narração separada (26/11/2026)

Decisão do titular em 26/11/2026; registro completo em
[docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md](docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md).
Substitui a política anterior "vídeo sem áudio" (legendas queimadas + SRT obrigatórios);
campanhas antigas com legendas e SRT permanecem válidas e nada anterior é excluído.

- Renderizar vídeos sem nenhuma faixa de áudio, música ou narração; não preservar o áudio original.
- Não inserir legendas narrativas queimadas nos MP4.
- Não gerar SRT por padrão; legendas somente por solicitação expressa.
- Entregar o texto de narração separado em `04-legendas/`, em português brasileiro, organizado por cenas e tempos, pronto para copiar para uma ferramenta externa.
- Preservar textos gráficos editoriais da composição visual (títulos, destaques, chips, CTA de endcard).
- Sem faixas/áreas reservadas exclusivamente para legendas queimadas nas novas composições; o espaço liberado melhora enquadramento, tamanho, legibilidade, movimento e hierarquia.
- Elementos essenciais dentro das áreas seguras de cada plataforma (legendas podem ser adicionadas depois no CapCut/Canva).
- Preferir exportação sem faixa de áudio; não confundir faixa silenciosa com narração gerada.
- Só mudar essa política mediante pedido explícito do usuário.
- Os vídeos existentes de demonstração/teste não devem ser apresentados como campanhas finais aprovadas.

### Aplicação às ferramentas

Esta regra específica do Marca Salão orienta o uso das skills e templates genéricos: não seguir etapas de TTS, música ou preservação de áudio nesses fluxos. Nas composições, manter vídeos mudos e não adicionar elementos de áudio. Na exportação com FFmpeg, mapear somente vídeo e usar `-an`. No caminho VideoRequest/Video Studio, usar `--clean` (`tools/produce_video.py`, `tools/render_pipeline.py`, `tools/render_local.py`): sem legenda queimada, sem SRT, narração TXT preservada; sem a flag, o comportamento legado permanece para campanhas antigas. O caminho legado da fábrica (`preset_runner`/`factory_cli`) não foi alterado por esta decisão.

### Verificação da entrega

- Conferir os textos editoriais, legibilidade e correspondência com as cenas.
- Conferir a duração do vídeo e os tempos indicados no roteiro de narração.
- Conferir com `ffprobe` se há faixas de áudio; a exportação preferida não contém nenhuma.
- Conferir ausência de legendas narrativas queimadas (antiga banda de legendas sem texto).
- Entregar vídeo limpo + texto de narração separado + player + verificações técnicas + ZIP, sem gerar áudio. SRT não é condição de conclusão no modo clean.

## Fluxo completo

### Fluxo atual ponta a ponta (fábrica multi-tenant e Video Studio)

1. **Briefing, hooks e roteiro** (`00-briefings/` → `02-hooks/` → `03-roteiros/`): a dor, a
   evidência e os limites de promessa vêm antes de qualquer produção; sem briefing aprovado
   não se produz.
2. **Produção**: programática pela fábrica multi-tenant (`tools/factory_cli.py render`,
   `tools/preset_runner.py`, contratos em `tenants/`) ou interativa pelo Video Studio
   (`python tools/video_studio.py --port 8765`, guia em `tools/produce/README.md`). Sempre
   MP4 sem faixa de áudio para tenants `-an`. **Padrão atual (26/11/2026): VIDEO CLEAN** —
   novas produções pelo caminho VideoRequest usam `tools/produce_video.py --clean`
   (sem legendas queimadas, sem SRT); o caminho legado da fábrica mantém legendas
   queimadas para campanhas antigas.
3. **Narração, pacotes e calendário** (`04-legendas/`): `<slug>_narracao.txt` separado
   (obrigatório no modo clean), `.srt` sincronizado apenas quando legendas forem
   solicitadas ou em campanhas legadas, pacotes sociais por rede com `autoPublish: false`
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

#### 3. Legendas e narração
- Escreva textos curtos em `04-legendas/`
- Formato: título + 3-5 bullets + CTA
- Entregue texto de narração separado por cenas e tempos, para geração de áudio fora do editor
- `.srt` sincronizado somente quando legendas forem solicitadas expressamente (padrão clean de 26/11/2026) ou em campanhas legadas

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
- [ ] Textos editoriais revisados (legendas narrativas não são queimadas no modo clean)
- [ ] Texto de narração separado e pronto para ferramenta externa
- [ ] SRT sincronizado somente se legendas foram solicitadas (ou campanha legada)
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
