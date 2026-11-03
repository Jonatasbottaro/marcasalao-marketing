# MKT-PLATFORM-001 — Plataforma de produção multiprojeto

- Status: decisão arquitetural futura
- Implementação: não iniciada
- Primeiro consumidor: Marca Salão

## Decisão central

Usar o Marca Salão como primeiro projeto consumidor, sem incorporar marca, campanhas, regras comerciais, cores, domínios ou assets específicos ao núcleo futuro.

Registrar expressamente:

“Marca Salão será o primeiro consumidor da plataforma, não o núcleo da plataforma.”

## Separação conceitual

Núcleo reutilizável:

- contratos;
- schemas;
- timeline;
- validações;
- pipeline;
- adaptadores;
- renderizadores;
- inspeção de artefatos.

Configuração por projeto:

- metadados;
- identidade visual;
- idioma;
- assets;
- políticas;
- campanhas;
- CTA;
- formatos;
- destinos;
- regras editoriais.

## Regras contra acoplamento

O núcleo não deve conhecer:

- Marca Salão;
- NS-001;
- domínio marcasalao.com.br;
- logo do Marca Salão;
- cores específicas;
- funcionalidades do produto;
- textos promocionais;
- CTA específico;
- caminhos específicos do projeto.

## Estratégia de generalização

Não construir uma plataforma abstrata antes de provar o caso real.

Fluxo:

Caso real do Marca Salão
→ extrair o mínimo reutilizável
→ validar
→ criar segundo projeto de teste
→ identificar generalizações reais
→ evoluir o núcleo

## Critérios para algo entrar no núcleo

- independe de uma marca;
- atende pelo menos dois projetos;
- possui contrato definido;
- pode ser testado isoladamente;
- não carrega regra comercial específica;
- possui benefício comprovado.

## Possibilidades futuras

Registrar como possibilidades, não compromissos:

- ferramenta interna;
- múltiplas marcas;
- gerador de vídeos;
- apresentações;
- peças estáticas;
- Content Factory reutilizável;
- aplicação multiempresa;
- produto independente.

## Riscos

- abstração prematura;
- excesso de configuração;
- acoplamento oculto ao Marca Salão;
- dependência de fornecedor;
- duplicação entre projetos;
- schemas complexos antes do primeiro caso;
- outputs gerados misturados com fontes;
- regras editoriais tratadas como regra de renderização.

## Fora de escopo

- criar plataforma;
- criar segundo projeto;
- mover campanhas;
- renomear pastas;
- instalar ferramenta;
- criar schema;
- criar pipeline;
- criar renderer;
- publicar produto.
