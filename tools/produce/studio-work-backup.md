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
| `review-state.json` | Estado de revisão por perfil |
| `planning.json` | Planejamento do trabalho |
| `media-library.json` | Referências da biblioteca de mídia |
| `drafts/video.request.json` | Rascunho de vídeo |
| `drafts/carousel.request.json` | Rascunho de carrossel |
| `drafts/motion.plan.json` | Plano de motion |
| `media/**` | Todos os arquivos de mídia do trabalho |
| `MANIFEST.json` | Manifesto interno (hashes, dependências) |

**O que é excluído (v1):**

- Credenciais e configurações de máquina
- `production-queue.sqlite` (fila de produção)
- Aprovações e estado de review enviado
- Entregas renderizadas (`deliveries/`)
- Caches

---

### `inspect` — Verificar a integridade de um backup

```bash
python tools/studio_work_backup.py inspect <arquivo.zip>
```

**Exemplo:**

```bash
python tools/studio_work_backup.py inspect .workspace/tmp/meu-anuncio-novembro.zip
```

**Saída típica:**

```
=== Inspecao do backup ===
Trabalho : meu-anuncio-novembro
Exportado: 2026-11-15T10:30:00+00:00
Schema   : v1
Arquivos : 10

  OK             : .workspace/studio/works/meu-anuncio-novembro/work.json
  OK             : .workspace/studio/works/meu-anuncio-novembro/editorial.json
  ...

--- Dependências ---
  OK            : platform/examples/projects/marca-salao-social.project.json

Resultado: OK — backup integro e dependências satisfeitas.
```

> [!IMPORTANT]
> `inspect` verifica tanto a integridade interna do ZIP (SHA-256 de cada arquivo)
> quanto a presença e hash do `ProjectManifest` no **checkout atual**.
> Se o `ProjectManifest` estiver ausente ou modificado, a inspeção reporta o problema
> antes de tentar uma restauração.

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
> que ainda precisa estar dentro da raiz do repositório atual (conforme `AGENTS.md`).
> Ambos os checkouts devem ter o mesmo `ProjectManifest` referenciado pelo trabalho.

> [!CAUTION]
> A restauração só é permitida em destinos onde o trabalho **ainda não existe**.
> Não há `--overwrite` nesta versão. Para atualizar um trabalho, delete o diretório
> antes de restaurar.

---

## Fluxo completo de portabilidade

```bash
# Máquina de origem
cd /seu/checkout/marcasalao-marketing
python tools/studio_work_backup.py backup meu-trabalho .workspace/tmp/meu-trabalho.zip

# Verificar antes de transferir
python tools/studio_work_backup.py inspect .workspace/tmp/meu-trabalho.zip

# Copiar o ZIP para o outro computador (Git, pen drive, nuvem…)
# O ProjectManifest já versionado no Git estará disponível no outro checkout

# Máquina de destino (após git pull)
cd /outro/checkout/marcasalao-marketing
python tools/studio_work_backup.py inspect .workspace/tmp/meu-trabalho.zip
python tools/studio_work_backup.py restore .workspace/tmp/meu-trabalho.zip
```

---

## Dependências verificáveis

O `ProjectManifest` (`.project.json`) é um arquivo **versionado no Git** e referenciado
por `work.json`. O backup registra seu caminho relativo e SHA-256.

- `inspect` verifica se o manifest existe no destino com o hash correto.
- `restore` não reescreve o manifest — ele deve já estar presente no checkout de destino.
- Se o manifest estiver ausente, `inspect` reporta `AUSENTE` e `restore` continua
  (a restauração do trabalho em si funciona; o Studio abrirá o trabalho com o manifest
  local, que pode ter evoluído no Git).

---

## Erros comuns

| Mensagem | Causa | Solução |
|---|---|---|
| `id do trabalho deve usar kebab-case` | Work ID com maiúsculas ou `_` | Use `meu-trabalho`, não `Meu_Trabalho` |
| `trabalho nao encontrado` | Work não existe neste checkout | Confirme o ID com a lista de trabalhos |
| `O trabalho já existe` | Destino já tem o trabalho | Delete o diretório do trabalho no destino |
| `HASH_DIVERGENTE` | Arquivo corrompido ou modificado | Regenere o backup na origem |
| `AUSENTE NO ZIP` | ZIP incompleto | Regenere o backup |
| `ProjectManifest nao encontrado` | Destino não tem o manifest | Faça `git pull` no destino |

---

## Executar os testes

```bash
cd <RAIZ>
python -m unittest tools/tests/test_studio_work_backup.py -v
```

Todos os workspaces de teste ficam em `.workspace/tmp/studio-work-backup/tests/`
e são limpos após cada teste.
