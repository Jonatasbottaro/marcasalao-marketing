# Hooks — Content Factory Marca Salão

Esta pasta reúne os **hooks**: as primeiras frases de uma peça de conteúdo, escritas para prender a atenção antes de qualquer explicação.

Um hook é a etapa **Briefing → Hooks → Roteiro** do fluxo descrito em [`../00-briefings/README.md`](../00-briefings/README.md). Ele não é um roteiro completo nem uma legenda: é a porta de entrada que o roteiro desenvolve depois.

## 1. O que é um hook

É a abertura curta de uma peça — a primeira frase, a primeira tela ou os primeiros segundos — que faz a pessoa decidir se continua assistindo ou lendo.

## 2. Para que serve

- **Interromper a atenção** no meio de um feed em rolagem rápida.
- **Apresentar uma dor, uma pergunta ou um contraste** reconhecível para quem administra um salão.
- **Incentivar a continuidade** do conteúdo, criando a expectativa de que a peça seguinte entrega algo útil.
- **Permanecer coerente com o briefing** do qual deriva, sem ampliar o que ele permite dizer.

## 3. O que um hook não pode fazer

Um hook é descartado quando comete qualquer um destes erros:

- **Inventar uma funcionalidade** que não existe no sistema.
- **Transformar hipótese em fato**, apresentando como comprovado o que ainda depende de validação.
- **Prometer resultado garantido** ("elimina faltas", "aumenta o faturamento", "nunca mais perca clientes").
- **Exagerar uma dor sem evidência**, sobretudo em versão financeira.
- **Usar falsa urgência** ("só hoje", "últimas vagas", "antes que seja tarde").
- **Afirmar números sem fonte**, inclusive percentuais, médias e valores.
- **Sugerir que o sistema envia mensagens, lembretes ou confirmações automáticas** ao cliente, ou envia WhatsApp, SMS, e-mail ou push por conta própria. Existe implementação técnica dessas capacidades; implantação, configuração dos canais e entrega real não foram validados — ver seção 4.
- **Sugerir que o sistema elimina no-show** ou preenche automaticamente horários vagos. Não há validação operacional registrada que sustente um resultado atribuído a mensagens ou notificações.

Essas restrições vêm do contrato editorial de [`../00-briefings/README.md`](../00-briefings/README.md) e de [`../AGENTS.md`](../AGENTS.md).

## 4. Hooks sobre notificações, lembretes e contato

A existência de código, de testes ou de documentação técnica **não** autoriza um hook promocional.

Enquanto implantação, configuração dos canais e entrega real não forem validados, hooks não podem afirmar ou sugerir:

- "o sistema avisa o cliente";
- "o sistema lembra o cliente";
- "o sistema confirma automaticamente";
- "envie WhatsApp automaticamente";
- "reduza faltas com lembretes";
- "acabe com o no-show";
- qualquer resultado atribuído a mensagens ou notificações.

Hooks sobre essa capacidade somente poderão ser criados depois de um briefing específico aprovado, contendo validação operacional e autorização comercial — os registros exigidos estão em [`../00-briefings/README.md`](../00-briefings/README.md), seção "Notificações e automações de contato".

O texto permitido em documentação técnica é:

> "Existe implementação técnica; implantação e entrega real permanecem pendentes de validação."

Esse texto **não** deve ser usado como hook promocional: ele descreve estado de engenharia, não benefício para o dono do salão. Desempenho e operação não devem ser presumidos — não escrever "o lembrete funciona", "os clientes recebem o aviso" nem "as faltas caem" sem verificação registrada com responsável e data.

Também não escrever, em hook ou em nota de hook, que o sistema "não possui" notificações ou lembretes: formulação absoluta nesse sentido é imprecisa tecnicamente e continua proibida como mensagem atual.

## 5. Vínculo obrigatório com um briefing

Nenhum hook é escrito sem um briefing correspondente. Cada documento desta pasta declara, no bloco de controle, qual briefing o origina. Sem briefing, não há como saber se a dor é real, se a funcionalidade citada existe e se a promessa é defensável.

## 6. Convenção de pasta

```
02-hooks/campanhas/<CODIGO>/hooks.md
```

Uma campanha, um arquivo de hooks. O código é o mesmo do briefing em `00-briefings/campanhas/<CODIGO>/briefing.md`.

> **Nota sobre numeração.** Esta pasta reutiliza o prefixo `02-` já ocupado por `02-reels-shorts/`, e a sequência futura da Content Factory (`03-roteiros/`) colide com `03-youtube-pdf/`. A colisão é apenas de nome de pasta e não afeta o fluxo editorial. Renomear ou reorganizar pastas existentes está fora de escopo e depende de decisão específica do titular.

## 7. Estados de um hook

| Estado | Significado |
| --- | --- |
| `rascunho` | Escrito, ainda não revisado. |
| `em revisão` | Sob leitura editorial, aguardando ajustes. |
| `aprovado` | Liberado para virar roteiro. |
| `descartado` | Não segue adiante; registrado com o motivo. |
| `testado` | Publicado e medido; só neste estado o desempenho deixa de ser suposição. |

Registrar o estado real. Nenhum hook vira "aprovado" por ter sido bem escrito ou por parecer promissor.

## 8. Critério de "pronto para roteiro"

Um hook só avança quando **todos** os itens abaixo são verdadeiros:

- [ ] está vinculado a um briefing;
- [ ] permanece dentro das promessas permitidas por esse briefing;
- [ ] não depende de funcionalidade ainda não validada;
- [ ] não contém dado inventado;
- [ ] tem um público compreensível;
- [ ] tem uma continuação possível no roteiro;
- [ ] está marcado como `aprovado`;
- [ ] o briefing correspondente está aprovado — ou existe autorização registrada para avançar como experimento controlado.

## 9. Categorias iniciais

| Categoria | Movimento |
| --- | --- |
| `pergunta` | Formula uma pergunta que a pessoa reconhece como sua. |
| `dor` | Nomeia uma situação difícil da rotina, sem exagerá-la. |
| `diagnóstico` | Convida a refletir sobre o próprio processo, em formulação condicional. |
| `contraste` | Compara dois modos de fazer a mesma tarefa, sem desvalorizar quem usa um deles. |
| `curiosidade` | Abre uma lacuna de informação que a peça preenche, sem enganar. |

## 10. Sobre desempenho

Enquanto um hook não foi publicado **e medido**, qualquer afirmação sobre seu desempenho é hipótese. Não escrever "este hook converte mais", "funciona melhor no Reels" ou "tem maior retenção" sem dado real coletado na plataforma. A regra é a mesma do briefing: resultado esperado, nunca resultado garantido.

## 11. Nomenclatura

```
<CODIGO-DA-CAMPANHA>-H<NUMERO>
```

Exemplos:

- `NS-001-H01`
- `NS-001-H02`

O número é sequencial dentro da campanha e nunca é reutilizado, inclusive para hooks descartados.
