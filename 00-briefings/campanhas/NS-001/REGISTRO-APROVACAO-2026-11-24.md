# Registro de aprovação editorial — NS-001 (24/11/2026)

Natureza: registro de decisão real do titular. Este documento é o registro de aprovação exigido pelo passo 1 de [PLANO-CONTINUIDADE-PRODUCAO.md](PLANO-CONTINUIDADE-PRODUCAO.md) e pelas condições de entrada da Operação Resultado 02.

## Decisão

- **Aprovador:** titular do projeto (Jonatasbottaro), em sessão de 24/11/2026.
- **Data/hora do registro:** 24/11/2026, ~14:25 (America/Sao_Paulo); resposta explícita às perguntas de aprovação da Operação Resultado 02, nesta estação.
- **Veículo:** brief "OPERAÇÃO RESULTADO 02 — NS-001 — PRODUÇÃO AUDIOVISUAL REAL, EXPORTAÇÃO E VALIDAÇÃO" + resposta do titular à consulta de aprovação (opção "Aprovar pacote + produção").
- **Base aprovada:** pacote editorial do PR #32, branch `feat/ns-001-homologacao-editorial`, SHA `103b67ee3435147bea771cb72fe58ec49666f99d` (base `main` @ `bcabc00`). O PR não foi mesclado; a produção usa base explicitamente identificada em worktree isolada.

## Escopo aprovado (decisões do pacote, seção K)

| Decisão | Conteúdo | Estado |
| --- | --- | --- |
| 1 | Briefing v0.3 (`briefing.md`) | **APROVADO** |
| 2 | Hook recomendado H15 revisado: "Você consegue visualizar os agendamentos do seu salão com clareza?" | **APROVADO** |
| 3 | Roteiro de 7 cenas, 47,0 s (`storyboard-001.md`), **com as duas propostas de ajuste**: texto curto da cena 2 ("Informação espalhada: cada lugar mostra um pedaço do dia.") e narração da cena 5 em duas frases ("Abrindo o atendimento, aparecem o horário, o cliente e o profissional. Também o serviço, o preço e o status.") | **APROVADO** |
| 4 | Identidade visual **opção A** (identidade pública verde-petróleo/menta/branco, MS/tesoura nas artes; brand-kit como contrato de legendas/overlay; recorte exclui a sidebar "Meu Salão") | **APROVADO** |
| 5 | Preparação das capturas editoriais (fixture dedicada + plano de gravação do inventário) | **AUTORIZADO** |
| 6 | Canais: Instagram Reels, Facebook Reels, YouTube Shorts (perfis existentes) | **CONFIRMADO** |
| 7 | CTA/destino/bio/UTM por canal | **PENDENTE** (não bloqueia a peça de revisão; bloqueia publicação) |
| 8 | Textos de tela e narração do storyboard aprovado (com os ajustes da decisão 3) | **APROVADO** |
| 9 | Gravação e produção da peça de revisão (master 9:16 + três saídas + SRT + narração TXT + manifestos) | **AUTORIZADO** |

## Fixture editorial

- **Nome fictício do salão aprovado pelo titular: "Salão Harmonia"** (resposta explícita na mesma sessão).
- Demais requisitos conforme [INVENTARIO-CAPTURAS-E-PLANO-GRAVACAO.md](INVENTARIO-CAPTURAS-E-PLANO-GRAVACAO.md) §2: namespace próprio, pessoas fictícias neutras, campos completos, preços plausíveis (R$ 40–180), estados Pendente/Confirmado/Concluído/Cancelado, somente Firestore Emulator, produto intacto.

## Limites desta aprovação

- **Publicação, agendamento e rascunhos em contas externas: NÃO autorizados** (decisão separada e posterior, sempre manual).
- Decisão 7 (CTA/destino/bio/UTM) permanece pendente; a peça de revisão usa a CTA neutra aprovada do storyboard ("Conheça a agenda do Marca Salão." + domínio), sem orientação de link por canal na imagem.
- Nome público oficial do produto ("Marca Salão" × "Meu Salão") não foi decidido; o recorte da gravação exclui a sidebar, conforme opção A. Nenhum arquivo de marca ou produto é alterado.
- A aprovação técnica de pacotes/render não se confunde com esta aprovação editorial; a peça produzida é **material de revisão**, não campanha aprovada para publicação.
- Extração de hex/tipografia exatos da arte aprovada `marcas/marcasalao/posts/2026-11-01-troca-profissional-combinado/arte-compartilhada-quadrado.png` autorizada como parte da decisão 4 (opção A, pendência 2 da auditoria de identidade).

## Rastreabilidade

- Documentos originais do pacote preservados sem edição (as propostas de ajuste aprovadas são aplicadas nos artefatos de produção: VideoRequest, SRT e narração efetivos).
- Operação executada na branch `feat/ns-001-resultado02-producao` (worktree `.workspace/worktrees/ns001-resultado02`), a partir de `103b67e`.
- Estados editoriais anteriores (briefing em validação; hook/roteiro rascunho) são substituídos por este registro a partir da data acima.