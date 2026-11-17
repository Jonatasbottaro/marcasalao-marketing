# Studio Work Backup — Guia de uso

CLI de backup e restauração de um trabalho salvo do Video Studio.
Permite guardar uma cópia portátil e reabrir o mesmo trabalho em outro checkout compatível.

## Instalação

Nenhuma dependência extra. Requer Python 3.9+ e o repositório `Jonatasbottaro/marcasalao-marketing`.

```bash
# A partir da raiz do repositório
python tools/studio_work_backup.py --help
```

## Subcomandos

### `backup` — Criar um arquivo de backup

```bash
python tools/studio_work_backup.py backup <work-id> <saida.zip>
```

**Exemplo:**

```bash
python tools/studio_work_backup.py backup meu-anuncio-novembro .workspace/tmp/meu-anuncio-novembro.zip
```

**O que é incluído no ZIP:**

| Arquivo | Descrição |
|---|---|
| `work.json` | Configuração do trabalho (projeto, título, ID) |
| `editorial.json` | Ficha editorial e textos por canal |
| `planning.json` | Planejamento do trabalho |
| `media-library.json` | Referências da biblioteca de mídia |
| `drafts/video.request.json` | Rascunho de vídeo |
| `drafts/carousel.request.json` | Rascunho de carrossel |
| `drafts/motion.plan.json` | Plano de motion |
| `media/**` | Todos os arquivos de mídia do trabalho |
| `MANIFEST.json` | Manifesto interno (hashes, dependências) |

**O que é excluído (v1):**

- `review-state.json` (aprovações mantidas fora desta versão para evitar transporte acidental de estado aprovado)
- Credenciais e configurações de máquina
- `production-queue.sqlite` (fila de produção)
- Entregas renderizadas (`deliveries/`)
- Caches

---

### `inspect` — Verificar a integridade de um backup

```bash
python tools/studio_work_backup.py inspect <arquivo.zip> [--workspace <dir>]
```

**Exemplo:**

```bash
python tools/studio_work_backup.py inspect .workspace/tmp/meu-anuncio-novembro.zip
```

**Saída típica:**

```
=== Inspecao do backup ===
Trabalho : meu-anuncio-novembro
Exportado: 2026-11-17T10:30:00+00:00
Schema   : v1
Arquivos : 8

--- Arquivos no pacote ---
  OK             : .workspace/studio/works/meu-anuncio-novembro/work.json
  OK             : .workspace/studio/works/meu-anuncio-novembro/editorial.json
  ...

--- Dependencias ---
  OK [Manifest]       : platform/examples/projects/marca-salao-social.project.json
  OK [Midia]          : platform/examples/media/logo-compartilhado.png

Resultado: OK — backup integro e dependencias satisfeitas.
```

> [!IMPORTANT]
> A validação é **compartilhada** de forma idêntica entre `inspect` e `restore`:
> - Integridade interna do ZIP (tamanho e SHA-256 de cada entrada).
> - Restrição estrita: apenas arquivos permitidos do trabalho indicado podem constar no ZIP.
> - Presença e hash SHA-256 do `ProjectManifest` no checkout de destino.
> - Presença e hash SHA-256 de todas as **mídias compartilhadas** (arquivos fora da pasta do trabalho).

---

### `restore` — Restaurar um trabalho a partir de um backup

```bash
python tools/studio_work_backup.py restore <arquivo.zip> [--workspace <dir>]
```

**Restaurar no checkout atual:**

```bash
python tools/studio_work_backup.py restore .workspace/tmp/meu-anuncio-novembro.zip
```

**Restaurar em outro checkout:**

```bash
python tools/studio_work_backup.py restore \
  .workspace/tmp/meu-anuncio-novembro.zip \
  --workspace /outro/checkout/marcasalao-marketing
```

> [!NOTE]
> `--workspace` deve apontar para a **raiz de outro checkout compatível** do repositório,
> que precisa estar dentro da raiz do repositório conforme o `AGENTS.md`.

> [!CAUTION]
> A restauração **recusa expressamente** qualquer diretório de destino já existente,
> mesmo que vazio. Não há sobrescrita cega.

### Montagem segura (staging e publicação atômica)

1. A validação compartilhada roda antes de qualquer escrita. Se houver divergência ou dependência ausente, aborta imediatamente.
2. O trabalho é montado em um diretório temporário exclusivo (`.backup-staging-<work-id>-...`) no **mesmo sistema de arquivos** do destino final.
3. Todo o conteúdo do staging é validado contra o manifesto antes da promoção.
4. O diretório final é publicado em uma **única operação atômica** (`os.replace`). Se ocorrer qualquer erro ou interrupção no meio do processo, o staging é descartado e nenhum trabalho parcial aparece no destino.

---

## Fluxo completo de portabilidade

```bash
# Máquina de origem
cd /seu/checkout/marcasalao-marketing
python tools/studio_work_backup.py backup meu-trabalho .workspace/tmp/meu-trabalho.zip

# Verificar antes de transferir
python tools/studio_work_backup.py inspect .workspace/tmp/meu-trabalho.zip

# Máquina de destino (após git pull para ter o ProjectManifest e mídias compartilhadas)
cd /outro/checkout/marcasalao-marketing
python tools/studio_work_backup.py inspect .workspace/tmp/meu-trabalho.zip
python tools/studio_work_backup.py restore .workspace/tmp/meu-trabalho.zip
```

---

## Executar os testes

```bash
cd <RAIZ>
python -m unittest tools/tests/test_studio_work_backup.py -v
```

Todos os workspaces de teste ficam em `.workspace/tmp/studio-work-backup/tests/`
e são limpos automaticamente após cada teste.
