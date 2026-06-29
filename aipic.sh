#!/bin/bash
# ============================================================
#  aipic - 管理 AI Picture 服务的统一命令行工具
#  用法: aipic {start|stop|restart|status|logs}
# ============================================================

set -e

# ---------- 解析脚本真实路径（支持软链接） ----------
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
# -----------------------------------------------

VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
PORT=8000
WORKERS=4
PID_FILE="$PROJECT_DIR/app.pid"
LOG_FILE="$PROJECT_DIR/app.log"
UVICORN="$VENV_DIR/bin/uvicorn"
APP_MODULE="app.main:app"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ---------- 辅助函数 ----------
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        error "虚拟环境不存在，请先运行: python3 -m venv $VENV_DIR"
    fi
    if [ ! -f "$UVICORN" ]; then
        error "uvicorn 未安装，请在虚拟环境中执行: $VENV_DIR/bin/pip install uvicorn[standard]"
    fi
}

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            warn "已从模板创建 .env 文件，请编辑填入 API Key 后再启动"
            exit 0
        else
            error ".env.example 不存在，请手动创建 .env 文件"
        fi
    fi
}

# 获取主进程 PID（优先从 PID 文件读取）
get_main_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        lsof -t -i:$PORT 2>/dev/null | head -1
    fi
}

# 检查服务是否运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# ---------- 子命令 ----------
cmd_start() {
    check_venv
    check_env

    if is_running; then
        warn "服务已在运行中 (PID: $(get_main_pid))"
        exit 0
    fi

    info "安装/更新依赖..."
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"

    info "启动服务 (端口 $PORT, workers $WORKERS)..."
    cd "$PROJECT_DIR"
    nohup "$UVICORN" "$APP_MODULE" --host 0.0.0.0 --port "$PORT" --workers "$WORKERS" > "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"

    sleep 1
    if is_running; then
        info "服务启动成功，PID: $NEW_PID"
        echo "📋 日志文件: $LOG_FILE"
        echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}'):$PORT"
    else
        error "服务启动失败，请查看日志: $LOG_FILE"
    fi
}

cmd_stop() {
    if is_running; then
        if [ -f "$PID_FILE" ]; then
            MAIN_PID=$(cat "$PID_FILE")
            if ps -p "$MAIN_PID" > /dev/null 2>&1; then
                kill "$MAIN_PID"
                info "已停止主进程 PID: $MAIN_PID"
                rm -f "$PID_FILE"
                sleep 1
                pkill -P "$MAIN_PID" 2>/dev/null || true
                exit 0
            fi
        fi

        PIDS=$(lsof -t -i:$PORT 2>/dev/null)
        if [ -n "$PIDS" ]; then
            echo "$PIDS" | while read -r pid; do
                [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
            done
            info "已停止所有占用端口 $PORT 的进程"
            rm -f "$PID_FILE"
        else
            warn "没有运行中的服务"
        fi
    else
        warn "没有运行中的服务"
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

# ---------- 主入口 ----------
usage() {
    cat <<EOF
用法: $0 {start|stop|restart|status|logs}

命令:
  start      启动服务（后台运行）
  stop       停止服务
  restart    重启服务
  status     查看服务运行状态
  logs       实时查看日志

环境变量:
  PORT       指定端口（默认 8000）
  WORKERS    指定 worker 数量（默认 4）

示例:
  $0 start
  PORT=8080 $0 start
EOF
}

case "$1" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    -h|--help|help|*) usage ;;
esac