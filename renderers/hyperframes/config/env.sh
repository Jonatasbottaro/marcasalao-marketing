# Confinamento de caches e temporarios dentro de <RAIZ>/.workspace/tmp/hf001 (AGENTS.md).
# <RAIZ> e o checkout ATIVO (worktree ou principal), resolvido por git rev-parse
# --show-toplevel. Nao fixa caminho de maquina.
#
# ATENCAO: sobrescreve HOME/USERPROFILE do processo. Sourcing este arquivo em uma
# shell interativa pode quebrar o git de commits (identidade em ~/.gitconfig).
# Use sempre pelo wrapper scripts/hf.sh, que isola o processo.

HF001_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$HF001_ROOT" ]; then
  echo "ERRO: nao foi possivel resolver a raiz do checkout ativo (git rev-parse --show-toplevel)" >&2
  return 1 2>/dev/null || exit 1
fi
if [ ! -f "$HF001_ROOT/AGENTS.md" ]; then
  echo "ERRO: raiz resolvida invalida (sem AGENTS.md): '$HF001_ROOT'" >&2
  return 1 2>/dev/null || exit 1
fi

# Runtime HyperFrames instalado no checkout ativo (renderers/hyperframes/node_modules).
# Em worktrees sem o runtime, emite erro claro em vez de fallthrough silencioso.
if [ ! -d "$HF001_ROOT/renderers/hyperframes/node_modules/hyperframes" ]; then
  echo "ERRO: runtime HyperFrames nao instalado em '$HF001_ROOT/renderers/hyperframes/node_modules/'." >&2
  echo "      Execute 'npm ci' em renderers/hyperframes/ ou use o checkout que contem o runtime." >&2
  return 1 2>/dev/null || exit 1
fi

# FFmpeg portavel: procura no checkout ativo e, em fallback, no checkout principal
# (para worktrees que compartilham o .workspace/tools/ffmpeg do principal).
HF001_FFMPEG_DIR="$HF001_ROOT/.workspace/tools/ffmpeg"
if [ ! -d "$HF001_FFMPEG_DIR" ]; then
  HF001_GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)"
  if [ -n "$HF001_GIT_COMMON" ]; then
    case "$HF001_GIT_COMMON" in
      /*)              _MAIN_ROOT="$(cd "$HF001_GIT_COMMON/.." && pwd)" ;;
      [A-Za-z]:[/\\]*) _MAIN_ROOT="$(cd "$HF001_GIT_COMMON/.." && pwd)" ;;
      *)               _MAIN_ROOT="$(cd "$(pwd)/$HF001_GIT_COMMON/.." && pwd)" ;;
    esac
    if [ -d "$_MAIN_ROOT/.workspace/tools/ffmpeg" ]; then
      HF001_FFMPEG_DIR="$_MAIN_ROOT/.workspace/tools/ffmpeg"
    fi
  fi
fi

HF001_TMP="$HF001_ROOT/.workspace/tmp/hf001"
mkdir -p "$HF001_TMP/npm-cache" "$HF001_TMP/temp" "$HF001_TMP/puppeteer" "$HF001_TMP/xdg-cache" "$HF001_TMP/home"

export npm_config_cache="$HF001_TMP/npm-cache"
export TEMP="$HF001_TMP/temp"
export TMP="$HF001_TMP/temp"
export TMPDIR="$HF001_TMP/temp"
export PUPPETEER_CACHE_DIR="$HF001_TMP/puppeteer"
export XDG_CACHE_HOME="$HF001_TMP/xdg-cache"
# Redireciona os.homedir() do processo (caches tipo ~/.hyperframes) para dentro da raiz.
export USERPROFILE="$HF001_TMP/home"
export HOME="$HF001_TMP/home"

# FFmpeg portavel: adiciona ao PATH quando presente (resolucao acima).
# Em CI (Ubuntu) o FFmpeg do sistema entra pelo PATH normal.
export HF001_FFMPEG_DIR
if [ -d "$HF001_FFMPEG_DIR" ]; then
  export PATH="$HF001_FFMPEG_DIR:$PATH"
fi

# Skills HyperFrames ficam versionadas no repositorio (.agents/skills/);
# init nao deve consulta-las no GitHub nem instalar por conta propria.
export HYPERFRAMES_SKIP_SKILLS=1
