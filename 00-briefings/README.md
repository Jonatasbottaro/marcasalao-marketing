# Briefings de campanha — Content Factory Marca Salão

Esta pasta reúne os briefings: o ponto de partida documentado de toda campanha ou peça de conteúdo do Marca Salão.

Um briefing é o registro escrito de **por que** uma peça existe: qual dor do salão ela aborda, qual impacto essa dor causa, qual solução o Marca Salão ajuda a construir, qual funcionalidade comprova essa solução e o que pode ser dito com segurança.

Nenhum conteúdo novo (arte, vídeo, legenda, post ou roteiro) deve ser produzido sem um briefing aprovado. Sem briefing, não há como saber se a peça responde a um problema real, se o que ela mostra existe no sistema e se o que ela promete é defensável.

## Fluxo da Content Factory

```
Briefing → Hooks → Roteiro → Legendas → Vídeo ou peça → Publicação → Métricas → Aprendizado
```

Cada etapa consome a anterior. O briefing é a única etapa que define a dor, o público, a evidência e os limites de promessa; tudo que vem depois herda essas decisões. O resultado da última etapa (métricas e aprendizado) volta para o próximo briefing.

A produção segue as regras de [`../WORKFLOW.md`](../WORKFLOW.md) e [`../AGENTS.md`](../AGENTS.md): vídeo sem áudio, legendas visíveis sincronizadas, `.srt` correspondente, narração em texto separado e CTA específico por rede.

## Conceitos que não devem ser misturados

| Conceito | O que é | Cuidado |
| --- | --- | --- |
| Dor do público | Problema que o estabelecimento reconhece e sente na rotina. | Não inventar a dor; descrever a situação em que ela aparece. |
| Impacto da dor | Consequência operacional, financeira, na experiência do cliente ou na equipe. | Valores só com fonte, dado real ou hipótese rotulada. |
| Solução proposta | Como o problema pode ser enfrentado, incluindo o processo do salão. | A solução não é necessariamente o software; o salão também age. |
| Funcionalidade demonstrada | Recurso concreto do sistema atual usado como prova da solução. | Precisa existir e ter sido verificada antes de virar conteúdo. |
| Resultado esperado | Melhora que se espera observar, sem garanti-la. | Escrever como expectativa, nunca como promessa. |
| Promessa garantida | Afirmação de resultado certo ("elimina faltas", "aumenta o faturamento"). | Proibida. Não há evidência que a sustente. |

Marque explicitamente em cada campo se a informação é **confirmada**, **hipótese** ou **pendente de validação**. Hipótese não vira fato por repetição.

## Regras de veracidade

1. **A funcionalidade precisa ser demonstrável no sistema atual.** Antes de produzir, verificar no painel de demonstração que o recurso existe, onde está e qual comportamento ele executa. Se não for possível verificar, o briefing fica "em validação" e a funcionalidade não entra na peça.
2. **Uma captura de tela comprova somente o que está visível nela.** Ela não comprova integrações, automações, sincronizações, nem resultados de negócio. Descreva a tela como ela é, sem extrapolar.
3. **É proibido divulgar funcionalidades não implementadas ou não validadas**, ainda que pareçam plausíveis ou solicitadas por clientes.
4. **O Marca Salão não possui sistema de mensagens, lembretes ou confirmações automáticas.** É proibido atribuir ao sistema, em qualquer material:
   - mensagens, lembretes ou confirmações automáticas;
   - envio automático de WhatsApp, SMS ou e-mail;
   - notificações automáticas não implementadas e validadas;
   - redução garantida de faltas ou no-show;
   - qualquer capacidade não comprovada no produto atual.
5. **Não publicar nem afirmar que uma campanha existe em produção** a partir do briefing. O documento registra intenção e estado editorial; publicação e agendamento continuam dependendo de autorização específica ([`../AGENTS.md`](../AGENTS.md)).
6. **Sem credenciais.** Não incluir senhas, tokens, chaves, cookies ou dados pessoais de clientes em briefing algum. O acesso à demonstração não fica neste repositório; solicite ao responsável pelo projeto.

## Como criar um briefing

1. Copie [`TEMPLATE-BRIEFING.md`](TEMPLATE-BRIEFING.md).
2. Salve em `00-briefings/campanhas/<CODIGO>/briefing.md`, uma pasta por campanha. Ao nascer a pasta de produção, o briefing acompanha a campanha como origem.
3. Atribua um código único (veja a convenção abaixo) e não reutilize códigos de campanhas anteriores.
4. Preencha todos os campos obrigatórios; escreva "não se aplica" quando for o caso, nunca deixe em branco sem explicação.
5. Registre hipóteses e pendências criticamente, identificando quem valida e quando.
6. Valide a funcionalidade usada como prova antes de liberar a produção.
7. Consulte os temas já usados em `../marcas/marcasalao/posts/` e na memória da marca para não repetir ângulo nem contradizer o que já foi dito.
8. Use [`../templates/CAMPAIGN_TEMPLATE.md`](../templates/CAMPAIGN_TEMPLATE.md) na fase de produção e [`../docs/ARQUIVAMENTO-DE-CAMPANHAS.md`](../docs/ARQUIVAMENTO-DE-CAMPANHAS.md) ao arquivar o material aprovado.

## Convenção de identificação

```
[SIGLA-DA-CAMPANHA]-[NÚMERO]
```

- A sigla resume o tema da campanha em duas a quatro letras.
- O número é sequencial de três dígitos, sem reutilização.
- Exemplo apenas de formato: `NS-001`. Esse código **não** representa campanha aprovada ou criada; é ilustração de identificação.

## Estados permitidos

| Estado | Significa |
| --- | --- |
| rascunho | Ideia em escrita; campos ainda abertos. |
| em validação | Aguarda verificação de funcionalidade, evidência ou aprovação. |
| aprovado | Pronto para produção, sem pendência crítica. |
| em produção | Materiais sendo gerados. |
| publicado | Conteúdo efetivamente publicado, com estado lido na fonte. |
| arquivado | Encerrado; mantido para histórico e consulta de temas. |

Registrar o estado real, nunca o pretendido. Um briefing "aprovado" não prova que algo foi publicado; "publicado" só se escreve após verificar a publicação.

## Critério de "pronto para produção"

Um briefing só passa para produção quando **todos** os itens abaixo estiverem verdadeiros:

- [ ] a dor está claramente descrita, com a situação em que ocorre;
- [ ] o público está definido;
- [ ] a mensagem principal está definida;
- [ ] a funcionalidade usada como prova foi verificada no sistema atual, com responsável e data;
- [ ] as telas ou evidências necessárias estão identificadas;
- [ ] o CTA e o destino estão definidos, por canal;
- [ ] não há promessa não comprovada, nem automação inexistente atribuída ao sistema;
- [ ] as métricas pretendidas estão registradas (ou "linha de base ainda não disponível");
- [ ] as pendências críticas foram resolvidas;
- [ ] o checklist da seção 15 do template está completo e a aprovação está registrada.

## Relação com os documentos existentes

| Arquivo | Papel | Diferença |
| --- | --- | --- |
| Esta pasta | Decisão editorial e evidência antes de produzir. | Responde "por que e o que podemos dizer". |
| [`../templates/CAMPAIGN_TEMPLATE.md`](../templates/CAMPAIGN_TEMPLATE.md) | Estrutura e checklist de entrega da campanha produzida. | Trata de arquivos, mídia e reprodução; não define dor nem promessa. |
| [`../marcas/marcasalao/comfyui/exemplo-brief.json`](../marcas/marcasalao/comfyui/exemplo-brief.json) | Brief de execução da arte no ComfyUI (tema, título, benefícios, direção visual, legendas). | É derivado do briefing, não substituto. Um briefing aprovado pode gerar vários briefs de arte. |
| [`../docs/ARQUIVAMENTO-DE-CAMPANHAS.md`](../docs/ARQUIVAMENTO-DE-CAMPANHAS.md) | Como guardar o material aprovado e publicado. | Registra o resultado; o briefing registra a intenção. |
| [`../WORKFLOW.md`](../WORKFLOW.md) / [`../AGENTS.md`](../AGENTS.md) | Regras de produção e de publicação. | Prevalcem sobre qualquer convenção desta pasta. |
