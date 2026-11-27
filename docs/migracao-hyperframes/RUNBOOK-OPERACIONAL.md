# Runbook operacional — motor HyperFrames (HF-001)

Operação diária do novo motor na estação de trabalho. Todos os comandos partem da
raiz do checkout (`<RAIZ>` = `git rev-parse --show-toplevel` da estação).

## Regra zero: sempre pelos wrappers

```bash
# CLI HyperFrames com env confinado (caches/temp dentro de <RAIZ>):
bash renderers/hyperframes/scripts/hf.sh <comando>

# CLI contra um projeto de composição específico:
bash renderers/hyperframes/scripts/hf-project.sh <dir-do-projeto> <comando>
```

- **Nunca** rodar `npx hyperframes` cru (usa caches fora de `<RAIZ>`).
- **Nunca** fazer `source config/env.sh` em shell interativo: ele sobrescreve
  `HOME`/`USERPROFILE` para confinar caches e **quebra a identidade Git da sessão**.
  O env é propriedade dos wrappers.

## Ciclo de produção (caminho novo)

1. **Brief → pacote:** produzir `VideoRequest` pelo fluxo existente
   (`tools/produce/produce_video.py` ou Studio) e derivar o
   `CreativeExecutionPackage` (contratos `platform/`).
2. **Seleção explícita:** manifest com `renderer.adapter: "hyperframes"`.
3. **Adaptador:** materializa a composição, valida guardrails, roda `check` e
   `render` (draft para iteração; delivery para entrega).
4. **Verificação de entrega (obrigatória):**

   ```bash
   .workspace/tools/ffmpeg/ffprobe -v error -show_format -show_streams out.mp4
   ```

   Aceite: 1 stream de vídeo (h264, geometria do perfil), **0 streams de áudio**,
   duração conforme plano. Textos gráficos legíveis nos snapshots; áreas seguras
   respeitadas.

5. **Narração:** TXT por cena e tempos em `04-legendas/` (obrigatório no modo
   clean). SRT somente sob pedido expresso.

## Studio e fila (F7/F8)

No Video Studio, a seleção do motor é **explícita por trabalho** e não muda o
caminho legado (MKT-VIDEO-003: sem fallback silencioso):

```bash
# 1. Selecionar o motor no trabalho (valida runtime antes de aceitar):
curl -X POST .../api/works/renderer/save \
  -d '{"workId": "<id>", "renderer": {"adapter": "hyperframes"}}'

# 2. Confirmar runtime/versão:
curl .../api/hyperframes/readiness

# 3. Fila: a modalidade "hyperframes" aparece no plano somente quando o
#    trabalho seleciona o motor; preflight exige ffmpeg/ffprobe + runtime:
curl -X POST .../api/queue/preflight \
  -d '{"items": [{"workId": "<id>", "modality": "hyperframes", "profileId": "<perfil>"}]}'

# 4. Enfileirar como qualquer item (mesma fila SQLite, mesmos estados):
curl -X POST .../api/queue/enqueue -d '{"items": [ ... ], "label": "..."}'
```

- Entrega promovida em `works/<id>/deliveries/hyperframes/<perfil>/` com
  `delivery-manifest.json` (mesmo contrato da fila; `captionsMode: clean`,
  `renderer.adapter: hyperframes`, sem SRT).
- Revisão/empacotamento inalterados: peça `hyperframes:<perfil>`, decisão
  `approved_for_local_delivery`, ZIP com `primary-output.mp4` + `narration.txt`.
- Item de fila `hyperframes` congela `tenantId` (guardrails por marca) e
  `renderer` no snapshot; falha do adaptador → item `failed` com
  `GUARDRAILS_VIOLATION`/`ADAPTER_*` no log — nunca reprocessa em FFmpeg.
- Trabalhos antigos: `renderer` ausente = `ffmpeg` (padrão); nada muda para
  eles.

## Diagnóstico rápido

| Sintoma | Primeiro passo |
| --- | --- |
| Render falha com erro de Chrome | `bash renderers/hyperframes/scripts/hf.sh doctor --json`; se Chrome ausente: `... hf.sh browser ensure` |
| `check` não abre browser / timeout na primeira vez | Download do Chrome pinado pendente: rodar `browser ensure` uma vez |
| FFmpeg/FFprobe não encontrados | Confirmar `.workspace/tools/ffmpeg/` presente; o env o coloca no PATH automaticamente |
| Falha de cache/permission | Verificar que o comando rodou via wrapper; caches vivem em `<RAIZ>/.workspace/tmp/hf001/` |
| Job `failed` na fila | Ler o log do item no Studio; **não** reprocessar em FFmpeg por conta própria |
| Suíte de testes longa expira | Rodar suítes separadas (`--smoke`, `--fast`, `--render`), nunca combinadas |

## Fallback operacional (decisão humana)

O render local FFmpeg (`tools/produce/render_pipeline.py`/`render_local.py`, com
`--clean`) permanece instalado e testado como **plano B**. Usá-lo é uma decisão
explícita do titular/operador — registrada no item/handoff — **nunca** uma recaída
automática do adaptador (MKT-VIDEO-003). Motivos típicos: Chrome indisponível na
estação, regressão do motor, prazo crítico de campanha.

## Recuperação da fila

- Fila: `.workspace/studio/production-queue.sqlite` (estados
  `queued/running/completed/failed/cancelled/interrupted`).
- Reinício do Studio executa `recover_on_startup`: itens `running/interrupted` da
  sessão anterior são reconciliados; snapshots SHA-256 preservam integridade.
- Job HyperFrames travado: cancelar o item pelo Studio (estado `cancelled`),
  corrigir a causa, submeter novamente — não matar o processo à mão sem depois
  reconciliar a fila.

## Atualização do motor

Ver [ATUALIZACOES-E-ROLLBACK.md](ATUALIZACOES-E-ROLLBACK.md). Resumo: versão pinada
0.9.103; upgrade é deliberado, testado (smoke + check) e registrado no README do
runtime e em EVIDENCIAS.

## Limpeza

- Render concluído e entregue: remover intermediários do job em
  `<RAIZ>/.workspace/tmp/hf001/` quando não precisarem de preservação.
- O download do Chrome pinado (~717 MB) fica em cache e **não** é removido entre
  tarefas (re-download é caro); `hf.sh browser clear` só em manutenção deliberada.
- Ao final da tarefa: checklist de limpeza do AGENTS.md (worktrees, temporários,
  `git status --short`, `git worktree list --porcelain`).
