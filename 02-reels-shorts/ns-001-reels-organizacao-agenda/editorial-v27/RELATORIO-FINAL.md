# NS-001 — Studio Bella — v2.7 — Relatório final

Pedido: `NS-001-P001-Studio-Bella-v2.7` · branch `feat/ns001-studio-bella-v2` · PR #33 (rascunho, sem merge) · publicação não autorizada.

## A. Diagnóstico (v2.6 → v2.7)

- v2.6: interface pequena e centralizada, cenas 1/2 com os mesmos cartões invertidos, sem hierarquia, aparência de screenshot estático; fonte de captura 665×605 limitava o tamanho do texto.
- v2.7 separa **evidência do produto** (recorte proporcional da captura real, sem deformação) de **destaque editorial** (tipografia grande de marca com valores verificados, sem imitar a UI nativa).

## B. Implementação

- Motor reutilizável `tools/editorial_compose.py` (FFmpeg filter-graph, determinístico, sem dependências novas): componentes `product-context`, `product-proof`, `status-sequence`, `brand-endcard`, `static-art`; validação de manifesto com proveniência obrigatória (hash, região, valor verificado), escopos por cliente e áreas seguras.
- Manifesto versionado `campanha-v27.editorial.json` + fontes versionadas em `fontes/` (captura real, artes aprovadas v2.4, snapshot de acessibilidade).
- Cena 1 (0–6s): contexto da agenda semanal (2,8s) → destaque 09:00 · Mechas e Iluminação · Confirmado (3,4s), com cartão real de fundo.
- Cena 2 (6–12s): sequência Confirmado → Concluído → No-show (2s cada), cada estado com o cartão real correspondente — visualmente distinta da cena 1.
- Cena 3 (12–17s) e cena 4 (17–22s): artes aprovadas v2.4 preservadas byte a byte.
- Movimento assado na mídia: revelação suave 0.35s, deriva controlada 6px, fades de borda 0.25s; `motionIntent: none` no pedido; sem cliques simulados, sem zoom que corte informação.
- Correção consolidada da prévia: faixa de marca `#025C5D` (y 1520–1700) sob a banda de legendas nas cenas editoriais — o texto branco do renderizador tinha contraste insuficiente sobre o fundo claro em 360×640. Cenas aprovadas 3/4 não foram tocadas.
- Cores: primária `#025C5D` (moda das cores escuras do logo oficial; sem hex oficial fixado), fundo `#EDFCF7`, funcionais amostradas dos cartões reais.

## C. Validação audiovisual

- Master e 3 perfis: 1080×1920, 30fps, 22s, h264, yuv420p, **0 faixas de áudio** (FFprobe).
- Correlação frames×cenas (região de conteúdo, sem banda de legenda): cena1 0.9995 · cena2 0.9995 · cena3 0.9976 · cena4 0.9998.
- Inspeção por OCR pt-BR em 16 frames (1,3,5,7,9,11,13,15,18,20s + limites 5.9/6.1/11.9/12.1/16.9/17.1): mapeamento correto, hierarquia legível, progressão de status correta, cortes limpos.
- Legibilidade 360×640: destaques e legendas recuperáveis por OCR após a faixa de contraste.
- Áreas seguras: 0 violações nos 3 perfis; sobreposição de QC nunca presente no MP4 (varredura de pixels).
- MP4 dos 3 perfis com bytes idênticos: `86fe2a527ce6c6e4c65243346c559ff645c929dc4c3ab45ca16c5b25e6c46aae`.

## D. Testes (A–J)

- `tools/tests/test_editorial_compose.py` (fast, 19 testes): proporção (A), proveniência/hash/valor (B), isolamento por escopo (C), legendas sem duplicação da CTA impressa (D), mapeamento cena→mídia (E), áreas seguras + captionBand (F), cenas distintas (G), portabilidade sem caminhos de máquina (I), estilo canônico de legenda (J).
- `tools/tests/test_editorial_compose_render.py` (render, 3 testes): reprodutibilidade byte-idêntica (H), exportação real sem áudio (J), campanha fictícia completa com áreas seguras (G/prova de reutilização).
- Gate smoke: 405/407 aprovados; 1 falha pré-existente de ambiente (`test_publish_pack.test_08_resolve_workspace_root` espera `.workspace` da worktree, mas a ferramenta resolve o da main) e 1 skip. Gate fast completo: mesmas causas ambientais (`test_studio_connections` exige build da platform ausente na worktree); nenhuma falha atribuível às mudanças v2.7.
- Prova de reutilização: fixture fictícia **Marca Exemplo** (`tools/tests/fixtures/editorial/`), paleta/logo/captura próprios, compõe os mesmos componentes apenas por configuração; evidência sanitizada em `prova-reutilizacao/`.

## E. Entrega (pacote portátil, fora do Git)

Em `<RAIZ>/.workspace/tmp/ns001-studio-bella-v27/entrega/`:

- `NS-001-Studio-Bella-v2.7-{instagram,facebook,youtube}.mp4`
- `review.html` (player com abas por perfil e marcadores de cena)
- `ns001_roteiro_001_v27_studio_bella.srt` e `..._narracao.txt`
- `NS-001-Studio-Bella-v2.7-final.zip`
- `qc/relatorio-qc.json` (FFprobe, checksums, correlações), `qc/composition-report.json` (geometria/proveniência/áreas seguras, sanitizado), `qc/checksums.txt`, `qc/frames/` (360×640), `qc/areas-seguras/` (51 prévias), `qc/verificacao-areas-seguras.md`, `qc/comparacao-v26-v27.md`
- Pastas por perfil com manifestos de entrega do pipeline.

Versionados neste diretório: manifesto, pedido VideoRequest, fontes, guia de reutilização (9 itens), prova de reutilização e este relatório. SRT/narração em `04-legendas/`.

## F. Limitações

- Verificação visual humana do MP4 final pendente (titular); OCR/pixels são proxies objetivos, não aprovação editorial.
- Margens de área segura são aproximações documentadas (Meta Reels ads / YouTube Shorts), não medições da interface publicada.
- "Mariana Silva" aparece pequena na arte aprovada da cena 3 (preservada como aprovada); a mensagem é transmitida pela legenda/narração.
- Dados da demonstração Studio Bella; nenhuma publicação, agendamento ou alteração de dados reais.