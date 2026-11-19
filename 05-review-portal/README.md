# Portal de Revisão — Content Factory Multi-Tenant

Portal estático de revisão humana das campanhas renderizadas pela fábrica
multi-tenant. Consolidado por `tools/review_dashboard.py` a partir de:

- `tenants/*/brand-kit.json` e `tenants/*/guardrails.json`
- `02-reels-shorts/deliveries/<tenant>/<slug>/` (`manifest.json`, `<slug>.srt`,
  `<slug>_narracao.txt`, `preview-storyboard.png`)
- `04-legendas/pacotes-publicacao/<tenant>/<slug>/`
  (`checklist-publicacao.json` e copies por rede)

Estado consolidado nesta geração: **4 tenants**
(estudio-flow, marca-salao, meu-salao, multitrack-hub) e **8 campanhas**.

## Gerar

```
python tools/review_dashboard.py --build [--json]
```

Gera `index.html`, `portal-data.json` e este `README.md`. O build é
**determinístico**: não grava timestamps e produz bytes idênticos para os
mesmos insumos, em qualquer estação. Hashes SHA-256 de SRT, narração e
storyboard são verificados contra o `manifest.json` de cada entrega; qualquer
divergência aborta o build com `HASH_DIVERGENTE`.

## Servir (recomendado)

```
python tools/review_dashboard.py --serve [--port 8765]
```

Sobe um servidor HTTP local em `http://127.0.0.1:8765/` (somente leitura,
vinculado a 127.0.0.1, sem dependências externas). Quando servido, cada
cartão exibe o player `<video>` com o MP4 preservado em
`.workspace/archives/<slug>/` (com suporte a Range/seek). Aberto direto do
disco (`file://`), o portal funciona com o storyboard 2×2 como prévia.

Os MP4s **não são versionados** (`.workspace/archives/` é local por estação):
se o arquivo não existir na estação, o player cai no storyboard com aviso.

## Interface

- **Filtros:** tenant, preset (`saas-demo` × `shorts-completo`) e política de
  áudio (`-an` sem áudio × `AAC` com áudio).
- **Cartões por campanha:** paleta do tenant, storyboard 2×2 (e player quando
  servido), abas **Legenda .srt**, **Roteiro de Narração**, **Copy
  Instagram/YouTube/Facebook** com botões "Copiar" e links UTM rastreados.
- **Checklist de aprovação humana:** itens por campanha, revisor e observações,
  persistidos no `localStorage` do navegador (chave
  `reviewPortal.aprovacoes.v1`).
- **Exportar JSON de Aprovações:** botão no cabeçalho que baixa
  `aprovacoes-titular.json` com todas as campanhas, estado de cada item do
  checklist, `aprovada` (true quando todos os itens marcados), revisor,
  observações e hashes SHA-256 para rastreabilidade — compatível com o fluxo
  manual de aprovação do titular.

## Segurança do servidor

- Somente `GET`/`HEAD`; métodos de escrita são recusados.
- Rotas restritas: `/` e `/portal-data.json` (portal),
  `/deliveries/<caminho>` (storyboards e textos das entregas) e
  `/archives/<slug>/<arquivo>.mp4` (vídeos, com `Range`).
- Todo caminho é decodificado e confinado à raiz do checkout: `..`, `\`,
  caminhos absolutos e UNC recebem 404; extensões fora da lista permitida
  também são recusadas.
- `portal-data.json` contém apenas caminhos relativos contidos na raiz
  (nenhum caminho absoluto de estação), mantendo o portal portátil.
