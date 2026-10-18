# Gestão financeira — Marca Salão

Status: RASCUNHO — NÃO PUBLICADO E NÃO AGENDADO.

Preparado em 18/10/2026 exclusivamente para Marca Salão — Facebook Meu salão e Marca Salão — Instagram @marcasalao no Postiz. Publicação exige autorização posterior do titular.

## Arquivos
- marcasalao-gestao-financeira.png: arte quadrada na identidade MS/tesoura, verde-petróleo, menta e branco.
- legenda.txt: legenda para os dois canais.

## Validação do conteúdo
Referência pública: https://marcasalao.com.br, recurso Gestão Financeira.
Código consultado em Jonatasbottaro/Salao02:
- src/app/(dashboard)/gestor/financeiro/page.tsx redireciona para /gestor/finances.
- src/app/(dashboard)/gestor/finances/page.tsx apresenta resumo e transações recentes.
- src/app/(dashboard)/gestor/_components/financial/FinancialOverview.tsx mostra receita, ticket médio e seleção Hoje / Esta Semana / Este Mês.
- src/app/(dashboard)/gestor/_lib/financial/services.ts calcula receita e ticket médio a partir de atendimentos COMPLETED no período; histórico recente reúne até 20 registros com pagamento PAID, independentemente do período escolhido.
A legenda mantém essa distinção: métricas de atendimentos concluídos e registros recentes de pagamentos. Não afirma que receita equivale a saldo bancário ou lucro.
Leitura de código sem teste funcional completo do painel. Nenhum dado financeiro de cliente real foi acessado ou exposto. Sem promessas de crescimento, controle de despesas/comissões não verificado, conciliação bancária ou contabilidade automatizada.

## Produção visual
Gerada com image_gen integrado usando o primeiro post aprovado como referência.
Prompt resumido: square marketing post, Marca Salão MS/scissors logo, petroleum teal, pale mint, white; headline Mais clareza nas finanças do seu salão.; three features Receita por período / Ticket médio / Transações recentes; mint calculator and paper planner on marble salon counter; CTA Conheça o Marca Salão and marcasalao.com.br; no invented UI, numbers, growth charts or other brands.

Multitrack Hub e anúncios preservados.
