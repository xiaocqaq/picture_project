#!/bin/bash
# 管理 AI Picture 服务：aipic {start|stop|restart|status|logs}

set -e

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
PID_FILE="$PROJECT_DIR/app.pid"
LOG_FILE="$PROJECT_DIR/app.log"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
UVICORN="$VENV_DIR/bin/uvicorn"
APP_MODULE="app.main:app"
IMAGES_DIR="$PROJECT_DIR/data/images"
THUMBS_DIR="$PROJECT_DIR/data/thumbs"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}OK $1${NC}"; }
warn() { echo -e "${YELLOW}WARN $1${NC}"; }
error() { echo -e "${RED}ERR $1${NC}"; exit 1; }

require_command() {
    command -v "$1" >/dev/null 2>&1 || error "缺少命令: $1"
}

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            warn "已从模板创建 .env，请填入 API Key 后再启动"
            exit 0
        fi
        error ".env 不存在"
    fi
}

load_env() {
    ORIGINAL_PORT="$PORT"
    ORIGINAL_WORKERS="$WORKERS"
    TMP_ENV="$(mktemp)"
    tr -d '\r' < "$ENV_FILE" > "$TMP_ENV"
    set -a
    . "$TMP_ENV"
    set +a
    rm -f "$TMP_ENV"
    PORT="$ORIGINAL_PORT"
    WORKERS="$ORIGINAL_WORKERS"
    export PORT WORKERS
}

check_venv() {
    require_command "python3"
    if [ ! -d "$VENV_DIR" ] || [ ! -x "$PYTHON" ] || [ ! -x "$PIP" ]; then
        info "虚拟环境不存在或不完整，正在重建"
        python3 -m venv --clear "$VENV_DIR" || error "创建虚拟环境失败，请先安装 python3-venv"
    fi
    if [ ! -x "$PIP" ]; then
        "$PYTHON" -m ensurepip --upgrade || error "初始化 pip 失败"
    fi
    if [ ! -x "$UVICORN" ]; then
        info "安装依赖"
        "$PIP" install -r "$REQUIREMENTS"
    fi
}

prepare_dirs() {
    mkdir -p "$IMAGES_DIR" "$THUMBS_DIR"
}

is_managed_process() {
    PID="$1"
    CMD=$(ps -p "$PID" -o args= 2>/dev/null || true)
    [[ "$CMD" == *"$APP_MODULE"* ]]
}

get_main_pid() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if is_managed_process "$PID"; then
            echo "$PID"
            return 0
        fi
    fi
    lsof -t -i:"$PORT" 2>/dev/null | head -1
}

is_running() {
    require_command "lsof"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if is_managed_process "$PID"; then
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1
}

print_runtime_info() {
    REV="$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    info "代码版本: $REV"
    (cd "$PROJECT_DIR" && "$PYTHON" - <<'PY'
import openai
from app.service import describe_client
print("OpenAI SDK:", openai.__version__)
print("Image client:", describe_client())
PY
    )
}

cmd_start() {
    check_env
    load_env
    check_venv
    prepare_dirs

    if is_running; then
        warn "服务已在运行中 (PID: $(get_main_pid))"
        exit 0
    fi

    info "安装/更新依赖"
    "$PIP" install -r "$REQUIREMENTS"
    print_runtime_info

    info "启动服务 (端口 $PORT, workers $WORKERS)"
    cd "$PROJECT_DIR"
    nohup "$UVICORN" "$APP_MODULE" --host 0.0.0.0 --port "$PORT" --workers "$WORKERS" > "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"

    sleep 1
    if is_running; then
        info "服务启动成功，PID: $NEW_PID"
        echo "日志文件: $LOG_FILE"
        echo "访问地址: http://$(hostname -I | awk '{print $1}'):$PORT"
    else
        error "服务启动失败，请查看日志: $LOG_FILE"
    fi
}

cmd_stop() {
    if ! is_running; then
        warn "没有运行中的服务"
        return 0
    fi

    if [ -f "$PID_FILE" ]; then
        MAIN_PID=$(cat "$PID_FILE")
        if ps -p "$MAIN_PID" >/dev/null 2>&1; then
            kill "$MAIN_PID"
            rm -f "$PID_FILE"
            sleep 1
            pkill -P "$MAIN_PID" 2>/dev/null || true
            info "已停止主进程 PID: $MAIN_PID"
            return 0
        fi
    fi

    PIDS=$(lsof -t -i:"$PORT" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | while read -r pid; do
            [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
        done
        rm -f "$PID_FILE"
        info "已停止占用端口 $PORT 的进程"
    fi
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    if is_running; then
        PID=$(get_main_pid)
        info "服务正在运行，PID: $PID"
        echo "端口: $PORT"
        echo "日志: $LOG_FILE"
        print_runtime_info
    else
        warn "服务未运行"
    fi
}

cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        warn "日志文件不存在"
    fi
}

usage() {
    cat <<EOF
用法: $0 {start|stop|restart|status|logs}

命令:
  start      启动服务
  stop       停止服务
  restart    重启服务
  status     查看状态
  logs       实时查看日志

环境变量:
  PORT       指定端口，默认 8000
  WORKERS    指定 worker 数，默认 1
EOF
}

case "${1:-}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    -h|--help|help|*) usage ;;
esac
