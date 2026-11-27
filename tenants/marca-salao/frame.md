---
# frame.md — design system de VÍDEO do Marca Salão (frame-scale)
#
# Camada normativa = o frontmatter abaixo (colors, typography, spacing, components,
# audio, captions). Ele deriva de fontes canônicas já existentes no repositório:
#   - tenants/marca-salao/brand-kit.json   (paleta, headerOverlay, subtitleStyle, tipografia)
#   - tenants/marca-salao/guardrails.json  (alegações proibidas, política de áudio)
#   - docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md (padrão de legendas/áudio)
# Prosa = contexto (intenção, quando usar, restrições). Não é token.
#
# Precedência de leitura do pipeline: frame.md → design.md → DESIGN.md.
name: Marca Salão
kind: video
scope: reels/shorts 9:16, youtube-shorts, youtube-video-horizontal 16:9, carrossel 1:1 e 4:5
version: 2
updated: 2026-11-27

colors:
  background: "#121620"
  surface: "#222C40"
  primary: "#F5C107"      # amarelo — acento principal (destaque, números, badge)
  secondary: "#4F8CFF"    # azul — apoio (links, trilhos, dados neutros)
  accent: "#28B463"       # verde — confirmação/positivo
  textPrimary: "#F5F7FA"
  textMuted: "#B4C0D2"
  headerBg: "#0E121C"
  status:
    confirmed: "#28B463"
    waiting: "#F5B041"
    done: "#8291AA"

typography:
  fontFamily: "Arial"
  titleWeight: "bold"
  bodyWeight: "bold"

spacing:
  headerHeight: 170
  # Margem de legenda: só se aplica quando legendas forem solicitadas expressamente
  # (fluxo legado) — NÃO é padrão no modo clean.
  subtitleMarginV: 34

components:
  headerOverlay:
    enabled: true
    label: "MARCA SALAO"
    badge: "AGENDAMENTO ONLINE"
    bg: "#0E121C"
    text: "#F5F7FA"
    replaceLegacyLabel: "Meu Salão"
  subtitle:
    # Estilo ASS (libass) da legenda queimada. NÃO é padrão do modo clean:
    # aplica-se apenas ao fluxo legado da fábrica ou a legendas pedidas expressamente.
    default: false
    appliesTo: "legacy-or-on-express-request"
    style: "Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=34"

audio:
  allowAudioTrack: false
  requireExternalNarration: true
  ffmpegFlag: "-an"

captions:
  standard: "clean"                 # VIDEO CLEAN — docs/decisoes/MKT-VIDEO-002
  burnNarratedCaptions: false       # sem legendas narrativas queimadas no MP4
  srtByDefault: false               # SRT só por solicitação expressa
  srtOnExpressRequest: true
  legacyFactoryRequireSrt: true     # preset_runner/factory_cli permanece inalterado
  narrationTxtDir: "04-legendas/"   # roteiro de narração em TXT separado (obrigatório)
  preserveGraphicTexts: true        # títulos/chips/CTA gráficos NÃO são legendas narrativas
  reserveCaptionBands: false        # não reservar faixa/área só para legenda queimada
---

# Marca Salão — Design system de vídeo (`frame.md`)

Este arquivo é a **verdade de marca para vídeo** do tenant `marca-salao`. Ele reframe a
identidade com o **quadro como unidade**, porque o material deste projeto é vídeo curto
(reels/shorts) com **textos gráficos editoriais** — não página web, e não legenda
narrativa queimada. Os tokens do frontmatter são os valores reais; a prosa explica
intenção e restrições.

O sistema de **arte estática de feed** (ComfyUI, quadrado/vertical) é um companheiro
separado — ver "Arte de feed (companheiro)" abaixo. Não misturar os dois: a arte de feed
usa verde-petróleo/menta; a sobreposição de vídeo usa a paleta escura do `brand-kit.json`.

## Decisão vigente de formato — VIDEO CLEAN (26/11/2026)

A decisão canônica vigente para novas produções do Marca Salão é **VIDEO CLEAN**
([docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md](../../docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md)),
espelhada em `AGENTS.md` e `WORKFLOW.md`:

- MP4 **sem faixa de áudio**, música ou narração embutida (`-an`).
- **Sem** legendas narrativas queimadas.
- **Sem SRT por padrão** — legendas só por solicitação expressa.
- Roteiro de narração em **TXT separado** em `04-legendas/` (obrigatório).
- Preservar os **textos gráficos editoriais** da composição (títulos, badges, chips de
  status, CTA de endcard) — não são legendas narrativas.
- Sem faixas/áreas reservadas só para legenda; reaproveitar o espaço para hierarquia e
  legibilidade; manter elementos essenciais dentro das **áreas seguras** (legendas podem
  ser adicionadas depois, no CapCut/Canva).

## Visão geral

- **Marca:** Marca Salão — sistema de **agendamento online e agenda do salão**.
- **Domínio:** https://marcasalao.com.br
- **Público:** donas(os) e equipes de salão; a dor é organização da agenda e visão do dia.
- **Tom:** claro, prático, profissional. Mostra o produto real pela interface
  (`/gestor/agenda`, `/booking/[salonId]`), sem promessas exageradas.
- **Limite de promessa (guardrails):** nunca afirmar whatsapp, sms, lembrete, 24h,
  "automático/automatizado", redução de faltas, no-show, aumento/garantia de faturamento
  ou "agenda sempre cheia". Não usar "meu salão" na comunicação desta marca.
- **Sem UI proibida:** pagamento, cobrança, checkout, cartão de crédito.

## O quadro (The Frame)

- **Formato primário:** 9:16, `1080x1920`, 30 fps, H.264 / yuv420p — destinos
  `instagram-reels-video`, `facebook-reels-video`, `youtube-shorts`.
- **Variantes locais:** `youtube-video-horizontal` 16:9 `1920x1080`; carrossel 1:1
  `1080x1080` e 4:5 `1080x1350`. A geometria vem do perfil resolvido; o layout acompanha.
- **Camadas (fundo → frente):** captura real do produto (mídia) → **headerOverlay**
  (`MARCA SALAO` + badge `AGENDAMENTO ONLINE`) → badge/headline/subline da cena → **textos
  gráficos editoriais** (títulos/chips/CTA). **Não há camada de legenda narrativa queimada
  no modo clean.** Recorte local com enquadramento por cena/destino (`framingByProfile`),
  movimento `none|slow-zoom`, transições `cut`/`fade` (fade só no último beat).
- **Áreas seguras:** reservar a faixa superior (interface do Reels/Stories) e a base
  (interface + legendas que a plataforma/CapCut possam sobrepor). No 9:16 nada de texto
  encostando nas bordas; manter o headline dentro do corpo da tela e o CTA acima do rodapé
  de interface. Não reservar uma banda fixa só para legenda queimada.
- **Sem áudio (política do projeto):** MP4 **sem faixa de áudio** (`-an`) e **roteiro de
  narração separado** em `04-legendas/`. O áudio é gerado fora do editor; a verificação da
  entrega usa `ffprobe` (0 streams de áudio).

## Regras de composição por tipo de cena

O `VideoRequest` monta cenas com `kind`, `surface`, `badge`, `headline` e, quando houver,
`highlightId` sobre a captura do produto:

| `kind` | `surface` | Papel | Regra de design |
| --- | --- | --- | --- |
| `hook-card` | `marca` | Gancho (abertura) | Card de marca em fundo `background`; badge curto no topo, headline grande em `textPrimary` (bold), subline em `textMuted`. Pergunta/provocação que espelha a dor. |
| `manager-agenda` | `manager-agenda` | Prova na interface | Captura real da rota (`/gestor/agenda`, `/booking/[salonId]`) com `highlightId` marcando o elemento em foco. Badge indica a área; headline descreve o que se vê. A UI do produto é a estrela — não cobrir com cartões. |
| `cta-card` | `marca` | Encerramento | Card de marca com headline de convite e subline com `marcasalao.com.br`. Sem aparência de botão/link clicável desenhado na imagem. |

- **Hierarquia:** badge (pequeno, caixa alta) → headline (grande, bold) → subline (muted).
  Um foco por cena; não competir com a captura do produto.
- **Acento:** usar `primary` (amarelo) com parcimônia — um destaque por cena no máximo —
  e `accent`/`secondary` apenas para estados e apoio. Texto sobre fundo escuro sempre em
  `textPrimary`.
- **Consistência:** mesma família tipográfica (Arial bold) em todas as cenas; o
  headerOverlay repete no topo de todo o vídeo para ancorar a marca.
- **Ritmo:** cenas curtas (4–6 s); hook no início, provas no meio, CTA no fim. Alinhar
  cortes ao conteúdo, não a uma grade fixa.

## Textos, legendas e narração (modo clean)

- **Textos gráficos editoriais** (headline, subline, badge, chips de status, CTA de
  endcard) fazem parte da arte e **permanecem** — não são legendas narrativas.
- **Sem legenda narrativa queimada** no MP4.
- **Sem SRT por padrão.** `.srt` só quando legendas forem solicitadas expressamente (ou em
  campanhas legadas); nesse caso usa-se o estilo ASS do token `components.subtitle.style`.
- **Roteiro de narração separado** em `04-legendas/` (TXT, por cena e tempos, PT-BR, pronto
  para ferramenta externa) — este é obrigatório no modo clean.
- **Nenhum** áudio no vídeo: sem faixa, sem narração embutida, sem música/SFX.
- Separar rigorosamente `caption`/`narrationText` (roteiro externo) e `postText`
  (texto de publicação por canal) — não se confundem nem se sobrescrevem. No modo clean,
  o `caption` das cenas serve de base para o roteiro de narração, não para queimar no vídeo.

## Divergência registrada — VIDEO CLEAN × fluxo legado (2026-11-27)

Há um conflito de documentos que fica **explicitamente registrado** aqui, sem alterar o
fluxo legado:

- `tenants/marca-salao/brand-kit.json` (`audioPolicy.requireSrt: true`) e
  `tenants/marca-salao/guardrails.json` (`audioPolicy.requireSrt: true` +
  `subtitleStyle` ASS) descrevem o **fluxo legado da fábrica**
  (`tools/preset_runner.py` / `tools/factory_cli.py`), que **ainda exige** legenda queimada
  e SRT.
- A **decisão canônica vigente** para as novas produções Marca Salão é **VIDEO CLEAN**
  (`docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md`): sem legenda narrativa
  queimada, sem SRT por padrão, narração em TXT separado.
- **Precedência:** para o caminho VideoRequest/Video Studio (produções novas), vale VIDEO
  CLEAN. O fluxo legado (`requireSrt`) **permanece válido e não é removido nem alterado**
  por este guia.
- Este `frame.md` **não** restabelece SRT obrigatório no modo clean; o token
  `components.subtitle.style` aplica-se apenas ao fluxo legado ou a legendas pedidas
  expressamente.

## Chamadas por rede (quando houver texto de publicação)

- **Facebook:** URL completa na legenda — "Acesse pelo link da descrição".
- **Instagram:** "Conheça o sistema — link na bio" **somente** com link da bio
  confirmado; caso contrário, usar "Conheça o Marca Salão".
- Nunca simular botão/adesivo de link clicável dentro do quadro.

## Arte de feed (companheiro, sistema separado)

A arte **estática** de feed é produzida no ComfyUI08 com identidade própria — **não** usar
a paleta escura do vídeo aqui:

- **Cores:** verde-petróleo `#073f40`, menta `#c8efe1`, papel `#f6faf7`, branco de mármore
  e **dourado discreto** (uso pontual). Texto branco só sobre a parede verde (contraste);
  no mármore claro, texto verde-petróleo escuro.
- **Logo:** monograma **MS** com tesoura em placa verde-petróleo, cantos arredondados,
  filete menta, ~15% da largura, no topo central; abaixo, "Marca Salão" em branco.
- **Tipografia:** sem serifa geométrica, pesada e arredondada, no título/benefícios/chamada
  (nunca serifada na chamada). Sem contorno escuro duro.
- **Formato:** quadrado compartilhado (mesma arte nas duas redes, CTA neutra
  "Conheça o Marca Salão") como padrão econômico; vertical/3 benefícios quando pedido.
- Regra vigente de produção/validação de arte: ComfyUI08 + guard de proveniência
  (`marcas/marcasalao/comfyui/marcasalao_media_guard.py`). Este guia não altera isso.

## Fazer / Não fazer

**Fazer**
- Mostrar o produto real; ancorar tudo em `marcasalao.com.br`.
- Manter contraste alto e legibilidade no 9:16 (áreas seguras respeitadas).
- Reutilizar tokens do `brand-kit.json` em vez de recriar cores.
- Entregar o roteiro de narração separado (`04-legendas/`).

**Não fazer**
- Não queimar legenda narrativa nem gerar SRT por padrão no modo clean.
- Não inserir áudio, música, narração ou SFX; não exportar com faixa de áudio.
- Não usar alegações proibidas pelos `guardrails.json` nem UI de pagamento/cobrança.
- Não usar "Meu Salão" na comunicação da marca Marca Salão.
- Não desenhar botão/adesivo de link clicável na imagem estática.
- Não misturar a paleta escura do vídeo com o teal/menta da arte de feed no mesmo quadro.
- Não remover nem reescrever as regras do fluxo legado que ainda exigem SRT.

## Adoção

- Em composições HyperFrames, adotar este arquivo como `frame.md` do projeto de vídeo e
  tratar o frontmatter como verdade de marca (hex, fontes, pesos, política de
  legendas/áudio) — layout é livre, brand não é.
- O `brand-kit.json` continua sendo o contrato de token consumido pela fábrica/Studio;
  este `frame.md` é a camada de **direção de design de vídeo** que se apoia nele.
- Ajustes de política (áudio, promessas, legendas) vêm de `guardrails.json` e da decisão
  `MKT-VIDEO-002`; em caso de divergência, vale a decisão canônica vigente (VIDEO CLEAN
  para novas produções; fluxo legado preservado).
