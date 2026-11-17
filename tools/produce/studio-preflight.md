# Pré-voo de Produção do Video Studio (`studio_preflight.py`)

Diagnóstico local sob demanda para verificar se um trabalho salvo no Video Studio está pronto para exportação em uma modalidade e perfil específicos — sem enfileirar, renderizar ou alterar rascunhos, revisões e entregas.

## Uso

Com o servidor do Video Studio ativo em loopback (por exemplo `python tools/video_studio.py --port 8765`):

```bash
# Saída resumida em português
python tools/studio_preflight.py --port 8765 --work-id exemplo --modality video --profile instagram-reels-video

# Saída estruturada em JSON (stdout limpo para automação local)
python tools/studio_preflight.py --port 8765 --work-id exemplo --modality video --profile instagram-reels-video --json
```

Modalidades aceitas: `video`, `carousel`, `motion`.

## O que é verificado

1. **Ambiente (`environment`)**: Python, Node.js, build de `platform/dist/src/` e ferramentas locais exigidas pela modalidade (`ffmpeg`/`ffprobe` para `video` e `motion`; `ffmpeg` para `carousel`). Quando uma dependência está ausente, verificações dependentes aparecem como pendentes (`pendingChecks`).
2. **Trabalho e projeto (`work`, `project`)**: existência do trabalho salvo e do `ProjectManifest` associado.
3. **Perfil e allowlist (`profile`)**: existência no catálogo, compatibilidade com a modalidade, autorização em `outputProfiles` do projeto e suporte à exportação local (incluindo restrição `9:16` para `motion`).
4. **Rascunho salvo (`draft`)**: presença de cenas (`videoRequest`), cards (`carouselRequest`) ou efeitos (`motionPlan`), conforme a modalidade.
5. **Prévia do produtor (`preview`)**: execução da prévia oficial (`produce_video.py` / `produce_carousel.py` via `--plan-only --json`) para o destino pedido, incluindo `MotionPlan` quando `modality=motion` e detecção de overflow de texto em carrossel.
6. **Mídia referenciada (`media`)**: apenas os arquivos efetivamente usados por cenas ou cards; confinamento à raiz, existência em disco, divergência de hash SHA-256 quando houver hash esperado e duração/corte de vídeo via FFprobe. Cards de carrossel sem `mediaId` (apenas fundo/texto) são aceitos normalmente.

## Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Checagem concluída e destino **pronto** (`ready`) |
| `1` | Checagem concluída e destino **bloqueado** (`blocked`) |
| `2` | Erro de uso, endereço fora de loopback, Studio desligado, timeout ou resposta HTTP/JSON inválida |

## Exemplos de saída

### Destino pronto (exit `0`)

```text
PRONTO: exemplo [video / instagram-reels-video] - Destino pronto para producao local.
```

### Destino bloqueado (exit `1`)

```text
BLOQUEADO: exemplo [motion / youtube-video-horizontal] - Destino bloqueado (1 impedimento(s)): Motion local exige perfil vertical 9:16 (youtube-video-horizontal e 16:9).
Impedimentos:
  - [MOTION_LOCAL_UNSUPPORTED_GEOMETRY] (youtube-video-horizontal): Motion local exige perfil vertical 9:16 (youtube-video-horizontal e 16:9).
Proximos passos:
  - Selecione um perfil vertical 9:16 (ex.: instagram-reels-video) para Motion.
```

## Limites do diagnóstico

- O comando **apenas diagnostica**; enfileiramento e render continuam pelos fluxos normais (`POST /api/queue/enqueue` ou interface do Studio).
- Aceita exclusivamente endereços loopback (`127.0.0.1`, `localhost`, `::1`).
- Observa o estado salvo no momento da consulta: se o trabalho ou as mídias mudarem depois, a validação do snapshot congelado na fila continua sendo a decisão final no momento da produção.
- O endpoint HTTP equivalente é `POST /api/queue/preflight`, que também aceita um lote em `{"items": [{"workId": "...", "modality": "...", "profileId": "..."}]}` (`schemaVersion: 1`).
