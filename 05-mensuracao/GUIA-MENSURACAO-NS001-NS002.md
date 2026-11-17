# Guia Operacional — Mensuração das Campanhas NS-001 e NS-002

## 1. Contexto e escopo

Este kit operacional permite registrar cada peça das campanhas NS-001 e NS-002, preparar o link de cada posicionamento com destino clicável confirmado, coletar resultados em momentos definidos e comparar publicações com critérios consistentes. Entrega modelos preenchíveis (CSV) e um ensaio local com dados fictícios.

### Campanhas cobertas

| Campanha | Nome | Status editorial | Material de referência |
| --- | --- | --- | --- |
| NS-001 | Organização e visibilidade da agenda | Em validação (não aprovada para produção) | `00-briefings/campanhas/NS-001/briefing.md`, `02-hooks/campanhas/NS-001/hooks.md`, `03-roteiros/campanhas/NS-001/roteiro-001.md` |
| NS-002 | Agendamento online no Marca Salão | Em validação — aprovação editorial parcial (2026-11-16) para hooks e roteiro; capturas, gravação e publicação bloqueadas | `00-briefings/campanhas/NS-002/briefing.md` (branch `docs/ns-002-agendamento-online`), `02-hooks/campanhas/NS-002/hooks.md`, `03-roteiros/campanhas/NS-002/roteiro-001.md` |

### Canais, CTAs e destinos pendentes

Os seguintes itens aguardam aprovação do titular e devem ser tratados como pendentes até confirmação escrita:
- Canais efetivamente publicados por campanha.
- CTA por canal (link na bio, sticker de link, URL na descrição).
- Destino clicável confirmado e link externo cadastrado no perfil.
- Mecanismo de rastreamento (utm, parâmetros de destino, pixel).

Não preencher campos que dependam dessas decisões com valores assumidos. Deixe vazios e registre como pendente.

> **Limite deste escopo:** este kit trata de documentação, modelos e validação local com dados fictícios. Publicação de campanhas, acesso a contas reais e configuração de analytics ficam para etapas próprias, sob autorização do titular.

## 2. Convenção de parâmetros UTM

Reaproveite a convenção abaixo para todas as peças das campanhas NS-001 e NS-002.

| Parâmetro | Valor | Regras de preenchimento |
| --- | --- | --- |
| `utm_source` | rede social | `instagram`, `facebook`, `youtube`, `tiktok`, `whatsapp`. Minúsculo, sem acentos. |
| `utm_medium` | formato/posicionamento | `reels`, `stories`, `shorts`, `status`, `feed`. Minúsculo, sem acentos. |
| `utm_campaign` | código da campanha | `ns-001` ou `ns-002`. Minúsculo, sem acentos. |
| `utm_content` | identificador da peça | `<id_peca>-<variante>`, ex.: `ns-001-p001-reels-v1`. Reprodutível e estável. |

### Exemplo fictício

Peça `NS-001-P001`, variante Reels, campanha NS-001:

```
https://marcaselao.com.br?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1
```

### Como distinguir duas peças da mesma campanha sem renomear as tags

Use `utm_content` com o identificador estável da peça (`id_peca`) e a variante. Dessa forma:
- `utm_source`, `utm_medium` e `utm_campaign` permanecem iguais para todas as peças da campanha (agrupam por campanha/rede/formato).
- `utm_content` carrega `id_peca` + `variante`, diferenciando cada peça individualmente sem alterar as outras três tags.

Exemplo: duas peças Reels da NS-001:
- `utm_content=ns-001-p001-reels-v1`
- `utm_content=ns-001-p002-reels-v1`

## 3. Registro de publicações

Preencha uma linha por peça publicada (ou planejada) no modelo `modelo-registro-publicacoes.csv`.

### Colunas

| Coluna | Obrigatório | Descrição |
| --- | --- | --- |
| `id_peca` | Sim | Identificador estável da peça, formato `<CAMPANHA>-P<NNN>` (ex.: `NS-001-P001`). Não reutilizar entre campanhas. |
| `campanha` | Sim | `ns-001` ou `ns-002`. |
| `canal` | Sim | `instagram`, `facebook`, `youtube`, `tiktok`, `whatsapp`. |
| `formato` | Sim | `reels`, `stories`, `shorts`, `status`, `feed`. |
| `variante` | Não | Variante da arte/legenda dentro do mesmo canal e formato (ex.: `v1`, `v2`). Vazio se não houver. |
| `posicao_cta` | Sim | Onde o CTA aparece: `legenda`, `bio`, `sticker`, `descricao`, `nenhum`. |
| `data_hora_publicacao` | Sim | Data e hora de publicação com fuso, ISO 8601 (ex.: `2026-11-20T10:00:00-03:00`). |
| `link_publico` | Não | Link público da postagem na rede (quando disponível). |
| `status_destino` | Sim | `confirmado`, `pendente_de_decisao`, `sem_destino_clicavel`. |
| `url_destino` | Não | URL de destino. Vazio enquanto depender de decisão não tomada. |
| `url_parametrizada` | Não | URL com parâmetros UTM. Vazio enquanto `url_destino` estiver vazio. |
| `utm_source` | Não | Preencher apenas se houver link clicável confirmado. |
| `utm_medium` | Não | Idem. |
| `utm_campaign` | Não | Idem. |
| `utm_content` | Não | Idem. Deve conter `id_peca` + variante. |

### Regras de preenchimento

- Deixe `url_destino`, `url_parametrizada` e os campos UTM vazios enquanto o destino clicável depender de decisão do titular. Não invente valores.
- Quando o destino for confirmado, preencha `url_destino`, gere `url_parametrizada` acrescida dos UTM e preencha `utm_source` a `utm_content`.
- `status_destino` é `sem_destino_clicavel` para peças sem link (ex.: Stories sem sticker de link autorizado, peça com CTA apenas de texto).
- Um mesmo `id_peca` não se repete no arquivo.

## 4. Casos de atribuição

### 4.1 Link direto

Peça com URL de destino própria e clicável confirmada.

- Preencha `url_destino` com o destino oficial (ex.: `https://marcaselao.com.br`).
- Preencha `url_parametrizada` com os parâmetros UTM.
- `status_destino = confirmado`.
- Cliques são atribuídos à peça pelo parâmetro `utm_content` (identifica a peça de forma estável).
- Acessos identificados por UTM no site (analytics do site) são distintos de cliques reportados pela rede; registre cada origem no seu campo `*_fonte` apropriado.

### 4.2 CTA que remete a link compartilhado na bio (bio/perfil compartilhado)

Peça cujo CTA orienta "link na bio" e o perfil tem um único link externo compartilhado por várias peças.

- Registre o URL do link cadastrado na bio/perfil e os parâmetros UTM efetivamente usados naquele link, quando confirmados.
- Preencha `url_destino` com o destino do link na bio somente se estiver confirmado.
- Preencha `url_parametrizada` com os UTM da peça.
- `status_destino = confirmado` se o link da bio estiver confirmado; caso contrário, `pendente_de_decisao`.
- **Atribuição do clique:** em um link de bio compartilhado, atribua o clique ao nível que a evidência sustenta. Se a rede não separar cliques por peça que apontam para o mesmo link da bio, registre a medição no nível da bio/perfil, não de cada peça. Deixe a atribuição por peça indisponível (`cliques_status = indisponível`, valor vazio) enquanto a fonte não identificar qual peça originou o clique.
- **Diferencie:** cliques reportados pela rede (painel nativo/insights da rede social no link da bio ou sticker) são distintos de acessos identificados por UTM no site (analytics do site). Não confunda um com o outro nem some valores de origens diferentes.

### 4.3 Peça sem destino clicável

Peça com CTA de texto apenas (ex.: "Conheça a agenda do Marca Salão" sem link), ou com botão desenhado em imagem estática que não gera clique.

- Deixe `url_destino`, `url_parametrizada` e os campos UTM vazios.
- `status_destino = sem_destino_clicavel`.
- Não registre cliques de destino para essa peça (não há mecanismo de rastreamento).

## 5. Registro de métricas

Preencha uma linha por combinação de publicação + janela de coleta no modelo `modelo-registro-metricas.csv`.

### Janelas iniciais

Use como janelas padrão de coleta:
- **24 horas** após a publicação.
- **7 dias** após a publicação.

Outras janelas podem ser adicionadas desde que estejam definidas antes da coleta.

### Coleta fora da janela definida

Se uma coleta for feita fora da janela planejada (antes de 24h ou depois de 7d, por exemplo), registre o horário real em `data_hora_coleta` (ISO 8601 com fuso) e anote em `observacoes` que a coleta ocorreu fora da janela. Não compare essa linha como se estivesse dentro da janela; use apenas para registro histórico e nunca misture com linhas da janela padrão na comparação direta.

### Colunas

| Coluna | Obrigatório | Descrição |
| --- | --- | --- |
| `id_publicacao` | Sim | `id_peca` da publicação a que se refere a coleta. |
| `janela` | Sim | `24h` ou `7d`. |
| `data_hora_coleta` | Sim | Data e hora da coleta com fuso, ISO 8601. |
| `fonte_dado` | Sim | Origem do dado (ex.: `instagram-insights`, `facebook-insights`, `youtube-studio`, `postiz`, `planilha-manual`). |
| `alcance` | Não | Número de contas únicas alcançadas, se a fonte disponibilizar. |
| `alcance_status` | Não | `medido`, `nao_coletado` ou `indisponivel`. |
| `alcance_fonte` | Não | Fonte específica do alcance (mesma de `fonte_dado` ou mais detalhada). |
| `visualizacoes` | Não | Número de visualizações, se a fonte disponibilizar. |
| `visualizacoes_status` | Não | `medido`, `nao_coletado` ou `indisponivel`. |
| `visualizacoes_fonte` | Não | Fonte específica das visualizações. |
| `interacoes` | Não | Número de interações (curtidas, comentários, compartilhamentos, salvamentos), se a fonte disponibilizar. |
| `interacoes_status` | Não | `medido`, `nao_coletado` ou `indisponivel`. |
| `interacoes_fonte` | Não | Fonte específica das interações. |
| `cliques` | Não | Número de cliques no link/destino, se a fonte disponibilizar. |
| `cliques_status` | Não | `medido`, `nao_coletado` ou `indisponivel`. |
| `cliques_fonte` | Não | Fonte específica dos cliques. |
| `formula_comparacao` | Não | Fórmula de comparação apenas se numerador e base estiverem definidos (ex.: `CTR = cliques / alcance`). Vazio caso contrário. |
| `observacoes` | Não | Observações sobre a coleta, limitações da fonte ou pendências. |

### Como diferenciar zero medido, dado não coletado e métrica indisponível

| Situação | Preenchimento |
| --- | --- |
| **Zero medido** | A fonte retornou 0 para a métrica. Preencha o valor `0` e o status `medido`. |
| **Dado ainda não coletado** | A coleta ainda não foi feita naquele momento. Deixe o valor vazio e o status `nao_coletado`. |
| **Métrica indisponível** | A fonte não disponibiliza essa métrica para o formato/canal. Deixe o valor vazio e o status `indisponivel`, e registre o motivo em `observacoes`. |

### Como comparar resultados na mesma janela

Para comparar duas peças, use apenas linhas com a mesma `janela` (ex.: ambas `24h`). Mantenha o nome e a definição da métrica conforme a fonte utilizada (não renomeie métricas entre fontes diferentes). Inclua `formula_comparacao` apenas quando o numerador e a base estiverem definidos para ambas as peças.

Exemplo: `CTR = cliques / alcance` exige que ambas as peças tenham `cliques` e `alcance` medidos **e** que `alcance > 0`. Se o alcance for zero, vazio ou indisponível em qualquer uma das peças, não calcule a comparação e deixe `formula_comparacao` vazio. Não declare comparação válida quando a outra peça não tem os dados necessários na mesma janela.

## 6. Onde cada dado vem de

### Dados do canal (disponíveis na rede social)

- Alcance, visualizações, interações (quando a plataforma disponibiliza para o formato).
- Cliques em link na bio ou sticker (quando a plataforma reporta).
- Fonte: painel nativo de cada rede ou ferramenta de gestão de mídia confirmada.

### Dados que exigiriam medição no site

- Conversões após o clique (preenchimento de formulário, solicitação de demonstração).
- Tempo de sessão, páginas visitadas, eventos de conversão.
- Fonte: analytics do site (ex.: Google Analytics, Meta Pixel) — **não configurada neste escopo**.

### Cliques por rede vs. acessos por UTM no site

Cliques reportados pela rede (ex.: `instagram-insights` no link da bio ou sticker) são distintos de acessos identificados por UTM no site (analytics do site). São origens distintas: registre cada uma no seu campo `*_fonte` apropriado e não some valores de origens diferentes.

### Dependências pendentes

Se não houver medição confirmada para uma conversão, registre a dependência em `observacoes` e deixe os campos de métrica relacionados como `nao_coletado` ou `indisponivel`, conforme o caso. Não assuma conversão a partir de clique.

## 7. Linha de base

Trate as primeiras publicações comparáveis (mesmo canal, mesmo formato, mesma janela) como **candidatas a estabelecer a linha de base**. Não defina metas numéricas a partir de uma única coleta. Preserve as métricas e metas que o projeto já tiver aprovado; se não houver, registre "linha de base ainda não disponível".

## 8. Ensaio local (dados fictícios)

O ensaio valida que os modelos podem ser preenchidos seguindo o guia, sem uso de contas reais. Os arquivos de exemplo estão em:
- `ensaio-registro-publicacoes.csv` — duas publicações fictícias (uma com link direto, outra com CTA para a bio).
- `ensaio-registro-metricas.csv` — coleta de 24h e 7d para cada uma, incluindo zero medido e métrica indisponível.

Validação feita:
- As linhas de métricas apontam para a publicação correta via `id_publicacao` = `id_peca`.
- Os CSVs abrem sem perda de colunas ou acentos (codificação UTF-8, vírgula como separador, aspas ao redor de campos com vírgula/acento).
- Zero medido: `cliques = 0`, `cliques_status = medido` (peça com link direto, fonte fictícia retornou zero).
- Métrica indisponível: `alcance_status = indisponível`, valor vazio, motivo em `observacoes` decorrente da própria fonte.
- Cliques por peça indisponíveis: na peça com CTA para a bio, `cliques` vazio e `cliques_status = indisponível`, pois o link de bio é compartilhado e a fonte não identifica qual peça originou o clique.

## 9. Arquivos entregues

| Caminho | Conteúdo |
| --- | --- |
| `05-mensuracao/GUIA-MENSURACAO-NS001-NS002.md` | Este guia operacional. |
| `05-mensuracao/modelo-registro-publicacoes.csv` | Modelo vazio para registro de publicações. |
| `05-mensuracao/modelo-registro-metricas.csv` | Modelo vazio para registro de métricas. |
| `05-mensuracao/ensaio-registro-publicacoes.csv` | Exemplo preenchido (ensaio, dados fictícios). |
| `05-mensuracao/ensaio-registro-metricas.csv` | Exemplo preenchido (ensaio, dados fictícios). |

## 10. Decisões que ainda dependem do titular

- Canais efetivamente publicados por campanha.
- CTA por canal (link na bio, sticker de link, URL na descrição).
- Destino clicável confirmado e link externo cadastrado no perfil.
- Mecanismo de rastreamento e fonte de dados confirmada para coleta de métricas.
- Aprovação dos briefings NS-001 e NS-002 antes de qualquer produção ou publicação.

Use os modelos apenas após essas decisões serem tomadas; até lá, preencha apenas o que estiver confirmado e deixe o restante como pendente.
