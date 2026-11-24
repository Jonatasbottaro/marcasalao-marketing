# Auditoria de identidade visual — NS-001 (24/11/2026)

Natureza: recomendação fundamentada para decisão do titular. **Nenhum arquivo de marca ou contrato foi alterado** (`tenants/marca-salao/brand-kit.json` intacto; produto intacto).

## 1. Fontes consultadas

| Fonte | O que registra | Estado |
| --- | --- | --- |
| `tenants/marca-salao/brand-kit.json` | Paleta técnica: primary `#F5C107` (amarelo), secondary `#4F8CFF` (azul), accent `#28B463` (verde), background `#121620`, surface `#222C40`, textPrimary `#F5F7FA`, textMuted `#B4C0D2`; tipografia **Arial bold**; monograma `MS`, displayTitle `MARCA SALAO`; header overlay 170 px que substitui o label legado "Meu Salão"; legendas ASS Arial 12 branco/outline preto 2, MarginV 34 | Contrato técnico vigente da fábrica |
| Briefing NS-001 §10/§14 | "identidade verde-petróleo, menta e branco, logo MS/tesoura, conforme as artes aprovadas" | Texto do briefing v0.3 (em validação) |
| Arte aprovada e PUBLICADA mais recente: `marcas/marcasalao/posts/2026-11-01-troca-profissional-combinado/arte-compartilhada-quadrado.png` (inspecionada visualmente nesta auditoria) | Parede **verde-petróleo**, destaques **menta**, texto **branco**, logo **MS/tesoura** centralizado, nome "Marca Salão", título grande em sans bold, três tópicos com ícones circulares menta, CTA neutra "Conheça o Marca Salão" + domínio | PUBLICADO em 01/11/2026 (README com IDs e links) |
| Segunda referência aprovada: `2026-10-31-conforto-tambem-e-cuidado/` (README) | Mesmo padrão visual preservado | PUBLICADO em 31/10/2026 |
| `VALIDACAO-EXECUCAO-2026-11-05.md` §6 | Interface do produto exibe "**Meu Salão**" (sidebar e título) | Pendência editorial de marca registrada |
| Postiz (histórico remoto) | **Sem acesso autorizado nesta estação** — não inventado; referências usadas são as artes versionadas com estado PUBLISHED registrado | Limitação declarada |

## 2. Divergências registradas (não resolvidas silenciosamente)

1. **Paleta:** artes públicas aprovadas = verde-petróleo/menta/branco; brand-kit técnico = amarelo/azul/verde/fundo escuro. São dois sistemas visuais coexistindo: o do feed publicado e o dos overlays/legendas da fábrica de vídeo.
2. **Tipografia:** artes públicas usam sans geométrica bold; contrato de legendas/overlay da fábrica é Arial bold.
3. **Nome público:** interface do produto "Meu Salão" × campanha "Marca Salão". O brand-kit já mitiga parcialmente via header overlay que substitui o label legado na composição da fábrica; a gravação bruta da sidebar ainda mostraria "Meu Salão".
4. **Logo:** artes públicas usam MS/tesoura em medalhão; brand-kit registra monograma `MS` sem arquivo de imagem.

Nenhuma dessas divergências é declarada "errada": dependem de decisão oficial do titular (briefing §14; execução §6).

## 3. Padrão visual recomendado para NS-001 (proposta)

**Opção A (recomendada):** identidade pública aprovada nas artes de abertura/situação/CTA e no fundo das composições; brand-kit mantido como contrato técnico de legendas ASS e geometria de overlay da fábrica até decisão de unificação.

- **Cores:** fundo verde-petróleo (referência visual das artes publicadas; hex exato a extrair da arte aprovada na produção), destaque menta, texto branco; nada de amarelo/azul do brand-kit nas artes públicas desta campanha.
- **Tipografia:** sans bold de alto peso para títulos de cena (padrão das artes); Arial bold para legendas queimadas conforme contrato ASS vigente.
- **Logotipo:** MS/tesoura em medalhão no topo das cenas 1 e 7, como nas artes aprovadas.
- **Cabeçalho:** overlay da fábrica (170 px) sobre a gravação do produto, conforme brand-kit; recorte da gravação exclui a sidebar com "Meu Salão" enquanto a decisão de nome não existir.
- **Contraste:** branco sobre verde-petróleo (alto); menta apenas como destaque, nunca como cor de texto longo.
- **Destaque das funções demonstradas:** realce suave (círculo/underline menta) sobre o controle acionado; sem redesenhar a interface.
- **Área segura de legendas:** faixa y ≈ 1450–1650 em 1080×1920 (fora dos ~250 px inferiores de UI das plataformas); MarginV 34 do contrato ASS respeitado na faixa de legendas da fábrica.
- **Área segura de elementos da plataforma:** nada essencial nos ~150 px do topo nem nos ~120 px da direita.
- **Transições:** corte seco ou crossfade ≤ 0,3 s; sem efeitos que distorçam o produto.
- **Padrão de CTA:** neutra na imagem ("Conheça a agenda do Marca Salão." + domínio); orientação de link por canal somente na legenda (AGENTS.md); sem botão clicável desenhado.
- **Comportamento por formato:** master 9:16 (1080×1920, 30 fps); derivados 1:1 e 16:9 pela fábrica com reenquadramento (`framingByProfile`), mantendo textos e legendas nas áreas seguras de cada formato.

**Opção B:** unificar tudo no brand-kit técnico — diverge do feed publicado e das referências de qualidade do AGENTS.md; não recomendada sem decisão explícita.
**Opção C:** atualizar o brand-kit para a paleta pública — exige autorização específica, regressão dos renders e revisão dos contratos; fora do escopo desta rodada.

## 4. Pendências de aprovação

1. Escolha do padrão visual público (A/B/C) e do nome oficial para uso público ("Marca Salão" × "Meu Salão").
2. Autorização para extrair hex/tipografia exatos da arte aprovada na produção.
3. Qualquer alteração de `brand-kit.json` ou da interface do produto: **proibida nesta rodada**, exige pedido separado.