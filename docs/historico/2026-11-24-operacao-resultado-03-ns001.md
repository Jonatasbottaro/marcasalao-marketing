# Operação Resultado 03 — NS-001 · distribuição manual e mensuração real — 24/11/2026

Base: `main` @ `bcabc00` (sincronizada com origin no início da operação). Natureza: verificação de
pré-condições + teste de destino renderizado + conferência do pacote de revisão + preparação de
handoff manual + registro de estado. **Nenhuma publicação, agendamento, rascunho externo, anúncio ou
alteração de site foi realizada.**

Pacote completo (relatório, handoff, registros CSV e screenshots):
[`02-reels-shorts/ns-001-reels-organizacao-agenda/resultado-03/`](../../02-reels-shorts/ns-001-reels-organizacao-agenda/resultado-03/RELATORIO.md).

## Fatos registrados

- **Gate de pré-condições reprovado para publicação.** A Operação Resultado 02 obteve aprovação
  editorial explícita do titular em 24/11/2026 e produziu vídeo real de revisão (47 s, 0 áudio) na
  branch `feat/ns-001-resultado02-producao` @ `5412db4` (worktree `.workspace/worktrees/ns001-resultado02`,
  **não integrada na main**). Essa aprovação cobre produção/revisão, não publicação; a decisão 7
  (CTA/destino/bio/UTM por canal) e a revisão humana permanecem pendentes.
- **Destino reprovado no teste de aceite renderizado** (desktop + celular, leitura, sem UTM de teste em
  produção): `https://marcasalao.com.br` carrega 200 sem redirects, mas exibe a marca **Meu Salão**
  (não Marca Salão), jornada de marketplace/assinatura paga incompatível com o CTA
  "Conheça a agenda do Marca Salão", e claims proibidos/sem evidência (+5.000 salões,
  100 mil agendamentos/mês, +40% faturamento, 1.1★ App Store, "reduza no-shows com confirmações
  automáticas por WhatsApp", "lembretes automáticos", depoimentos "faltas −60%"). Passo 4 do guia de
  destinos (ação × CTA), pendente na Resultado 02 (só GET), foi avaliado por renderização e reprovado.
  Registrado como **bloqueio de publicação**; site não alterado, destino não substituído.
- **Pacote de revisão conferido:** 3 MP4 (instagram-reels-video, facebook-reels-video, youtube-shorts),
  1080×1920@30, h264/yuv420p, 47,0 s, **0 faixas de áudio** (ffprobe portátil); SHA-256 dos três
  idêntico ao índice (`78017b98…`); SRT/narração versionados na branch; fixture "Salão Harmonia"
  fictícia, sem dados pessoais. MP4 não versionado (política `*.mp4`), presente só nesta estação.
- **Publicação: nenhuma.** Registro de publicações com 3 linhas (IG/FB Reels, YT Shorts), todas não
  publicadas (data/link vazios), `status_destino=pendente_de_decisao`. Métricas `nao_coletado`;
  linha de base indisponível; cliques de rede ≠ acessos UTM do site; bio compartilhada sem atribuição
  por peça; analytics do site não configurado.
- **Recomendação única (Fase 7): C — ajustar CTA ou destino antes da próxima campanha.**
  NS-002 não iniciada. Ciclo **PENDENTE / NÃO CONCLUÍDO** até publicação manual efetiva do titular.

## Decisões que permanecem com o titular

Nome público oficial do produto (Marca Salão × Meu Salão); coerência/claims do destino; decisão 7
(CTA/destino/bio/UTM); conferência da bio do Instagram e do mecanismo de link do Shorts na data;
revisão humana da peça v1; autorização específica de publicação manual; integração da branch de
produção por fluxo próprio (PR/merge).

## Versionamento

Registros permanentes versionados em `02-reels-shorts/ns-001-reels-organizacao-agenda/resultado-03/`
e commitados/enviados na `main` por autorização explícita do titular em 24/11/2026. Cópia local de
trabalho em `.workspace/logs/operacao-resultado-03-ns001/` (não sincroniza).

## Adendo — integração da branch de produção (24/11/2026)

Por autorização explícita do titular ("pode seguir com merge branch"), a branch
`feat/ns-001-resultado02-producao` (@ `5412db4`, inclui homologação `103b67e`) foi integrada na `main`
pelo merge **`7e9c41c`** e enviada a `origin/main`. Traz o pacote de aprovação editorial, storyboard,
SRT/narração NS-001, `editorial-v1/` e a correção TC-01 de estilo de legendas em `tools/render_local.py`
(suíte de render da branch: 107 testes OK). A integração não altera o gate: destino reprovado,
decisão 7, identidade pública, revisão humana e autorização de publicação manual seguem pendentes;
ciclo **PENDENTE**.