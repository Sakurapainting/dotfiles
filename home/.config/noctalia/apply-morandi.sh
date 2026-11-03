#!/bin/bash
# 由 noctalia 的 wallpaper_changed hook 调用：壁纸变了就重新取色 + 重新分发配色
# 手动跑一次等价于「立即把当前壁纸的颜色同步到全系统」

set -uo pipefail

LOG="$HOME/.local/state/noctalia/morandi.log"
COLORS="$HOME/.config/noctalia/colors.json"
GEN="$HOME/.config/noctalia/morandi-gen.py"

# hook 触发时环境变量可能极简，显式兜底
NOCTALIA="$(command -v noctalia || echo /usr/bin/noctalia)"
PYTHON="$(command -v python3 || echo /usr/bin/python3)"

mkdir -p "$(dirname "$LOG")"
# 日志超过 256K 就只保留最后 64K，避免长期堆积
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 262144 ]; then
    tail -c 65536 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

{
    echo "── $(date '+%F %T') 触发"
    WALLPAPER="$("$NOCTALIA" msg wallpaper-get 2>/dev/null)"

    if [ -n "$WALLPAPER" ] && [ -f "$WALLPAPER" ]; then
        if ! "$NOCTALIA" theme "$WALLPAPER" --scheme muted -o "$COLORS"; then
            echo "!! noctalia theme 取色失败，沿用旧 colors.json"
        fi
    else
        echo "!! 拿不到壁纸路径，沿用旧 colors.json"
    fi

    if [ ! -f "$COLORS" ]; then
        echo "!! 没有 colors.json，放弃"
        exit 0
    fi

    "$PYTHON" "$GEN"
} >> "$LOG" 2>&1
