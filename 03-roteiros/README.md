# Roteiros — Content Factory Marca Salão

Esta pasta reúne os **roteiros**: o plano escrito de uma peça, cena por cena, antes de qualquer gravação.

O roteiro é um artefato de planejamento. Ele não é a peça, não está aprovado para gravação e não autoriza publicação.

## 1. O que é um roteiro na Content Factory

É o documento que transforma um hook selecionado em uma sequência executável: objetivo, público, cenas, textos de tela, narração, demonstração, materiais, riscos e pendências. Ele define **o que será mostrado e dito** — e, sobretudo, o que **não** pode ser dito.

## 2. Vínculo obrigatório

```
Briefing → Hook selecionado → Roteiro → Legenda → Produção → Publicação → Métricas
```

Cada etapa consome a anterior. O roteiro herda do briefing a dor, o público, a evidência e os limites de promessa, e herda do hook a frase de abertura. Nenhum roteiro nasce sem os dois.

- Briefing: [`../00-briefings/README.md`](../00-briefings/README.md)
- Hooks: [`../02-hooks/README.md`](../02-hooks/README.md)

## 3. O roteiro não amplia as promessas do briefing

O que o briefing não autorizou, o roteiro não escreve. Se uma frase parece boa mas não tem espaço no briefing, ela fica fora — ou volta como pendência de revisão do briefing, registrada em outro documento.

## 4. Toda demonstração usa comportamento validado

Nenhuma cena de demonstração pode descrever clique, filtro, visualização, alerta ou fluxo que não tenha sido verificado no sistema atual, com responsável e data registrados. Comportamento lido em código ou sugerido por interface sem teste continua **pendente**, não vira roteiro aprovado.

## 5. Marcações `[PENDENTE DE VALIDAÇÃO]`

Marcas como:

```
[PENDENTE DE VALIDAÇÃO FUNCIONAL]
```

permanecem no roteiro até a verificação ser feita por quem tem acesso ao sistema. Remover a marcação exige evidência registrada, não a decisão de quem escreveu o texto.

## 6. Captura prova somente o que aparece nela

Uma captura de tela sustenta a existência de rótulos, botões e elementos visíveis. Ela não comprova que o botão funciona, que o filtro filtra, que a exportação exporta, nem que duas telas conversam entre si.

## 7. Limitação de produto

Nenhum roteiro pode afirmar, sugerir visualmente ou deixar implícita, sem validação operacional específica e registrada, nenhuma destas capacidades:

- mensagens, lembretes ou confirmações automáticas;
- envio automático de WhatsApp, SMS, e-mail ou push;
- preenchimento automático de horários vagos;
- redução de no-show ou de faltas causada por automação.

A formulação tecnicamente precisa é: existe implementação técnica de notificações e de lembrete de 24 horas no sistema; implantação, configuração dos canais e entrega real não foram validados. Portanto, o roteiro pode registrar a existência da implementação técnica quando sustentada por evidência, mas não pode afirmar que a capacidade está implantada, configurada, operacional ou entregando mensagens. A demonstração e o uso promocional permanecem bloqueados. A regra de demonstração está na seção 8.

Regras completas em [`../00-briefings/README.md`](../00-briefings/README.md) e [`../AGENTS.md`](../AGENTS.md).

## 8. Demonstração de notificações e lembretes

Nenhum roteiro pode mostrar, narrar ou sugerir notificações, mensagens, lembretes ou confirmações automáticas apenas porque existe implementação técnica no repositório.

Antes de autorizar uma cena sobre contato automático, devem estar registrados:

- ambiente de execução;
- gatilho;
- scheduler;
- provedor;
- canal;
- destinatário fictício;
- template utilizado;
- entrega observada;
- resultado da tentativa;
- falhas observadas;
- proteção de dados;
- data;
- responsável;
- autorização comercial.

Até essa validação, o roteiro deve classificar a capacidade como:

| Item | Classificação no roteiro |
| --- | --- |
| Implementação técnica | confirmada, quando sustentada por evidência |
| Implantação | pendente |
| Configuração dos canais | pendente |
| Entrega real | pendente |
| Uso promocional | não autorizado |
| Demonstração | não autorizada |

O roteiro não pode transformar:

- teste unitário em demonstração;
- mock em entrega;
- scheduler definido em scheduler ativo;
- canal opcional em canal disponível;
- tentativa de envio em mensagem entregue;
- implementação em promessa comercial.

A distinção entre implementação, teste automatizado, implantação, configuração, execução, entrega real e autorização comercial é obrigatória em toda cena, texto de tela e linha de narração. Não afirmar que os canais estão ativos e não afirmar que estão desativados: sem verificação registrada, nenhum dos dois estados é dizível.

## 9. Estados permitidos

| Estado | Significado |
| --- | --- |
| `rascunho` | Roteiro em escrita, sem revisão concluída. |
| `em revisão` | Em leitura editorial. |
| `bloqueado por validação` | Aguarda verificação funcional no sistema. |
| `aprovado para produção` | Liberado para gravar, com validações registradas. |
| `produzido` | Material gerado a partir deste roteiro. |
| `publicado` | Peça efetivamente publicada, conferida na fonte. |
| `arquivado` | Encerrado, mantido para histórico. |

Registrar o estado real. Um roteiro bem escrito não sobe de estado sozinho.

## 10. Critério de "pronto para produção"

Um roteiro só avança para gravação quando **todos** os itens abaixo são verdadeiros:

- [ ] briefing aprovado;
- [ ] hook aprovado;
- [ ] funcionalidade demonstrada validada no sistema atual;
- [ ] telas verificadas na data da produção;
- [ ] dados pessoais removidos de toda captura;
- [ ] texto de narração revisado;
- [ ] texto de tela revisado;
- [ ] CTA confirmado, com destino documentado;
- [ ] duração estimada revisada após leitura;
- [ ] nenhuma promessa indevida;
- [ ] responsável pela aprovação registrado.

Enquanto a validação funcional da agenda não existir, nenhum roteiro desta pasta passa de `rascunho`.

## 11. Convenção

```
03-roteiros/campanhas/<CODIGO>/roteiro-<NUMERO>.md
```

O código é o mesmo do briefing e da biblioteca de hooks; o número é sequencial dentro da campanha.

> **Nota sobre numeração.** Esta pasta reutiliza o prefixo `03-` já ocupado por `03-youtube-pdf/`. A coincidência é apenas de nome de pasta e não altera o fluxo editorial. Renomear ou reorganizar pastas existentes está fora de escopo e depende de decisão do titular.

## 12. Roteiro em rascunho não é conteúdo aprovado

Rascunho na pasta `03-roteiros/` continua sendo intenção editorial. Ele não autoriza gravar, editar, criar legenda, publicar, agendar nem registrar métricas. Produção segue as regras de [`../WORKFLOW.md`](../WORKFLOW.md) (vídeo sem áudio, legendas visíveis sincronizadas, `.srt` correspondente, narração em texto separado) e a autorização específica de publicação prevista em [`../AGENTS.md`](../AGENTS.md).
