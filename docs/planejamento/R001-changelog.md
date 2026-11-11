# R001 — changelog da revisão independente (2026-11-07)

Escopo: apenas `docs/planejamento/R001-formatos-sociais.md`. Nenhum código, schema, exemplo ou teste alterado; **nenhuma medida do documento mudou** — contagens de registro, revisões de perfil, fixtures, testes e portões continuam os do checkpoint R001-05.

Um revisor sem o contexto da conversa leu as 876 linhas do documento contra `rules.ts`, `catalog.ts`, os exemplos, os testes e o histórico. Onze achados: **três já estavam resolvidos** e **oito procediam**, corrigidos em `e8e0f60` (9 linhas) e `cfe7a8f` (+2 linhas). Os números de linha abaixo se referem ao documento como está em `cfe7a8f` (878 linhas).

| # | Achado | Correção |
| --- | --- | --- |
| 1 | D-34 chamava o custo antigo de upload de "número de **2024**" — nenhuma fonte desta etapa sustenta essa data | passa a citar a mudança "from approximately 1600 units to approximately 100 units" de **2025-12-04**, como já registram `S-YT-QUOTA` e `PN-YT-02` (linha 854) |
| 2 | Ponteiros `platform/README.md:11` desatualizados em dois lugares: a citação "primeiro consumidor" migrou para a linha 12 quando a terceira fatia entrou na linha 10 | ambos recontados para `:12`, com o recontamento declarado no texto; `:17-19` continua correto (linhas 263 e 824) |
| 3 | Referência de política de marca caía em `AGENTS.md:48`, linha da seção do **Multitrack Hub** | arte quadrada compartilhada passa a ser `AGENTS.md:52-54`, com `:39` rotulado como a parte de Stories (linha 42) |
| 4 | Verbo inglês com clítico português em regra promovida ("então **promote-se** o teto estrito") | "promove-se" (linha 104) |
| 5 | Concordância e grafia no cabeçalho de capacidade observada ("Catálogo concorrente **identificada**", "**triáde**") | "identificado" / "tríade" (linha 43) |
| 6 | D-30 dizia "Sem a string **erra** no registro" — a frase que explica por que a tradução defeituosa fica guardada | "string errada" (linha 850) |
| 7 | Célula do checkpoint R001-03 com duas palavras sem acento no meio de texto acentuado | "continuam **válidos**" e "três **suítes** de unidade" (linha 809) |
| 8 | §16 afirmava "Verificado com `grep -c` no arquivo anexado" sem caminho, contagens nem aviso de que o anexo não está no clone | medição real registrada: 17 932 bytes, 185 linhas, `720` = 0, `meta.json` = 0, `story_reel_vertical` = 2, `youtube_horizontal` = 2, linha 28 do anexo com os quatro defaults — com a limitação de reproduzibilidade (linha 862) |

## Achados verificados e descartados

- A distinção entre `P-FB-01` **estreitada** e `P-HELP-01` **revalidada sem número** já existia na linha 160 (corrigida antes da leitura do revisor).
- As linhas de `R-IG-02`/`R-IG-03` em §2.1 já declaram "**não existe no registro**" (entraram em `299849e`); nenhum dos dois IDs existe em `rules.ts`.
- O particípio solto em §11 já tinha virado "nem recomendações nem defaults internos viraram limites oficiais".

## Verificação depois das edições

Node **v22.23.2** / npm **10.9.8**, em `platform/`, com código e lockfile inalterados: `clean`, `typecheck` e `build` exit 0 · `npm test` **510 testes / 510 pass / 0 fail / 0 skipped** · `npm run test:contracts` **288 / 288 / 0 fail** · `npm ls --omit=dev --all` com a árvore vazia · `git diff --check` limpo. As quatro CLIs exit 0, e os fixtures `facebook-reels-video` e `youtube-shorts-studio-upload` permanecem idênticos byte a byte ao stdout fresco (`cmp`).

Nada foi enviado para `main`, nenhum PR aberto, nenhum deploy, nenhuma mídia gerada.
