# Operação do ai-memory no marketing

Ativação verificada em 31/10/2026, America/Sao_Paulo, usando ai-memory 3.3.0.

## Serviço e conexão

O Servidor02 mantém a base compartilhada em serviço systemd do usuário swn:
ai-memory.service habilitado e ativo, com linger já habilitado. O servidor escuta
somente em 127.0.0.1:49374. Wiki, índice e credenciais ficam no diretório privado
de dados do ai-memory, fora do repositório público.

No Windows, a tarefa de logon AiMemory-Servidor02-Tunnel mantém um túnel SSH para
o mesmo servidor em 127.0.0.1:49375. A tarefa executa sem janela e tem reinício
configurado em caso de falha. A sessão SSH depende do acesso servidor02 já
configurado neste computador; uma futura expiração desse acesso requer renovar
a autenticação SSH/Cloudflare. Não há uma segunda base independente no Windows.

O diretório de dados do cliente Windows é redirecionado pelo pacote do Codex.
A tarefa de logon aponta para o caminho físico do script nesse diretório.
A autenticação usa arquivo privado com permissões do titular/SYSTEM; nenhuma
credencial foi adicionada ao repositório ou aos arquivos de configuração MCP.

Embeddings e provedor LLM permanecem desativados no servidor. A importação
automática de históricos anteriores e o esquecimento automático também estão
desativados. Captura é allowlist: exige marcador .ai-memory.toml.

## Agentes

Codex no Windows e no Servidor02: MCP por stdio bridge, sete eventos de hooks
instalados e aprovados pela interface de revisão do próprio Codex.
As skills de consulta, páginas duráveis e continuidade foram instaladas.

Hermes: seis hooks por perfil, MCP e skills configurados nos homes do perfil
padrão Marca Salão e multitrackhub-marketing. Os pares exatos de evento/comando
foram aprovados via mecanismo de consentimento do Hermes, sem habilitar aprovação
automática de hooks arbitrários. O hook anterior de proteção de mídia Marca
Salão foi preservado. O gateway foi reiniciado e voltou ao estado ativo.

Os homes e os checkouts de trabalho dos dois bots têm marcadores explícitos:
workspace marketing, projetos marcasalao e multitrackhub. O workspace local
deste chat usa marcasalao-marketing. Clientes MCP estáticos informam sempre
workspace e project juntos.

Reiniciar instâncias do Codex já abertas para carregar o MCP e os hooks novos.
O servidor e os perfis Hermes já estão em funcionamento.

## Verificação realizada

- Health check respondeu status ok pelo túnel Windows.
- As 42 páginas iniciais foram importadas na base permanente, incluindo 24 campanhas.
- Consultas MCP por marca retornaram suas regras e decisões.
- Hooks Hermes executados com payload técnico: início, prompt e encerramento.
  A base confirmou uma sessão e três observações em cada escopo de marca.
- Execução real do Codex com pedido técnico de responder OK confirmou captura.
- Doctor confirmou os seis hooks de cada perfil Hermes aprovados.
- Handoffs dos testes foram cancelados por ID, preservando a evidência de captura.

A memória contém evidências históricas e não concede autorização para publicar,
agendar ou gerar campanhas. Estados operacionais continuam exigindo verificação
no Postiz.

## Manutenção

No Servidor02:

```sh
systemctl --user status ai-memory.service
systemctl --user is-enabled ai-memory.service
ai-memory doctor --workspace marketing --project marcasalao
ai-memory doctor --workspace marketing --project multitrackhub
hermes hooks list
HERMES_HOME=/home/swn/.hermes/profiles/multitrackhub-marketing hermes hooks list
```

No Windows, conferir a tarefa AiMemory-Servidor02-Tunnel e o health check
http://127.0.0.1:49375/healthz. Usar o binário instalado pelo caminho absoluto
se o terminal atual ainda não tiver atualizado o PATH.

Backups privados das configurações Hermes e do servidor foram preservados no
diretório deploy-backups da instalação. A configuração anterior do cliente
Windows foi copiada antes da alteração. Restaurar somente os trechos relativos
a esta integração e conferir alterações posteriores antes de qualquer rollback.
