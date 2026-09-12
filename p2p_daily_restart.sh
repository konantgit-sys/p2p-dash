#!/bin/bash
# Плановый перезапуск p2p-dash (ежедневно 04:00).
# Зачем: дашборд после миллионов сообщений накапливает анонимные арены malloc
# и держал ~1 ГБ, который ОС не возвращает. Перезапуск возвращает память
# (11.09.2026: 1050 МБ -> 68 МБ, анонимные арены 1011 МБ -> 24 МБ).
# Состояние не теряется: метрики в metrics_history.json, меш-база в SQLite
# /tmp/p2p_dash_mesh.db. Наблюдателей и мост поднимает сам start.sh.

LOG=/home/agent/data/sites/p2p-dash/restart.log
BASE=/home/agent/data/sites/p2p-dash
cd "$BASE" || exit 1

# Процессы ищем по cwd: fuser/ss в этом контейнере сокеты пода не видят,
# а pgrep по пути не матчит командную строку "python3 app.py".
find_dash() {
    python3 - << 'PYEOF'
import os
for p in os.listdir('/proc'):
    if not p.isdigit():
        continue
    try:
        if os.readlink(f'/proc/{p}/cwd') != '/home/agent/data/sites/p2p-dash':
            continue
        args = [a for a in open(f'/proc/{p}/cmdline').read().split('\0') if a]
        if len(args) < 2 or os.path.basename(args[1]) != 'app.py':
            continue
        rss = [l for l in open(f'/proc/{p}/status') if l.startswith('VmRSS')]
        print(f"{p} {int(rss[0].split()[1])//1024 if rss else 0}")
        break
    except OSError:
        continue
PYEOF
}

read -r OLD_PID OLD_RSS <<< "$(find_dash)"
echo "$(date -Is) — плановый перезапуск старт, PID был: ${OLD_PID:-нет}, RSS до: ${OLD_RSS:-?} МБ" >> "$LOG"

# Явная остановка: start.sh теперь идемпотентен и живой дашборд не убивает,
# поэтому плановый рестарт сам снимает процессы (иначе он бы ничего не сделал).
python3 - << 'PYEOF'
import os, signal
BASE = '/home/agent/data/sites/p2p-dash'
TARGETS = {'app.py', 'mesh_peer.py', 'nostr_mesh_bridge.py'}
me = {os.getpid(), os.getppid()}
killed = []
for p in os.listdir('/proc'):
    if not p.isdigit() or int(p) in me:
        continue
    try:
        args = [a for a in open(f'/proc/{p}/cmdline').read().split('\x00') if a]
        cwd = os.readlink(f'/proc/{p}/cwd')
    except OSError:
        continue
    if len(args) < 2 or not os.path.basename(args[0]).startswith('python'):
        continue
    if os.path.basename(args[1]) not in TARGETS or not cwd.startswith(BASE):
        continue
    try:
        os.kill(int(p), signal.SIGKILL)
        killed.append(os.path.basename(args[1]))
    except OSError:
        pass
print(f"[restart] остановлено: {len(killed)} процессов {sorted(set(killed))}")
PYEOF
sleep 3

setsid nohup bash start.sh >> "$LOG" 2>&1 < /dev/null &
sleep 12

read -r NEW_PID NEW_RSS <<< "$(find_dash)"
CODE=$(curl -s --max-time 8 -o /dev/null -w '%{http_code}' http://localhost:8090/health || echo "000")
echo "$(date -Is) — перезапуск готово, PID: ${NEW_PID:-НЕ ПОДНЯЛСЯ}, RSS после: ${NEW_RSS:-?} МБ, /health: $CODE" >> "$LOG"

if [ -z "$NEW_PID" ] || [ "$CODE" != "200" ]; then
    exit 1
fi
exit 0
