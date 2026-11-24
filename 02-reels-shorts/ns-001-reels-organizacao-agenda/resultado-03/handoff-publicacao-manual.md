# Handoff de publicação manual — NS-001-P001 (v1) — ESTADO: BLOQUEADO / PENDENTE

Operação Resultado 03 · 24/11/2026 · checkout principal `main` @ `bcabc00`.
**Este pacote NÃO está liberado para publicação.** Nenhuma publicação, agendamento ou rascunho em conta externa foi criado. Publicação é ato manual e separado do titular, após as decisões abaixo.

Mecanismo reutilizado (sem ferramenta nova): `05-mensuracao/GUIA-MENSURACAO-NS001-NS002.md`, `06-validacao-destinos/GUIA-VALIDACAO-DESTINOS-NS001-NS002.md`, `04-legendas/pacotes-publicacao/` (publish_pack), `registro-publicacao.csv` do piloto, e `ADAPTACAO-CANAIS-E-UTM.md` / `REGISTRO-APROVACAO-2026-11-24.md` / `editorial-v1/INDICE-ENTREGA.md` da branch `feat/ns-001-resultado02-producao` @ `5412db4` (worktree `.workspace/worktrees/ns001-resultado02`, **não integrada na main**).

## 1. Identificador e mídia audiovisual

- Peça: **NS-001-P001**, variante **v1** (peça de revisão editorial, 7 cenas, 47,0 s).
- Aprovação editorial de produção: registrada em 24/11/2026 (`REGISTRO-APROVACAO-2026-11-24.md`, branch acima). **Revisão humana do titular e aprovação para publicação: pendentes.**
- Master 9:16 compartilhado pelos 3 destinos (mesmo SHA-256): `78017b98a6f3268b0b25dec7c64106b809a5192360e3acd3a4457b35f2e7816d`.
- Arquivos (locais da worktree; MP4 não versionado por política `*.mp4`):
  - instagram-reels-video: `…/entrega-v1/instagram-reels-video/execution-v1-feab3b6e…-primary-output.mp4`
  - facebook-reels-video: `…/entrega-v1/facebook-reels-video/execution-v1-148faea9…-primary-output.mp4`
  - youtube-shorts: `…/entrega-v1/youtube-shorts/execution-v1-2fda4d1d…-primary-output.mp4`
- FFprobe (conferido nesta estação, ffprobe portátil): 1080×1920, 30/1 fps, h264/yuv420p, 47.0 s, **0 faixas de áudio** nos 3.
- SRT final: `04-legendas/ns001_roteiro_001.srt` (branch) sha `d75d62d3…`; narração: `04-legendas/ns001_roteiro_001_narracao.txt` (branch) sha `e317ff64…`.
- Capa de revisão: `entrega-v1/capa-revisao.png` (local). Capa publicitária por rede: fora do escopo aprovado.

## 2. Textos por canal (PROPOSTAS pendentes — de ADAPTACAO-CANAIS-E-UTM.md, não aprovadas para publicação)

- **Instagram Reels** — legenda proposta: "Você consegue visualizar os agendamentos do seu salão com clareza? Na agenda do Marca Salão, o registro do dia, da semana e do mês fica reunido: filtros por profissional e status, busca por cliente e os dados de cada atendimento. Conheça o sistema — link na bio. #MarcaSalão #AgendaDoSalão #GestãoDeSalão". CTA: "Conheça a agenda do Marca Salão." + "link na bio" **somente se o link externo do perfil estiver conferido na data da publicação**. URL em legenda não é clicável.
- **Facebook Reels** — legenda proposta: mesma mensagem + "Acesse pelo link da descrição: <URL completa com UTM>". CTA neutra na peça; URL completa na legenda conforme AGENTS.md.
- **YouTube Shorts** — descrição proposta: "Veja como a agenda do Marca Salão reúne os agendamentos do dia, da semana e do mês, com filtros por profissional e status, busca por cliente e detalhes de cada atendimento. Conheça o sistema: <URL com UTM>". #Shorts #MarcaSalão #AgendaDoSalão. Conferir mecanismo de link vigente para Shorts na data da publicação.

## 3. URL final e UTM (CANDIDATAS — pendente_de_decisao, decisão 7)

Base candidata `https://marcasalao.com.br` (oficial documentado). `/gestor` NÃO é destino de campanha.

| Canal | utm_source | utm_medium | utm_campaign | utm_content |
| --- | --- | --- | --- | --- |
| instagram | instagram | reels | ns-001 | ns-001-p001-reels-v1 |
| facebook | facebook | reels | ns-001 | ns-001-p001-fbreels-v1 |
| youtube | youtube | shorts | ns-001 | ns-001-p001-shorts-v1 |

Nenhuma UTM/destino entra como confirmado sem decisão escrita do titular. Linhas da `matriz-utm-consolidada.csv` (pacote técnico saas-demo) permanecem intactas.

## 4. Checklist de postagem (a cumprir SOMENTE após liberação)

- [ ] Decisão 7 assinada: CTA/destino/bio/UTM por canal.
- [ ] Teste de aceite do destino `aprovado` (hoje **reprovado** — ver teste-aceite-destino.csv) + confirmação escrita do titular.
- [ ] Nome público oficial do produto resolvido (Marca Salão × Meu Salão); hoje o site exibe Meu Salão.
- [ ] Revisão humana do titular da peça v1 concluída e aprovada para publicação.
- [ ] Link externo do perfil Instagram conferido na data (para "link na bio").
- [ ] Mecanismo de link do YouTube Shorts conferido na data.
- [ ] Autorização específica de publicação manual do titular (separada da aprovação editorial).
- [ ] Vídeo sem áudio + SRT + narração TXT conferidos (já conferidos nesta estação).
- [ ] Nenhum dado pessoal real (fixture Salão Harmonia fictícia — ok).

## 5. Orientação de publicação

Manual, pelo titular, nas contas oficiais. Não usar API/Postiz para publicar/agendar nesta operação. Não criar anúncios. Não alterar posts antigos. Não publicar conteúdo de outro tenant. Após publicar, preencher `data_hora_publicacao` (ISO 8601 com fuso) e `link_publico` reais no registro; nunca inventar.

## 6. Campos de registro do link público (modelo-registro-publicacoes.csv)

`id_peca, campanha, canal, formato, variante, posicao_cta, data_hora_publicacao, link_publico, status_destino, url_destino, url_parametrizada, utm_source, utm_medium, utm_campaign, utm_content` — preenchidos hoje apenas até `posicao_cta`; demais vazios/pendentes (ver registro-publicacoes.csv desta pasta). Estado atual: **NÃO PUBLICADA** nos 3 canais.

## 7. Bloqueios ativos (impedem publicação agora)

1. Destino reprovado no teste renderizado (marca Meu Salão + claims proibidos/sem evidência + jornada incompatível com o CTA).
2. Decisão 7 (CTA/destino/bio/UTM) pendente.
3. Nome público oficial do produto não decidido.
4. Revisão humana da peça v1 pendente; peça é material de revisão, não campanha aprovada para publicação.
5. Autorização específica de publicação manual não concedida.
6. Branch de produção não integrada na main (registro e mídia vivem na worktree/branch).