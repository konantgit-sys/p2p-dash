#!/bin/bash
# p2p-dash v1.0 — full mesh: 4 observers + bridge + dashboard
# Единая точка входа. Поднимается системным health-check при падении.
LOCKFILE=/tmp/p2p-dash.lock

exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "[start] another start.sh is running — exiting"
    exit 0
fi

echo "[start] $(date) — acquired lock"

# — Идемпотентность (12.09.2026) —
# start.sh вызывает и системный health-check, и скрипт рестарта. Если дашборд уже
# отвечает, второй запуск убивал живого и падал с "address already in use" —
# поймали гонку в логах. Теперь: живой дашборд не трогаем. Явная остановка —
# задача p2p_daily_restart.sh.
if curl -sf --max-time 5 http://localhost:8090/health >/dev/null 2>&1; then
    echo "[start] дашборд уже отвечает на /health — выходим, не трогаем"
    exit 0
fi

# — Ограничить арены malloc (11.09.2026) —
# За 53 ч через шину прошло 6.42 млн сообщений, куча раздулась до 1 ГБ анонимных
# арен (4 региона rw-p), при этом [heap] всего 20 МБ — ОС не возвращала страницы.
# MALLOC_ARENA_MAX=1 держит одну арену: после правки RSS 1050 -> 68 МБ.
export MALLOC_ARENA_MAX=1
export MALLOC_TRIM_THRESHOLD_=131072
# --- Эксперимент 12.09.2026: pymalloc -> glibc malloc ---
# База на pymalloc: 68 -> 131 МБ за 120 мин = 31.5 МБ/ч (heap 67 МБ).
# PYTHONMALLOC=malloc отключает пул мелких объектов Python: аллокации уходят в
# glibc, которая с MALLOC_ARENA_MAX=1 и trim-порогом должна возвращать память ОС.
# ОТКАТ: закомментировать строку ниже и перезапустить (bash p2p_daily_restart.sh).
export PYTHONMALLOC=malloc
export PYTHONUNBUFFERED=1

# — Остановить прежние процессы —
# ВАЖНО (11.09.2026): fuser/ss в этом контейнере НЕ видят сокеты пода (при живом
# дашборде "fuser 8090/tcp" отдаёт пусто), а pkill -f матчит любую командную строку
# с подстрокой "mesh_peer.py" и убивает посторонние процессы (включая вызывающий
# скрипт). Поэтому цели ищем строго: python <файл> + каталог процесса.
python3 - << 'PYEOF'
import os, signal
BASE = '/home/agent/data/sites/p2p-dash'
TARGETS = {'app.py', 'mesh_peer.py', 'nostr_mesh_bridge.py'}
PY = ('python3', 'python', 'python3.11')
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
    if len(args) < 2 or os.path.basename(args[0]) not in PY:
        continue
    if os.path.basename(args[1]) not in TARGETS:
        continue
    if not cwd.startswith(BASE):
        continue
    try:
        os.kill(int(p), signal.SIGKILL)
        killed.append(f'{os.path.basename(args[1])} (PID {p})')
    except OSError:
        pass
print('[start] killed: ' + (', '.join(killed) if killed else 'нечего убивать'))
PYEOF
sleep 2

# — Start bridge —
cd /home/agent/data/sites/p2p-dash/bridge
nohup python3 nostr_mesh_bridge.py > bridge.log 2>&1 9>&- &
echo "[start] bridge PID=$!"

# — Start 4 observers —
for i in 1 2 3 4; do
    PEER_NAME="observer-$i" nohup python3 mesh_peer.py > mesh_peer_${i}.log 2>&1 9>&- &
    echo "[start] observer-$i PID=$!"
done

sleep 3

# — Start dashboard —
cd /home/agent/data/sites/p2p-dash
# Освобождаем flock ПЕРЕД exec: иначе лок унаследует дашборд, следующий start.sh
# его уже не получит — и health-check не сможет поднять бэкенд после падения.
flock -u 9 2>/dev/null || true
exec 9>&-
exec python3 app.py
