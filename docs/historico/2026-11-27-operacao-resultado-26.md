# Operação Resultado 26 — Qualidade Criativa V3 (PILOTO-OPERACIONAL-001-V3)

Data: 2026-11-27
Branch de trabalho: `codex/operacao-resultado-26` (worktree isolada `.workspace/worktrees/op26`)
Base: `origin/codex/operacao-resultado-24` (inclui o fix P1 `56f6800` e os docs da Op 25)
Escopo: elevar a qualidade criativa das peças Marca Salão (post 4:5, carrossel, reel) para v3,
com tipografia profissional, identidade de marca, imagens reais do produto, narração corrigida e
entrega revisável — **sem** criar novo editor, **sem** substituir o Video Studio, **sem** refazer a
arquitetura, **sem** publicar/agendar/merge/deploy.

> Restrições respeitadas: não alterar a `main`; não alterar o Salao02; não sobrescrever Op 23/Op 24;
> não publicar, agendar nem aprovar campanha automaticamente; não usar force push; não usar dado real
> de cliente; não criar funcionalidade visual inexistente no produto; não gerar imagem por provedor
> pago sem autorização; não inserir chave no código; não declarar qualidade estética aprovada (o agente
> não lê imagens). Todos os materiais permanecem **AGUARDANDO APROVAÇÃO DO TITULAR**.

## A. Escopo e resultado

Entrega v3 do piloto, composta por três peças redesenhadas e materiais de revisão, produzidas por um
motor de tipografia comercial reutilizável (ASS/libass sobre o FFmpeg portátil já existente). Não foi
criado editor novo; o Video Studio não foi substituído nem reconstruído.

## B. Estado inicial verificado

- Repositório e branch conferidos no Git; worktree isolada criada dentro de `.workspace/worktrees/op26`.
- Base já continha o fix P1 do VIDEO CLEAN (`56f6800`) e os documentos da Op 25.
- Causa-raiz da tipografia "pixelada": o renderizador legado `tools/carousel_layout.py` usa fonte
  **bitmap 5×7** e transliteração (remove acentos).
- Capturas reais autorizadas localizadas em `00-briefings/campanhas/NS-001/capturas/2026-11-05/`.

## C. Correção da tipografia (P1)

- Novo motor `tools/commercial_text.py`: ASS v4.00+ sobre `libass` (filtro `ass=`/`subtitles=`),
  resolvendo **Arial** pelo provedor do sistema (DirectWrite no Windows; fontconfig no Linux), com
  acentos, negrito, cor de marca, alinhamento (numpad) e **quebra automática por largura** (WrapStyle 0).
- Nenhuma dependência de Pillow nem medição manual de texto; reaproveita o FFmpeg portátil do projeto.
- O renderizador bitmap legado permanece intacto (válido para testes e entregas históricas).

## D. Identidade visual Marca Salão

- Paleta do `tenants/marca-salao/brand-kit.json` aplicada: primário #F5C107, secundário #4F8CFF,
  acento #28B463, fundo #121620→#1C2434 (gradiente), texto #F5F7FA/#B4C0D2.
- Barra de acento no topo, rótulo de marca "MARCA SALAO | AGENDAMENTO ONLINE" e tipografia bold.

## E. Imagens reais do produto

- Post e carrossel usam **capturas reais autorizadas** da agenda (`capturas/2026-11-05/`):
  `10-agenda-mobile-dia.png`, `11-agenda-mobile-semana.png`, `03-agenda-status-confirmado.png`.
- Enquadramento preservando proporção (scale + pad + setsar), sem distorção, em moldura com borda.
- As capturas são **evidência técnica**, não frames finais aprovados; a peça segue pendente do titular.

## F. Regras de geração por IA (documentadas)

- Nenhuma imagem por IA foi usada nestas peças v3; não houve chamada a provedor pago (sem autorização).
- Regra registrada: imagem de IA é **ilustrativa** e nunca pode ser apresentada como screenshot do
  aplicativo; chaves ficam fora do código; simulador não é arte final; rótulo sintético quando aplicável.

## G. Redesign do post 4:5

- `tools/produce_v3.py::compose_post` — 1080×1350, texto ASS (marca, título, sub, CTA) + captura mobile
  em moldura. CTA neutra "Conheça o Marca Salão" (padrão de arte compartilhada de 22/10).

## H. Redesign do carrossel

- `tools/produce_v3.py::compose_carousel` — 4 cards 1080×1080 (`01-capa`, `02-horarios`,
  `03-atendimentos`, `04-cta`), com badge, título, corpo e CTA; capturas reais nos cards 1–3.

## I. Redesign do reel

- `tools/produce_v3_reel.py` — 1080×1920, 30 fps, h264/yuv420p, **20 s**, **0 faixas de áudio (`-an`)**.
- 4 cenas com legendas de tela curtas e sincronizadas (ASS/libass); cenas 2–3 usam capturas reais.

## J. Correção do gerador de narração (Fase I)

- **Antes (v2):** o arquivo de narração continha verbos de direção ("Apresente…", "Mostre…",
  "Destaque…") e uma promessa proibida ("reduzir faltas").
- **Agora (v3):** direção e narração são **arquivos distintos**:
  - `03-reel/direcao-de-cenas.md` — o que mostrar em cada cena;
  - `04-legendas/narracao-reel.txt` — fala real por cena/tempo, sem verbos de direção;
  - `04-legendas/legendas.srt` — legendas cronometradas.

## K. Auditoria de claims (Fase J)

- `tools/assemble_v3_delivery.py::audit_claims` compara todos os textos (imagens, cópias, narração,
  SRT, direção) contra `forbiddenClaims`/`forbiddenUiElements` do `guardrails.json` do tenant.
- Resultado: **0 ocorrências** (auditoria limpa). Removidas promessas de "reduzir faltas" etc.

## L. Estrutura de template reutilizável (Fase K)

- "Modo Comercial" = `commercial_text` (texto) + `produce_v3` (estáticas) + `produce_v3_reel` (vídeo)
  + `assemble_v3_delivery` (entrega). Brand-kit e capturas são dados, não código.
- Assim, o ganho de qualidade é reaplicável a outras peças sem novo editor.

## M. Revisão visual obrigatória (Fase L)

- Pacote de revisão gerado: `review/review.html` (página validada: todas as imagens carregam),
  `board-carousel.png` (2×2), `board-reel.png` (4 frames), `comparacao-v2-v3.png` (post v2 × v3).
- **Limitação declarada:** o agente **não visualiza imagens**; portanto **não declara aprovação
  estética**. A avaliação visual humana é obrigatória e está pendente.

## N. Testes de regressão (Fase M)

- Novo `tools/tests/test_produce_v3.py` (grupo render) — valida geometria, texto renderizado (variância),
  reel VIDEO CLEAN sem áudio, separação narração/direção e claims limpos. Resultado: **3/3 OK**.
- `test_produce_v3` registrado em `tools/run_tests.py` (RENDER_MODULES) — particionamento sem órfãos.
- Suítes relacionadas (todas verdes, com o `platform` compilado):
  - `test_run_tests` — **45/45 OK** (valida a própria partição, sem órfãos);
  - `test_render_local` — **33/33 OK** (a falha anterior era só o `platform/dist` ausente → exit 2);
  - `test_produce_carousel` — **7/7 OK**;
  - `test_ns002_pilot` — **5/5 OK**; `test_build_video` — OK.
- `platform` compilada (`npm ci` + `npm run build`) dentro da raiz para habilitar a ponte Node dos testes.

## O. Entrega v3 (Fase N)

- `.workspace/archives/operacao-resultado-26/delivery-v3/` (local, não versionada):
  `post-45/01-capa.jpg`, `carousel/` (4 cards + `carousel.zip`), `03-reel/` (reel + direção),
  `04-legendas/` (narração + SRT), `05-copias/` (Facebook/Instagram + `claims-audit.json`),
  `media-manifest.json` (com SHA-256), `QUALIDADE-V3.md`, `review/`, `delivery-v3-completa.zip`.

## P. Validação do Video Studio (Fase O)

- O Studio não foi modificado por esta operação; validado como intacto por inspeção do código e pela
  suíte `test_video_studio`/`test_studio_video_api` (não alteradas). Nenhum novo editor foi criado.

## Q. Git e integração (Fase P)

- Branch `codex/operacao-resultado-26`; commits e push normal (sem force). Base do PR sugerida:
  `codex/operacao-resultado-24` (não `main`). PR em rascunho a ser aberto **após** confirmação —
  nenhum merge, nenhum deploy. `main` intacta.

## R. Riscos residuais

- Aprovação visual humana pendente (agente não lê imagens).
- Capturas são evidência técnica (podem conter rótulo técnico E2E); uso como frame final exige revisão.
- Integração à `main` depende de autorização do titular (Op 23/24/25/26 encadeadas).

## S. Pendências

- Decisão do titular sobre link/bio e destino; assinatura da identidade; aprovação estética das peças.

## T. Confirmação / Handoff (portabilidade)

- Raiz usada (`git rev-parse --show-toplevel`): `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing/.workspace/worktrees/op26`
  (worktree; o checkout principal é `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`).
- Diretórios auxiliares criados, todos sob a raiz: `.workspace/worktrees/op26`, `.workspace/tmp/*`
  (staging transitório), `.workspace/archives/operacao-resultado-26/delivery-v3`.
- Worktrees criadas/removidas: nenhuma removida nesta etapa; worktree `op26` mantida para revisão.
- Ferramentas portáteis: FFmpeg/FFprobe portáteis já existentes (junção em `.workspace/tools/ffmpeg`);
  Node do sistema para `npm ci`/`build` do `platform` (dentro da raiz).
- Nenhum merge, deploy, publicação ou agendamento. `main` e PRs intactos.
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora de
  `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing/.workspace/worktrees/op26`.
