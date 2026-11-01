# Memória de marketing com ai-memory

Esta configuração foi conferida contra ai-memory 3.3.0, commit
62d1c90dd040d472dfec4e5a2144ba24db878e7d.
O binário/servidor e sua wiki privada são instalados fora do repositório.
Requer Python 3.11+ para o importador, sem dependências pip.

## Estrutura e escopos

| Diretório de trabalho | Workspace | Project |
| --- | --- | --- |
| Raiz / ferramentas gerais | marketing | marcasalao-marketing |
| marcas/marcasalao/ | marketing | marcasalao |
| marcas/multitrackhub/ | marketing | multitrackhub |

Os marcadores mais próximos definem o escopo dos hooks. Para bots operando
sempre na raiz, definir explicitamente o par da marca em todas as chamadas MCP.
No Hermes gateway, configurar também o marcador no home privado de cada perfil:
o diretório do processo pode ser diferente do checkout. Não copiar credenciais.

- common/_rules/: regras gerais fixadas, replicadas nos três escopos.
- common/decisions/ e common/procedures/: decisões e procedimentos gerais.
- marcasalao/ e multitrackhub/: páginas exclusivas de cada marca.
- campaigns/: namespace remoto produzido a partir de marcas/<marca>/posts/*/README.md.
- sessions/: criado pelo ai-memory durante a operação, fora do Git público.
- templates/campanha.md: modelo para registrar uma campanha nova manualmente.

As páginas têm H1 e fontes; o importador atribui kind, tier e tags via MCP.
Regras usam kind=rule, tier=semantic e pinned=true; decisões usam kind=decision;
procedimentos usam kind=fact e tier=procedural. Campanhas são snapshots sem TTL,
tier=semantic, tag historical e link imutável para a revisão do README.
Datas, aprovações e estados do documento são históricos, não uma leitura atual do Postiz.

## Ativação no ambiente do agente

1. Instalar uma release oficial de ai-memory conforme
   https://github.com/akitaonrails/ai-memory/blob/main/docs/install.md.
   Fixar a versão homologada e verificar checksum. Windows nativo é experimental;
   Linux/WSL2 são suportados pelo upstream.
2. Em uma instalação dedicada, usar config/server.toml.example como base da
   configuração privada do servidor. Em uma instalação existente, integrar os
   campos com cuidado. O exemplo desativa embeddings, captura de respostas,
   esquecimento automático e manutenção por LLM. Não configurar llm_provider ou
   llm_fallbacks nesta etapa. Conferir variáveis AI_MEMORY_* que possam sobrepor
   o arquivo. Tokens e diretório de dados permanecem privados.
3. Configurar a integração do agente com a CLI oficial:

   ```sh
   ai-memory setup --yes --agent codex
   ai-memory doctor
   ```

   setup é uma ação no host: instala serviço, MCP, hooks e skills. Executar após
   revisar a configuração privada e reiniciar o agente para carregar a integração.
   Se o servidor já for administrado separadamente, usar --no-service.
   Este commit não executa setup nem modifica configurações globais.
4. Para Hermes, consultar a integração específica:

   ```sh
   ai-memory install-hooks --agent hermes
   ai-memory install-mcp --client hermes
   ai-memory install-skills --scope global --agent hermes
   ```

   Os dois primeiros imprimem trechos para integrar ao YAML privado; o upstream
   não aplica esses blocos automaticamente. Conferir o escopo de cada perfil e
   o mecanismo de aceitação de hooks do Hermes. O upstream declara suporte
   modelado no Hermes v0.22.2, ainda sem validação ponta a ponta dos mantenedores.
5. Revisar/importar as páginas conforme abaixo e testar busca/briefing por marca.

## Revisar e importar

Plano offline, padrão sem contato com servidor:

```sh
python tools/memory_sync.py --scope all --plan
```

Revisar os Markdown de memory/ e os READMEs das campanhas listadas. O importador
não percorre perfis Hermes, logs, .env, imagens ou a biblioteca .agents/.

Com o servidor stateless acessível, fornecer a chave de usuário por variável
AI_MEMORY_AUTH_TOKEN no ambiente privado e executar:

```sh
python tools/memory_sync.py --scope marcasalao --apply --server-url http://127.0.0.1:49374
python tools/memory_sync.py --scope multitrackhub --apply --server-url http://127.0.0.1:49374
python tools/memory_sync.py --scope general --apply --server-url http://127.0.0.1:49374
```

URL-base sem /mcp; HTTPS obrigatório para destinos remotos. A importação não usa
retry automático e não segue redirects. Uma falha pode deixar um lote parcial:
reexecutar é seguro para páginas idênticas. Saídas: created, unchanged ou conflict.
Exit codes: 0 sucesso/plano; 1 falha; 2 conflitos (ou uso inválido de argumentos).
Páginas existentes diferentes nunca são sobrescritas, excluídas ou desfixadas.

Para atualizar uma página conflitante, ler memory_read_page no escopo correto,
revisar a diferença e escrever com expected_page_id igual ao page_id retornado.
Não apagar a página para contornar o conflito. Atualizar também a fonte no Git
quando a mudança for uma regra ou decisão oficial. Exclusões no Git não apagam
memória automaticamente. A importação inicial é explícita; não há sync contínuo.

## Verificação e continuidade

Chamada MCP de exemplo:

```json
{"name":"memory_query","arguments":{"workspace":"marketing","project":"marcasalao","query":"CTA arte quadrada","pin_first":true}}
```

Conferir memory_briefing e abrir as páginas retornadas. Buscar identidade da outra
marca não deve retornar páginas exclusivas dela neste escopo. Escopos organizam
conteúdo; para impor acesso a operadores diferentes, configurar grants no servidor.
As páginas comuns são deliberadamente replicadas e podem divergir até reconciliação.

AGENTS.md e instruções atuais continuam governando o trabalho. Memória não autoriza
publicação, agendamento, gasto de API ou reutilização de aprovação.
Consultar o serviço atual e validar evidências antes de agir.
Handoffs são temporários e consumidos uma vez; regras/decisões ficam em páginas.

As exclusões capture.ignore_paths são filtros de melhor esforço para ferramentas
reconhecidas, não impedem que alguém cole segredos num prompt. Não importar
transcripts privados nem habilitar captura ampla sem revisar a instalação.

Testes locais:

```sh
python -m unittest discover -s tools/tests -p "test_memory_sync.py" -v
```

## Referências

- https://github.com/akitaonrails/ai-memory/blob/main/docs/marker-file.md
- https://github.com/akitaonrails/ai-memory/blob/main/docs/programmatic-memory.md
- https://github.com/akitaonrails/ai-memory/blob/main/docs/support-matrix.md
- https://github.com/akitaonrails/ai-memory/blob/main/DATA_HANDLING.md
