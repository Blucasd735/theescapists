#!/bin/bash

# --------------------------------------------------
# THE ESCAPISTS - PORTMASTER TEST
# WestonPack + GL4ES + Box64
# --------------------------------------------------

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

# Pasta do PortMaster no ArkOS
controlfolder="/opt/system/Tools/PortMaster"

# Pasta onde este launcher está
PORTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Pastas do port
GAMEDIR="$PORTS_DIR/theescapists"
GAMEDATA="$GAMEDIR/gamedata"
GAME_DIR="$GAMEDATA/game"
CONFDIR="$GAMEDIR/conf"
LIBDIR="$GAMEDIR/libs"

# Executáveis
BOX64="$GAMEDIR/box64/box64"
GAME="$GAME_DIR/bin64/Chowdren"

# Arquivos auxiliares
GPTK_FILE="$GAMEDIR/controls.gptk"
LOG="$GAMEDIR/log.txt"

# Criar pastas necessárias
mkdir -p "$CONFDIR"
mkdir -p "$LIBDIR"

# Gravar toda a execução no log
exec > "$LOG" 2>&1

echo "=========================================="
echo "The Escapists - PortMaster test"
echo "=========================================="
echo "Data: $(date)"
echo "Arquitetura: $(uname -m)"
echo "GAMEDIR: $GAMEDIR"
echo "GAME_DIR: $GAME_DIR"
echo "BOX64: $BOX64"
echo "GAME: $GAME"
echo "=========================================="

# --------------------------------------------------
# CARREGAR FUNÇÕES DO PORTMASTER
# --------------------------------------------------

if [ ! -d "$controlfolder" ]; then
    echo "ERRO: PortMaster não encontrado:"
    echo "$controlfolder"
    exit 1
fi

source "$controlfolder/control.txt"
source "$controlfolder/funcs.txt"

get_controls

# --------------------------------------------------
# CONFERIR OS ARQUIVOS
# --------------------------------------------------

if [ ! -f "$BOX64" ]; then
    echo "ERRO: Box64 não encontrado:"
    echo "$BOX64"
    pm_message "Box64 não encontrado."
    sleep 5
    pm_finish
    exit 1
fi

if [ ! -f "$GAME" ]; then
    echo "ERRO: Chowdren não encontrado:"
    echo "$GAME"
    pm_message "Executável Chowdren não encontrado."
    sleep 5
    pm_finish
    exit 1
fi

chmod +x "$BOX64"
chmod +x "$GAME"

# Os scripts originais do GOG também podem precisar de permissão
[ -f "$GAMEDATA/start.sh" ] && chmod +x "$GAMEDATA/start.sh"
[ -f "$GAME_DIR/run.sh" ] && chmod +x "$GAME_DIR/run.sh"

# --------------------------------------------------
# PREPARAR O WESTONPACK
# --------------------------------------------------

weston_runtime="weston_pkg_0.2"
weston_file="$controlfolder/libs/${weston_runtime}.squashfs"
weston_dir="/tmp/weston"

$ESUDO mkdir -p "$weston_dir"

# Solicitar o runtime ao PortMaster se estiver faltando
if [ ! -f "$weston_file" ]; then
    echo "WestonPack não encontrado. Solicitando ao PortMaster..."

    if [ ! -f "$controlfolder/harbourmaster" ]; then
        echo "ERRO: harbourmaster não encontrado."
        pm_message "WestonPack 0.2 não encontrado."
        sleep 5
        pm_finish
        exit 1
    fi

    $ESUDO "$controlfolder/harbourmaster" \
        --quiet \
        --no-check \
        runtime_check \
        "${weston_runtime}.squashfs"
fi

if [ ! -f "$weston_file" ]; then
    echo "ERRO: Não foi possível obter o WestonPack."
    pm_message "Falha ao carregar o WestonPack."
    sleep 5
    pm_finish
    exit 1
fi

# Desmontar uma montagem anterior
if [ "$PM_CAN_MOUNT" != "N" ]; then
    $ESUDO umount "$weston_dir" 2>/dev/null
fi

# Montar o runtime
echo "Montando WestonPack em $weston_dir..."

$ESUDO mount "$weston_file" "$weston_dir"

if [ ! -f "$weston_dir/westonwrap.sh" ]; then
    echo "ERRO: westonwrap.sh não encontrado após a montagem."
    pm_message "Falha ao montar o WestonPack."
    sleep 5
    pm_finish
    exit 1
fi

# --------------------------------------------------
# CONFIGURAÇÃO GRÁFICA DO PORTMASTER
# --------------------------------------------------

if [ -f "$controlfolder/libgl_${CFW_NAME}.txt" ]; then
    echo "Carregando libgl_${CFW_NAME}.txt"
    source "$controlfolder/libgl_${CFW_NAME}.txt"
elif [ -f "$controlfolder/libgl_default.txt" ]; then
    echo "Carregando libgl_default.txt"
    source "$controlfolder/libgl_default.txt"
fi

# Configuração usual do GL4ES para Mali-450
export LIBGL_ES=2
export LIBGL_GL=21
export LIBGL_FB=4

# Saves e configurações
export XDG_DATA_HOME="$CONFDIR"
export XDG_CONFIG_HOME="$CONFDIR"
export HOME="$CONFDIR"

# Controle SDL detectado pelo PortMaster
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

# Diagnóstico do Box64
export BOX64_LOG=1
export BOX64_DYNAREC=1
export BOX64_EMULATED_LIBS="libSDL2-2.0.so.0"

# Bibliotecas x86_64 fornecidas pelo próprio jogo
export BOX64_LD_LIBRARY_PATH="$GAME_DIR/bin64:$GAME_DIR/lib64:$GAME_DIR/lib"

# --------------------------------------------------
# ENTRAR NA PASTA CORRETA
# --------------------------------------------------

cd "$GAME_DIR" || {
    echo "ERRO: Não foi possível entrar em $GAME_DIR"
    pm_finish
    exit 1
}

echo "Diretório atual: $(pwd)"
echo "Conteúdo de bin64:"
ls -la "$GAME_DIR/bin64"

# --------------------------------------------------
# INICIAR CONTROLES
# --------------------------------------------------

echo "Iniciando GPTOKEYB para o processo Chowdren..."

if [ -f "$GPTK_FILE" ]; then
    $GPTOKEYB "Chowdren" -c "$GPTK_FILE" &
else
    $GPTOKEYB "Chowdren" &
fi
# --------------------------------------------------
# EXECUTAR WESTON + GL4ES + BOX64 + CHOWDREN
# --------------------------------------------------

echo "Iniciando The Escapists..."
echo "Comando: WestonPack -> GL4ES -> Box64 -> Chowdren"

$ESUDO env \
    WRAPPED_LIBRARY_PATH="$LIBDIR" \
    LIBGL_ES=2 \
    LIBGL_GL=21 \
    LIBGL_FB=4 \
    WESTON_HEADLESS_WIDTH=640 \
    WESTON_HEADLESS_HEIGHT=480 \
    "$weston_dir/westonwrap.sh" \
    headless \
    noop \
    kiosk \
    crusty_glx_gl4es \
    BOX64_LD_PRELOAD="$GAMEDIR/fixes/libresolution_fix.so" \
    XDG_DATA_HOME="$CONFDIR" \
    XDG_CONFIG_HOME="$CONFDIR" \
    HOME="$CONFDIR" \
    FILTER_ARROW_KEYS=1 \
    KEY_TRACE=1 \
    BOX64_LOG=1 \
    BOX64_DYNAREC=1 \
    BOX64_EMULATED_LIBS="libSDL2-2.0.so.0" \
    BOX64_LD_LIBRARY_PATH="$GAME_DIR/bin64:$GAME_DIR/lib64:$GAME_DIR/lib" \
    "$BOX64" \
    "$GAME"

GAME_EXIT_CODE=$?

echo "=========================================="
echo "Chowdren/Box64 retornou: $GAME_EXIT_CODE"
echo "=========================================="

# --------------------------------------------------
# LIMPEZA
# --------------------------------------------------

echo "Encerrando WestonPack..."

$ESUDO "$weston_dir/westonwrap.sh" cleanup 2>/dev/null

if [ "$PM_CAN_MOUNT" != "N" ]; then
    $ESUDO umount "$weston_dir" 2>/dev/null
fi

pm_finish

echo "Launcher finalizado."
exit "$GAME_EXIT_CODE"