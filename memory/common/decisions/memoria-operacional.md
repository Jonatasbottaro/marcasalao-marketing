# Memória operacional em ai-memory

A integração mantém páginas iniciais revisáveis em memory/ e importa-as por MCP. A wiki privada e o índice SQLite ficam no diretório de dados do ai-memory. O índice pode ser reconstruído; não copiar o banco nem o histórico privado para o Git público.

Workspace: marketing. Projetos: marcasalao-marketing para trabalho geral, marcasalao e multitrackhub para cada marca. Consultas e gravações programáticas sempre informam workspace e project juntos. Busca global só quando o pedido exigir comparação entre marcas.

As páginas de campanha são snapshots do README oficial com referência ao commit. Não expiram automaticamente. Alterações remotas diferentes são reportadas como conflito para revisão; o importador inicial não as sobrescreve.

Fonte: pedido de integração nesta conversa e memory/README.md.

