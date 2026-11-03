# MKT-VIDEO-001 — Produção modular e programática

- Status: decisão arquitetural futura
- Implementação: não iniciada
- Prioridade atual: posterior à validação da primeira campanha
- Primeiro caso de uso: Marca Salão

## Contexto

Registrar que a Content Factory precisa produzir conteúdos reproduzíveis, testáveis e revisáveis, evitando acoplamento entre conteúdo editorial e tecnologia de renderização.

## Decisão

Adotar futuramente uma arquitetura modular:

Conteúdo aprovado
→ Especificação neutra
→ Composição
→ Renderizador
→ Validação
→ Artefato final

## Princípios

- módulos pequenos;
- interfaces claras;
- testes isolados;
- falhas localizadas;
- conteúdo separado do renderizador;
- assets separados da composição;
- outputs separados das fontes;
- dependências externas atrás de adaptadores;
- preview e renderização reproduzíveis;
- nenhuma ferramenta decide promessas comerciais.

## Renderizadores possíveis

Registrar como possibilidades futuras:

- HTML/CSS + FFmpeg;
- HyperFrames;
- edição manual;
- outros renderizadores.

Deixar explícito:

- HyperFrames não foi adotado;
- HyperFrames não será copiado;
- conceitos úteis podem ser estudados;
- eventual integração ficará atrás de adaptador;
- nenhuma composição deve depender obrigatoriamente dele.

## Conceitos úteis inspirados no HyperFrames

- composição declarativa;
- timeline determinística;
- animações controladas pelo tempo;
- templates;
- preview;
- lint;
- renderização reproduzível;
- integração com agentes;
- variações de formato.

## Contratos conceituais

Renderer:

- validate;
- preview;
- render;
- inspect;
- report.

Composition:

- formato;
- cenas;
- timeline;
- textos;
- mídia;
- legendas;
- áudio;
- CTA.

Validator:

- schema;
- editorial;
- privacidade;
- assets;
- duração;
- acessibilidade;
- output.

Esses contratos são conceituais. Não criar interfaces de código nesta tarefa.

## Critério para iniciar implementação

- briefing aprovado;
- hook aprovado;
- roteiro aprovado;
- assets fictícios aprovados;
- necessidade real de renderização;
- primeiro piloto definido;
- comparação possível com fluxo manual.

## Fora de escopo

- implementação;
- escolha definitiva de framework;
- instalação;
- renderização;
- criação de templates executáveis;
- migração de peças existentes.
