# Devlog — Etapa 6 / Agente 6 (confiabilidade e infraestrutura local)

### Agente 6 — `workspace_doctor`: diagnóstico e higiene do `.workspace/` compartilhado

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa6-agente6`  
> **Worktree:** `.workspace/worktrees/etapa6-agente6`  
> **Base:** `main` @ `8a1b361`  
> **Escopo:** CLI/API 100% stdlib de higiene do workspace, auditoria de mídia local contra hashes versionados, limpeza segura de `tmp/` e suíte automatizada

## 1. Objetivo

Entregar, no território exclusivo do Agente 6 da Etapa 6, uma ferramenta de confiabilidade local que audite o `.workspace/` do checkout **principal** (compartilhado por todas as worktrees): presença/versão do FFmpeg portátil, integridade das mídias em `.workspace/archives/` contra os SHA-256 declarados nas entregas versionadas, higiene de worktrees/arquivos não rastreados e limpeza restrita de subdiretórios descartáveis de `.workspace/tmp/`. O relatório completo fica neste devlog para ser transferido ao `contexto_projeto.md` pelo `devlog_sync.py` — `contexto_projeto.md` **não** foi editado diretamente.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/workspace_doctor.py` | novo | API `run_workspace_doctor(root=".", clean_tmp=False)` e CLI `python tools/workspace_doctor.py [--check \| --clean-tmp] [--json] [--root DIR]`; 4 seções (ffmpeg, archives, worktrees, tmp), relatório `schemaVersion: 1`, exit codes 0/1/2; somente biblioteca padrão |
| `tools/tests/test_workspace_doctor.py` | novo | 11 testes em `TemporaryDirectory`, cobrindo auditoria íntegra, hash corrompido, preservação de protegidos no `--clean-tmp`, contenção de caminhos, CLI `--json`/`--clean-tmp`, FFmpeg ausente, higiene de worktrees e avisos de mídia ausente/não declarada |
| `.workspace/devlogs/etapa6-agente6.md` | novo | este relatório completo |

## 3. Desenho e decisões

- **Raiz principal por Git:** `_resolve_main_root()` usa `git rev-parse --git-common-dir` (o mesmo mecanismo de `bootstrap_ffmpeg.py`), de modo que, mesmo executado dentro de uma worktree, o doutro aponte para o `.workspace/` compartilhado. Sem Git, cai para o diretório informado.
- **Separação `source_root` × `resolution_root` (correção encontrada na validação real):** os manifestos `manifest.json`/`derivatives.json` são **versionados** e podem ser lidos de uma worktree, mas as mídias declaradas vivem em `.workspace/archives/` da **raiz principal**. Os caminhos `.workspace/archives/...` são resolvidos contra `MAIN_ROOT`, e as chaves de comparação são relativas a `MAIN_ROOT`. Sem essa separação, a primeira execução real acusava 70 erros falsos de `PATH_OUTSIDE_ARCHIVES`.
- **Cruzamento de hashes:** `manifest.json → artifacts.video.archivePath` e `derivatives.json → source.path` alimentam a categoria `9:16`; `derivatives.json → derivatives.{1x1,16x9,cover,thumb-16x9,preview-formats}` alimentam as demais. Caminhos declarados fora de `archives/` são recusados (`PATH_OUTSIDE_ARCHIVES`); hashes conflitantes para o mesmo arquivo geram `DECLARACAO_CONFLITANTE`.
- **Severidades:** divergência de SHA-256, FFmpeg ausente/inválido e worktree registrada sem diretório são `error`. Mídia declarada mas ausente (política do projeto: mídia local não é versionada), mídia não declarada, arquivos não rastreados e worktree órfã são `warning` — `ok` depende somente de `error`.
- **`--clean-tmp` restrito:** percorre apenas filhos diretos de `<MAIN_ROOT>/.workspace/tmp/`, remove somente diretórios, nunca arquivos soltos. `aprovacoes-titular.json` está em `PROTECTED_TMP_NAMES`; links/junções e alvos cujo `realpath` saia de `tmp/` são ignorados. `archives/`, `tools/` e `devlogs/` são irmãos de `tmp/`, estruturalmente inalcançáveis.
- **Isolamento dos testes:** `TemporaryDirectory(dir=<RAIZ>/.workspace/tmp/etapa6-agente6-doctor-tests/)` mantém todos os artefatos sob a raiz; `_resolve_main_root` e `_probe_version` são substituídos por `mock.patch.object` em `setUp` para que nenhum teste toque o `.workspace/` real ou execute binários.

## 4. Evidências de validação (nesta estação)

```
$ python -m unittest tools/tests/test_workspace_doctor.py -v
Ran 11 tests — OK   (PYTHON_EXIT_CODE=0)
  test_01_auditoria_integra_e_formatos ........................ ok
  test_02_detecta_hash_corrompido_em_archive .................. ok
  test_03_clean_tmp_preserva_protegidos ....................... ok
  test_04_clean_tmp_preserva_arquivos_soltos .................. ok
  test_05_declaracao_fora_de_archives_e_recusada .............. ok
  test_06_contenção_de_alvos_do_clean_tmp ..................... ok
  test_07_cli_json ............................................ ok
  test_08_cli_clean_tmp_json ................................... ok
  test_09_ffmpeg_ausente ....................................... ok
  test_10_worktrees_e_nao_rastreados ........................... ok
  test_11_midia_nao_declarada_e_midia_ausente_sao_avisos ....... ok

Execução real somente leitura (python tools/workspace_doctor.py --root . --json,
a partir da worktree, após a correção source_root/resolution_root):
  exit=1, ok=False, errors=1, warnings=1
  ffmpeg: ffmpeg.exe e ffprobe.exe presentes, versão 9.1-essentials_build-www.gyan.dev
  archives: 60 declarados, 60 presentes, 59 verificados, 1 divergente, 0 ausentes
  por formato: 9:16=10, 1x1=10, 16x9=10 (cover/thumb/preview também 10 cada)
  worktrees: 9 registradas, 0 órfãs, 4 arquivos não rastreados
  único error: ARCHIVE_HASH_DIVERGENTE em
    .workspace/archives/camp-shorts-completo-multitrack-001/camp-shorts-completo-multitrack-001.mp4
    (declarado em multitrack-hub/camp-shorts-completo-multitrack-001:derivatives.source)
```

O `ARCHIVE_HASH_DIVERGENTE` é um achado legítimo do auditor sobre mídia local não versionada desta estação (os derivados do Multitrack Hub foram regenerados em rodadas anteriores); **não** foi alterado — `.workspace/archives/` está fora do território do Agente 6. O `ARQUIVOS_NAO_RASTREADOS` são os próprios arquivos desta entrega antes do commit (`tools/workspace_doctor.py`, `tools/tests/test_workspace_doctor.py` e dois `__pycache__`, removidos antes de commitar).

## 5. Incidente registrado (transparência)

Na **primeira** execução da suíte, antes do `mock.patch.object(wd, "_resolve_main_root", ...)` em `setUp`, os testes de `--clean-tmp` rodaram com `workspace_root` apontando para a raiz principal real e removeram os **subdiretórios** então presentes em `<RAIZ>/.workspace/tmp/` (diretório hoje vazio). Eram artefatos locais ignorados pelo Git — pertencentes a rodadas anteriores (por exemplo simulações UTM, sandbox editorial-qa e staging de bootstrap) — e nenhum arquivo versionado foi afetado. Não há como restaurá-los; o isolamento foi corrigido imediatamente e a suíte foi reexecutada com 11/11 OK sem novo acesso ao `.workspace/` real. Sinalizo o fato para que outras estações/agentes saibam que evidências locais ali depositadas podem ter sido perdidas nesta sessão.

## 6. Limitações

- Não foi necessário baixar ferramentas portáteis: o FFmpeg já existe em `<RAIZ>/.workspace/tools/ffmpeg/` e foi apenas inspecionado.
- A auditoria compara hash dos arquivos **presentes**; encoded characteristics (fps/codec/dimensões) e `-an` continuam sendo verificados pelo `release_audit.py`. Mídia ausente permanece como aviso, conforme a política do projeto.
- Suíte roda em Windows (py 3.15 nesta estação) com nomes `ffmpeg.exe`/`ffprobe.exe`; em outras plataformas a ferramenta procura os nomes sem extensão.
- `contexto_projeto.md` não foi tocado; a consolidação deve ser feita por `python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md --pattern "etapa6-agente*.md"`.

## 7. Arquivos não tocados

`contexto_projeto.md`, `tenants/`, `02-reels-shorts/deliveries/`, `.workspace/archives/`, `.workspace/tools/`, a worktree principal e as worktrees dos outros agentes não foram alterados por esta entrega (com a exceção transitória registrada na Seção 5, já contida). Nenhum post, campanha, calendário ou portal foi publicado ou editado.

## 8. Handoff

- Branch pronta para merge: `codex/etapa6-agente6` (commit com os 3 arquivos do território).
- Verificação rápida: `python -m unittest tools/tests/test_workspace_doctor.py -v`.
- Diagnóstico local: `python tools/workspace_doctor.py --check --json` (somente leitura).
- Limpeza segura: `python tools/workspace_doctor.py --clean-tmp --json`.
- A divergência de hash do Multitrack Hub detectada na estação deve ser tratada pelo responsável de mídia, não por este agente.
