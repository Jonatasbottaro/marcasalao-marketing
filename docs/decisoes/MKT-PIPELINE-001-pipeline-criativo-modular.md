# MKT-PIPELINE-001 — Pipeline criativo modular por beats e assets independentes

- Status: decisão arquitetural futura
- Implementação: não iniciada
- Primeiro caso de uso previsto: Marca Salão
- Dependência: MKT-VIDEO-001 e MKT-PLATFORM-001
- Aplicação imediata: orientar o futuro contrato Composition
- Autorização de produção: não concedida

## Contexto

Workflows audiovisuais assistidos por IA tendem a obter resultados mais consistentes quando seguem uma sequência planejada, em vez de gerar mídia direto de um prompt solto:

```
Ideia → roteiro → beats → estilo visual → referências → assets por cena
→ movimento → áudio → montagem → validação
```

Os conceitos úteis observados nesse tipo de workflow são: planejamento antes da geração; decomposição do roteiro em beats; direção visual compartilhada; imagem ou referência visual âncora; assets independentes por cena; movimento descrito separadamente; texto editável fora da mídia gerada; áudio separado da composição visual; montagem por adaptador; validação antes da publicação.

O projeto já possui um fluxo editorial anterior, definido em `00-briefings/README.md`, `02-hooks/README.md` e `03-roteiros/README.md`:

```
Evidência funcional → briefing → hook → roteiro → aprovação
→ produção → publicação → métricas
```

Esta decisão **não substitui** esse fluxo. Ela define o pipeline entre **roteiro aprovado → produção validada**: o que acontece depois que o conteúdo editorial está aprovado e antes que qualquer peça possa ser publicada.

## Decisão central

> “Toda produção audiovisual deve ser planejada como uma sequência de beats temporais versionados. Direção visual, assets, movimento, texto, áudio e montagem são módulos independentes, relacionados por contratos, mas substituíveis.”

Registrar expressamente:

- roteiro não é composição;
- composição não é renderização;
- imagem não contém o texto canônico;
- áudio não fica incorporado obrigatoriamente ao visual;
- fornecedor não faz parte do contrato editorial;
- aprovação de conteúdo precede geração de mídia;
- publicação depende de validação final.

Esses pontos herdam MKT-VIDEO-001 (conteúdo separado do renderizador) e MKT-PLATFORM-001 (núcleo multiprojeto sem marca no núcleo).

## Pipeline conceitual

```
Evidência funcional
→ Briefing aprovado
→ Hook aprovado
→ Roteiro aprovado
→ Composition
→ BeatPlan
→ VisualStyle
→ VisualAnchor
→ AssetManifest
→ AudioPlan
→ RenderPlan
→ Adaptador
→ Artefatos
→ Validação
→ Aprovação de publicação
→ Publicação
→ Métricas
```

Responsabilidade de cada etapa (conceitual; sem schema nem interface executável nesta decisão):

| Etapa | Responsabilidade |
| --- | --- |
| Evidência funcional | Provar no sistema atual o que a campanha pode mostrar. |
| Briefing aprovado | Dor, público, mensagem, limites de promessa e CTA. |
| Hook aprovado | Abertura curta que o roteiro desenvolve. |
| Roteiro aprovado | Cenas, textos de tela, narração e demonstrações permitidas. |
| Composition | Contrato declarativo da peça: formato, cenas, textos, mídia, CTA. |
| BeatPlan | Decomposição temporal do roteiro em beats versionados. |
| VisualStyle | Direção visual compartilhada, declarada uma vez e herdada. |
| VisualAnchor | Referência visual âncora para consistência entre cenas. |
| AssetManifest | Inventário versionado e rastreável dos materiais. |
| AudioPlan | Plano de áudio independente da composição visual. |
| RenderPlan | Escolha registrada de como a peça será montada/renderizada. |
| Adaptador | Tradução dos contratos neutros para uma ferramenta concreta. |
| Artefatos | Saídas geradas (vídeo, imagem, áudio, legendas), separadas das fontes. |
| Validação | Verificação técnica e editorial antes da publicação. |
| Aprovação de publicação | Decisão humana explícita de liberar. |
| Publicação | Distribuição conforme as regras de `AGENTS.md`. |
| Métricas | Resultado observado, que alimenta o próximo briefing. |

## BeatPlan

O **BeatPlan** é a decomposição temporal do roteiro: a lista ordenada e versionada dos beats que a peça executa.

Cada beat deve poder representar conceitualmente:

- id;
- ordem;
- função narrativa;
- duração estimada;
- segmento de narração;
- texto na tela;
- intenção visual;
- intenção de movimento;
- transição de entrada;
- transição de saída;
- evidência editorial;
- estado de validação.

A duração **não será fixada universalmente em seis segundos**. A duração estimada de cada beat deverá considerar:

- duração real ou estimada da narração;
- tempo mínimo de leitura;
- tempo necessário de demonstração;
- ritmo editorial;
- transição;
- formato da peça.

Registrar: **cenas e beats não precisam ser equivalentes um para um.** Uma cena pode conter vários beats; um beat pode atravessar duas cenas. O roteiro continua sendo a fonte editorial; o BeatPlan é a tradução temporal para produção.

## Direção visual

### VisualStyle

Responsável por:

- paleta;
- tipografia;
- iluminação;
- profundidade;
- materiais;
- textura;
- enquadramento;
- ritmo visual;
- áreas seguras;
- política de texto em mídia.

### VisualAnchor

Responsável por:

- referência visual principal;
- consistência entre cenas;
- imagem âncora;
- referências permitidas;
- elementos obrigatórios;
- elementos proibidos;
- origem;
- licença;
- versão;
- hash futuro do asset.

Registrar:

- estilo é declarado uma vez e herdado;
- cenas podem especializá-lo sem alterar o contrato do projeto;
- VisualAnchor não depende de Google Flow, HyperFrames ou outro fornecedor;
- adaptadores traduzem a referência para cada ferramenta.

## AssetManifest

O **AssetManifest** é o inventário versionado dos materiais usados pela peça.

Cada asset poderá futuramente registrar:

- id;
- tipo;
- caminho;
- origem;
- fornecedor;
- prompt;
- versão;
- licença;
- status;
- dimensões;
- duração;
- formato;
- hash;
- cena ou beat consumidor;
- política de dados pessoais.

Tipos conceituais possíveis:

- image;
- video;
- screenshot;
- illustration;
- logo;
- narration;
- music;
- sound-effect;
- subtitle;
- font.

Registrar:

- arquivos gerados não são fontes editoriais;
- assets precisam de rastreabilidade;
- capturas de produto exigem dados fictícios;
- mídia sem origem ou licença conhecida não deve chegar à publicação.

## Texto editável

Regra:

> “O texto canônico permanece estruturado e editável fora de imagens e vídeos gerados.”

Consequências:

- texto na tela pertence à composição;
- CTA pertence à composição;
- legendas pertencem ao plano de conteúdo ou áudio;
- imagem gerada não é fonte canônica do texto;
- correção de texto não deve exigir regenerar o visual;
- tradução não deve exigir regenerar assets sem necessidade;
- tipografia e acessibilidade permanecem controláveis.

Texto queimado na mídia pode existir apenas como **exceção registrada e validada** — nunca como comportamento padrão do pipeline.

## Áudio separado

O **AudioPlan** é um módulo independente da composição visual. Deve poder representar conceitualmente:

- modo de áudio;
- roteiro de locução;
- provider;
- voz;
- idioma;
- arquivo de narração;
- música;
- efeitos;
- duração;
- marcadores;
- normalização;
- mix profile;
- legenda associada;
- licença;
- estado de aprovação.

Modos possíveis:

- human-recording;
- text-to-speech;
- imported;
- none.

Registrar:

- áudio não pertence obrigatoriamente ao renderizador visual;
- locução deve poder ser substituída sem remontar o conteúdo editorial;
- fornecedor de voz deve ficar atrás de adaptador;
- ElevenLabs é possibilidade futura, não dependência;
- nenhuma chave ou voz específica deve ser codificada no núcleo;
- áudio gerado não é automaticamente aprovado;
- pronúncia e licença exigem revisão.

Nota de coerência com a regra vigente (`AGENTS.md`/`WORKFLOW.md`): a produção do Marca Salão hoje entrega **vídeo sem faixa de áudio**, com narração como texto separado e `.srt` correspondente. Isso corresponde, na terminologia desta decisão, ao modo `none` combinado com narração estruturada fora da mídia — a regra atual permanece vigente e só muda mediante pedido explícito do titular.

## Movimento e transições

**MotionIntent** e **TransitionIntent** são descrições neutras de intenção, não comandos de ferramenta.

Exemplos conceituais:

- slow-zoom;
- parallax-depth;
- camera-orbit;
- fade;
- material-dissolve;
- slide;
- cut;
- none.

Registrar:

- o contrato descreve intenção;
- o adaptador decide a implementação compatível;
- não usar nomes específicos de uma ferramenta como contrato canônico;
- ferramentas podem degradar uma intenção de forma registrada;
- ausência de capacidade deve gerar warning ou erro, não comportamento silencioso.

## Adaptadores

Contratos conceituais de adaptador:

- **ImageGeneratorAdapter** — gera imagens a partir de prompts e referências;
- **VideoGeneratorAdapter** — gera clipes de vídeo por beat/cena;
- **AudioProvider** — produz ou importa narração, música e efeitos;
- **Assembler** — monta a peça a partir de assets, textos e timing;
- **Renderer** — transforma composição em artefato final;
- **ArtifactInspector** — inspeciona artefatos (duração, faixas, legendas, dimensões).

Possibilidades futuras:

- Google Flow;
- HTML/CSS;
- FFmpeg;
- CapCut manual;
- HyperFrames;
- ElevenLabs;
- outros.

Registrar:

- **nenhuma ferramenta foi adotada por esta decisão** — todas as citações acima são possibilidades futuras;
- integrações ficam atrás de adaptadores;
- um pipeline pode misturar fornecedores;
- troca de fornecedor não deve alterar roteiro ou política editorial;
- credenciais nunca pertencem ao manifesto versionado;
- execução remota deve ser opt-in e auditável.

## Automação e revisão humana

Bons candidatos à automação:

- decomposição do roteiro em beats;
- estimativa inicial de duração;
- validação de texto;
- criação de prompts;
- nomenclatura de assets;
- checagem de assets ausentes;
- geração de variações;
- geração de locução;
- geração de SRT/VTT;
- inspeção técnica de mídia;
- comparação entre roteiro e composição;
- relatório final.

Decisões humanas obrigatórias:

- mensagem principal;
- escolha do hook;
- aprovação do roteiro;
- veracidade comercial;
- aprovação visual;
- seleção de geração;
- pronúncia;
- direitos de uso;
- privacidade;
- autorização de publicação.

A automação nunca substitui o rol de decisões humanas; onde houver dúvida entre os dois, prevalece a revisão humana.

## Multiprojeto

- o pipeline pertence ao núcleo reutilizável;
- estilos, temas, assets, políticas e fornecedores permitidos pertencem ao projeto;
- Marca Salão será o primeiro consumidor;
- **nenhuma regra do pipeline deve verificar projectId de uma marca**;
- um segundo projeto deverá validar a generalização antes de promover novos recursos ao núcleo.

## Portabilidade e determinismo

Princípios para implementação futura:

- contratos versionados;
- relatórios determinísticos;
- ordem estável;
- fontes separadas de outputs;
- paths relativos;
- hashes de assets;
- execução local quando possível;
- rede opt-in;
- fornecedores registrados;
- nenhuma dependência de conversa como fonte única;
- prompts importantes versionados;
- outputs reproduzíveis dentro dos limites do fornecedor.

Registrar que IA generativa pode não ser deterministicamente reproduzível, mesmo com prompt igual. Nesse caso, preservar:

- prompt;
- modelo;
- provider;
- parâmetros;
- seed, quando disponível;
- data;
- asset resultante;
- hash;
- seleção humana.

## Relação com a NS-001

A NS-001 poderá ser o primeiro caso real para testar partes do pipeline somente depois de:

- briefing aprovado;
- hook aprovado;
- roteiro aprovado;
- cenas validadas por execução;
- capturas com dados fictícios;
- autorização específica de produção.

Esta decisão não:

- aprova a campanha;
- libera gravação;
- libera publicação;
- altera checkboxes;
- cria assets;
- cria áudio;
- escolhe renderizador.

## Riscos e mitigações

| Risco | Mitigação curta |
| --- | --- |
| Abstração prematura | Extrair contratos somente depois do primeiro caso real validado. |
| Excesso de contratos | Cada contrato precisa de consumidor concreto, schema e teste. |
| Fornecedor invadindo o núcleo | Nomes de ferramentas só em adaptadores; contratos neutros. |
| Prompts não versionados | Versionar prompt, modelo, parâmetros e seed quando existir. |
| Ausência de rastreabilidade | AssetManifest obrigatório com origem, versão e hash. |
| Mídia sem licença | Bloquear da publicação qualquer asset sem origem/licença. |
| Texto incorporado à imagem | Texto canônico fora da mídia; queimado só como exceção registrada. |
| Áudio acoplado ao vídeo | AudioPlan independente; montagem por adaptador. |
| Custos imprevisíveis de geração | Registrar contagem e limites de geração por peça antes de gerar. |
| Variação não controlada de IA | Preservar prompt/modelo/provider/seed/hash e registrar seleção humana. |
| Dados pessoais em captura | Somente dados fictícios; inspeção antes da publicação. |
| Publicação sem aprovação | Publicação sempre condicionada a validação + aprovação humana explícita. |
| Tentativa de automatizar julgamento editorial | Automação limitada ao rol mecânico; decisões humanas ficam com humanos. |

## Critérios para implementação futura

A implementação do pipeline só pode começar **incrementalmente**, na ordem recomendada:

1. Composition;
2. BeatPlan;
3. VisualStyle;
4. VisualAnchor;
5. AssetManifest;
6. AudioPlan;
7. RenderPlan;
8. Fake adapters;
9. primeiro adaptador real;
10. piloto de campanha.

Cada incremento deve:

- ter contrato;
- ter schema;
- ter validação;
- ter relatório;
- ter testes;
- preservar independência de projeto;
- não exigir fornecedor sem necessidade.

## Fora de escopo

- criar Composition;
- criar BeatPlan executável;
- criar schemas;
- criar código;
- alterar `platform/`;
- instalar Google Flow;
- instalar HyperFrames;
- instalar ElevenLabs;
- instalar FFmpeg;
- integrar CapCut;
- gerar imagem;
- gerar vídeo;
- gerar áudio;
- criar prompts de campanha;
- alterar NS-001;
- criar assets;
- alterar workflows;
- publicar conteúdo;
- criar credenciais;
- executar deploy.
