# Especificacao Arquitetural — Fluxo Integrado de Provas de Campanha, Video Studio, ZIP e Backup

- **Data:** 2026-11-18
- **Status:** Aprovado (Revisao Goldfish EGM — Estagios 5 a 9 consolidados)
- **Escopo de Sistemas:** `tools/campaign_proof.py`, `tools/video_studio.py`, `tools/studio/` (UI Astryx e fallback legado), `tools/delivery_verify.py`, `tools/studio_work_backup.py`, `.github/workflows/local-render-validation.yml` e documentacao operacional de campanhas `NS-001` / `NS-002`.

---

## 1. Visao Geral e Problema Resolvido

Para produzir e validar campanhas locais do Marca Salao sem expor credenciais ou acionar publicacoes externas, o operador precisa de um ciclo local deterministico:

`preparar midia -> verificar prontidao (VideoRequest v1 + ProjectManifest) -> abrir no Video Studio -> enfileirar e renderizar sem audio -> revisar e aprovar entrega tecnica -> gerar e verificar ZIP -> restaurar em segundo workspace`.

As implementacoes parciais presentes antes desta especificacao apresentavam lacunas de integracao: preparacao de midias fora dos caminhos declarados no pedido, falso positivo de prontidao (`ready: true`) sem manifesto ou arquivos fisicos, mascara de erros na chamada de render e HTML de revisao estatico, ausencia de selecao dinamica de pedidos exemplo no Video Studio, e inconsistencias em documentos de mensuracao/destinos.

### Glossario Minimo

- **`VideoRequest v1` / `ProjectManifest`**: contratos validados em Node/TypeScript (`platform/src/`) e compilados via `tools/render_bridge.mjs`.
- **Midia sintetica de prova**: arquivo gerado localmente sem rede nem dados reais, marcado visual e estruturalmente (`"PROVA FICTICIA"`) para nao ser confundido com capturas oficiais.
- **Astryx / Video Studio**: interface React servida por `tools/video_studio.py` quando `tools/studio/frontend/dist/` esta compilada, substituindo containers legados na inicializacao.
- **`<RAIZ>` e `.workspace/`**: raiz do checkout Git e diretorio local ignorado pelo Git onde ficam worktrees, caches portateis, rascunhos, trabalhos e entregas preservadas.

---

## 2. Objetivos, Limites e Nao-Objetivos

### Objetivos

1. Garantir que `tools/campaign_proof.py` prepare, valide via `platform`, renderize via `tools/produce_video.py`, inspecione entregas reais e gere pagina HTML portavel com links relativos e textos escapados.
2. Preservar integralmente midias fornecidas pelo operador em `media[].path`, sobrescrevendo apenas arquivos ausentes ou marcados como prova sintetica gerada pela ferramenta.
3. Permitir criacao/abertura generica de qualquer exemplo `*.video-request.json` no Video Studio via `/api/examples`, sem acoplar campanhas especificas em codigo compartilhado, e isolar o modo avulso legado na UI.
4. Validar tecnicamente as campanhas piloto `NS-001-P001` (7 cenas, 30 s) e `NS-002-P001` (6 cenas, 30 s) sem audio (`-an`), com `.srt` e `.txt` de narracao, provando ZIP (`delivery_verify.py`) e portabilidade de backup/restauracao (`studio_work_backup.py`).

### Limites Operacionais

- Todos os arquivos temporarios, caches de build/npm, navegador e entregas ficam estritamente sob `<RAIZ>/.workspace/`.
- O indicador principal `readiness["ready"]` de `video_studio.py --check` permanece atrelado as 5 ferramentas essenciais (`python`, `node`, `platformBuild`, `ffmpeg`, `ffprobe`) para preservar compatibilidade com pipelines existentes; diagnostico do frontend e comandos recomendados sao expostos de forma aditiva.
- Renders completos multi-perfil sao executados para provas locais e arquivos preservados; a validacao automatica de CI prioriza compilacao estrutural de todos os perfis e render do perfil primario para manter tempo de build previsivel.

### Nao-Objetivos e Restricoes Permanentes

- Proibida geracao, preservacao ou inclusao de faixa de audio nos videos (`AGENTS.md` e `WORKFLOW.md`).
- Proibida aprovacao editorial automatizada, publicacao, agendamento, criacao de rascunhos externos no Postiz ou alteracao de analytics de producao.
- Sem alteracao nos contratos centrais em `platform/`.

---

## 3. Arquitetura e Fronteiras de Dados

```text
[Pedido VideoRequest v1 + ProjectManifest]
   |
   +--> campaign_proof.py
   |      |-- prepare: gera ou preserva em media[].path ("PROVA FICTICIA" + marcador PNG tEXt antes de IDAT)
   |      |-- verify: checa arquivos fisicos + delega validacao/compilacao a produce_video.run_bridge_video_request
   |      |-- render: executa produce_video.py (--attempt-id); consulta index.json e delivery-manifest.json
   |      '-- review: gera HTML escapado responsivo consumindo entregas/miniaturas por caminhos relativos
   |
   +--> tools/video_studio.py + Studio UI (Astryx React)
          |-- GET /api/examples descobre *.video-request.json dinamicamente
          |-- Studio.create_work aceita videoRequestPath / template="example:<id>" e copia midias para <workDir>/media/
          |-- fila SQLite + preflight -> Revisao & Entrega -> ZIP + delivery_verify.py
          '-- studio_work_backup.py: portabilidade entre workspaces (dependencias ProjectManifest / sharedMedia)
```

### Contratos e Invariantes

1. **Fonte unica de verdade de contrato (`platform/`):** a ferramenta Python nao reimplementa regras do schema `VideoRequest v1` / `VisualStyle v1`; limita-se a leitura JSON UTF-8, contencao sob `root`, presenca fisica de `ProjectManifest` e midias, delegando regras semanticas e geometria de perfis ao `render_bridge.mjs` via `produce_video.run_bridge_video_request`.
2. **Fonte unica de estado de render (`index.json` + `delivery-manifest.json` + `report.json`):** `campaign_proof.py` nao mantem manifestos paralelos por perfil. Falhas de `produce_video.py` (incluindo saidas `1/2/3` em `stderr`) sao reportadas explicitamente preservando `lastValidDelivery` registrada em `index.json`.
3. **Preservacao de midia real:** arquivos existentes em `media[].path` nunca sao sobrescritos por inferencia de metadados do JSON (como `origin: "synthetic-demo"`); somente ausencia em disco, pedido explicito (`--force`) ou assinatura sintetica propria no arquivo autoriza regeneracao.
4. **Portabilidade do HTML de revisao:** textos e saidas externas sao sempre escapados; arquivos ja contidos no diretorio do HTML usam caminho relativo direto (`relpath`), enquanto ativos externos sao copiados para subpastas locais validadas.
5. **Desacoplamento de campanhas no Studio:** `WorksAndProjectsTab.jsx` e `video_studio.py` resolvem campanhas de exemplo dinamicamente via `/api/examples`, preservando o catalogo de marca neutro em `BRAND_EXAMPLES`.

---

## 4. Decisoes Reversiveis e Modos de Falha

- **Modo avulso vs. trabalho aberto (`tools/studio/app.js`):** carregar um exemplo ou rascunho avulso desvincula explicitamente `currentWork` em vez de misturar payloads novos com pastas de entrega de um trabalho ativo. *Reversivel:* restrito aos handlers de carga avulsa na UI legada.
- **Unificacao do dono de verificacao de ZIP (`ReviewPackagePanel.jsx`):** como `main.jsx` limpa os containers legados quando o bundle React esta presente, a verificacao interativa de ZIP e mantida na UI React e testada na API `/api/works/package/verify` + `tools/delivery_verify.py`, sem duplicar maquinas de estado em JavaScript legado. *Reversivel.*
- **Falha de ferramentas de video (`render_local.ensure_video_tools`):** ausencia de FFmpeg/FFprobe degrada para estado explicitamente pendente em verificacao/render e falha apenas quando `REQUIRE_RENDER=1` e exigido nos testes.
- **Portabilidade Windows / caminhos longos:** operacoes de sistema de arquivos utilizam `render_local.fs_path` e decodificacao UTF-8 explicita em subprocessos.

---

## 5. Criterios de Aceite

1. **`campaign_proof.py` ponta a ponta:** `prepare` preserva midias reais de operador e gera substitutos nos caminhos do contrato; `verify` retorna `ready=false` quando `ProjectManifest` ou midias faltam; `render` reflete tentativas atuais sem apagar entrega anterior em caso de erro; `review` renderiza HTML escapado, responsivo (`1280x800` e `390x844` sem overflow horizontal) e funcional apos mover a pasta.
2. **Provas NS-001 e NS-002:** entregas multi-perfil com `0` faixas de audio, duracao exata de `30 s` dentro da tolerancia, `.srt` e `.txt` de narracao validos.
3. **Fluxo integrado Studio + ZIP + Backup:** abertura generica de pedido exemplo -> reload -> preflight -> fila -> revisao -> ZIP verificado (`delivery_verify.py`) -> edicao invalidando entrega e novo ZIP invalidando verificacao por SHA-256 anterior -> backup e restauracao em segundo workspace validando `ProjectManifest`, `sharedMedia`, exclusao de `review-state.json` e recusa em destino ja existente.
4. **Higiene documental e CI verde:** ausencia de `marcaselao.com.br` / `@marcaselao` e CSVs duplicados `exaivo-*`; `platform test`, `typecheck`, `unittest discover -s tools/tests -v` com `REQUIRE_RENDER=1` e workflows GitHub Actions aprovados em Ubuntu e Windows.

---

## 6. Referencias

- [AGENTS.md](../../AGENTS.md)
- [WORKFLOW.md](../../WORKFLOW.md)
- [README de Contexto](../contexto/README.md)
- [campaign_proof.py](../../tools/campaign_proof.py)
- [video_studio.py](../../tools/video_studio.py)
- [delivery_verify.py](../../tools/delivery_verify.py)
- [studio_work_backup.py](../../tools/studio_work_backup.py)
- [local-render-validation.yml](../../.github/workflows/local-render-validation.yml)
