# Portal de Revisão — Content Factory Multi-Tenant

Portal estático de revisão humana das campanhas renderizadas pela fábrica
multi-tenant. Consolidado por `tools/review_dashboard.py` a partir de:

- `tenants/*/brand-kit.json` e `tenants/*/guardrails.json`
- `02-reels-shorts/deliveries/<tenant>/<slug>/` (`manifest.json`, `<slug>.srt`,
  `<slug>_narracao.txt`, `preview-storyboard.png` e, quando existirem,
  `cover.png`, `preview-formats.png` e `derivatives.json`)
- `04-legendas/pacotes-publicacao/<tenant>/<slug>/`
  (`checklist-publicacao.json` e copies por rede)

Estado consolidado nesta geração: **5 tenants**
(clinica-vital, estudio-flow, marca-salao, meu-salao, multitrack-hub) e **11 campanhas**.

## Gerar

```
python tools/review_dashboard.py --build [--json]
```

Gera `index.html`, `portal-data.json` e este `README.md`. O build é
**determinístico**: não grava timestamps e produz bytes idênticos para os
mesmos insumos, em qualquer estação. Hashes SHA-256 de SRT, narração e
storyboard são verificados contra o `manifest.json` de cada entrega; qualquer
divergência aborta o build com `HASH_DIVERGENTE`. `portal-data.json` contém
apenas caminhos relativos contidos na raiz (nenhum caminho absoluto de
estação), mantendo o portal portátil.

## Servir (recomendado)

```
python tools/review_dashboard.py --serve [--port 8765] [--host 127.0.0.1]
```

Reconstrói o portal na inicialização e sobe um servidor HTTP local em
`http://127.0.0.1:8765/` (somente leitura, vinculado a 127.0.0.1, sem
dependências externas). Endpoints:

- `GET /` e `GET /portal-data.json` — o portal e seus dados.
- `GET /api/health` — `{"ok": true, "tenants": N, "campaigns": M}`.
- `GET /api/data` — `portal-data.json` atualizado.
- `GET /media/storyboard/<tenant>/<slug>` — `preview-storyboard.png`.
- `GET /media/cover/<tenant>/<slug>` e `GET /media/formats/<tenant>/<slug>`
  — `cover.png` e `preview-formats.png`, quando existirem na entrega.
- `GET /media/video/<tenant>/<slug>/<variante>` — streaming do MP4 preservado
  em `.workspace/archives/<slug>/` (variante primária derivada da geometria;
  derivadas `1x1`/`16x9` via `derivatives.json` ou convenção de nomes), com
  suporte a `Range` (206/416).
- `GET/POST /api/approvals` — lê e persiste as decisões do titular em
  `.workspace/tmp/aprovacoes-titular.json` (schema estrito v2: decisão em
  `aguardando`/`aprovado`/`ajuste`, locução externa conferida, observações e
  hashes SHA-256).

## Exportar aprovações

```
python tools/review_dashboard.py --export-aprovacoes
```

Emite no stdout o conteúdo atual de `aprovacoes-titular.json` (schema v2)
para redirecionar a um arquivo ou anexar ao handoff. Sem arquivo persistido,
encerra com `APROVACOES_AUSENTES`.

## Interface

- **Painel de métricas:** nichos, campanhas, vídeos `-an` × `AAC`,
  conformidade de guardrails e contadores dinâmicos de aprovados, pendentes
  e ajustes.
- **Filtros e busca:** tenant (com monograma e cor), preset, política de
  áudio, status de aprovação e busca textual por slug, título, legenda,
  roteiro ou rota.
- **Cartões por campanha:** paleta do tenant, storyboard 2×2 (com lightbox),
  player por variante quando servido, abas **Legenda .srt** (blocos numerados
  com timecodes), **Narração**, **Instagram/YouTube/Facebook** (copy completa,
  contador de caracteres, URL UTM destacada e botões Copiar) e
  **Guardrails & Hashes** (rotas autorizadas, claims bloqueados,
  `autoPublish: false` e hashes SHA-256).
- **Controle editorial:** decisão por campanha (Aguardando Revisão, Aprovado
  para Publicação Manual, Solicitar Ajuste), conferência de locução externa
  para tenants `-an` e observações do titular — salvos no `localStorage`
  (chave `reviewPortal.aprovacoes.v2`) e sincronizados via
  `POST /api/approvals` quando o portal é servido.
- **Exportar/Importar:** botões que baixam `aprovacoes-titular.json` e
  reimportam um JSON de aprovações.

## Segurança do servidor

- Somente `GET`/`HEAD`; métodos de escrita são recusados, exceto
  `POST /api/approvals` (validação estrita de schema, corpo limitado a 1 MB).
- Rotas restritas: portal, `/api/*`, `/media/*`, `/deliveries/<caminho>`
  (PNG/SRT/TXT/JSON/MD das entregas) e `/archives/<slug>/<arquivo>.mp4`
  (legado, com `Range`).
- Todo caminho é decodificado e confinado à raiz permitida: `..`, `\`,
  caminhos absolutos e UNC recebem 404; extensões fora da lista permitida
  também são recusadas.
- Os MP4s **não são versionados** (`.workspace/archives/` é local por
  estação): quando a raiz é uma worktree, o servidor localiza a raiz
  principal via `git rev-parse --git-common-dir` para alcançar os vídeos;
  se o arquivo não existir na estação, o player cai no storyboard com aviso.
