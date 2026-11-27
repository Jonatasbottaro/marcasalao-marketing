# Confinamento de caches e temporarios dentro de <RAIZ>/.workspace/tmp/hf001 (AGENTS.md).
# <RAIZ> e o checkout PRINCIPAL, resolvido via git-common-dir para funcionar tambem
# dentro de worktrees. Nao fixa caminho de maquina.
#
# ATENCAO: sobrescreve HOME/USERPROFILE do processo. Sourcing este arquivo em uma
# shell interativa pode quebrar o git de commits (identidade em ~/.gitconfig).
# Use sempre pelo wrapper scripts/hf.sh, que isola o processo.

HF001_GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)"
if [ -z "$HF001_GIT_COMMON" ]; then
  echo "ERRO: nao foi possivel resolver o diretorio git comum" >&2
  return 1 2>/dev/null || exit 1
fi
case "$HF001_GIT_COMMON" in
  /*)              HF001_ROOT="$(cd "$HF001_GIT_COMMON/.." && pwd)" ;;
  [A-Za-z]:[/\\]*) HF001_ROOT="$(cd "$HF001_GIT_COMMON/.." && pwd)" ;;
  *)               HF001_ROOT="$(cd "$(pwd)/$HF001_GIT_COMMON/.." && pwd)" ;;
esac
if [ -z "$HF001_ROOT" ] || [ ! -f "$HF001_ROOT/AGENTS.md" ]; then
  echo "ERRO: raiz resolvida invalida: '$HF001_ROOT'" >&2
  return 1 2>/dev/null || exit 1
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

# FFmpeg portavel do projeto (por estacao), quando presente no checkout principal.
# Em CI (Ubuntu) o FFmpeg do sistema entra pelo PATH normal.
HF001_FFMPEG_DIR="$HF001_ROOT/.workspace/tools/ffmpeg"
if [ -d "$HF001_FFMPEG_DIR" ]; then
  export PATH="$HF001_FFMPEG_DIR:$PATH"
fi

# Skills HyperFrames ficam versionadas no repositorio (.agents/skills/);
# init nao deve consulta-las no GitHub nem instalar por conta propria.
export HYPERFRAMES_SKIP_SKILLS=1
