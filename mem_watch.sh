#!/bin/bash
# Наблюдатель за памятью p2p-dash для эксперимента pymalloc → malloc (12.09.2026).
# Пишет строку JSON каждые 5 минут: режим аллокатора, uptime, RSS, heap, арены, msg/s.
# Запуск: nohup bash mem_watch.sh >> mem_watch.log 2>&1 &
# Остановка: touch MEM_WATCH_OFF
cd /home/agent/data/sites/p2p-dash || exit 1

while true; do
    if [ -f MEM_WATCH_OFF ]; then sleep 60; continue; fi
    python3 - << 'PY'
import json, os, re, time, urllib.request

base = "/home/agent/data/sites/p2p-dash"
pid = None
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        if os.readlink(f"/proc/{p}/cwd") == base and "app.py" in open(f"/proc/{p}/cmdline").read():
            pid = p
            break
    except OSError:
        pass
if not pid:
    time.sleep(60)
    raise SystemExit

rss = int([l for l in open(f"/proc/{pid}/status") if l.startswith("VmRSS")][0].split()[1]) // 1024
pat = re.compile(r"([0-9a-f]+)-([0-9a-f]+) \S+ \S+ \S+ \S+ *(\S*)")
cur = None
regs = {}
for line in open(f"/proc/{pid}/smaps"):
    m = pat.match(line)
    if m:
        cur = m.group(3).strip()
        regs.setdefault(cur, 0)
    elif line.startswith("Rss:") and cur is not None:
        regs[cur] += int(line.split()[1])

mode = "pymalloc"
try:
    env = dict(kv.split("=", 1) for kv in open(f"/proc/{pid}/environ").read().split("\0") if "=" in kv)
    mode = env.get("PYTHONMALLOC", "pymalloc") + ("+arena1" if env.get("MALLOC_ARENA_MAX") == "1" else "")
except OSError:
    pass

metrics = {}
try:
    with urllib.request.urlopen("http://localhost:8090/api/metrics", timeout=8) as r:
        metrics = json.load(r).get("data", {})
except Exception:
    pass

# Внутренняя атрибуция памяти (эксперимент №2, 12.09): арены Python и крупные
# анонимные блоки. Нужна кривая, а не одна точка: растут ли арены pymalloc
# (тогда копятся Python-объекты) или крупные анонимные блоки C-слоя.
alloc = {}
try:
    with urllib.request.urlopen("http://localhost:8090/api/debug/alloc", timeout=25) as r:
        alloc = json.load(r).get("data", {})
except Exception:
    pass

a = alloc.get("allocator") or {}
big = (alloc.get("top_regions") or [{}])[0]

row = {
    "ts": int(time.time()),
    "mode": mode,
    "uptime_min": round((metrics.get("uptime") or 0) / 60, 1),
    "rss_mb": rss,
    "heap_mb": regs.get("[heap]", 0) // 1024,
    "anon_mb": regs.get("", 0) // 1024,
    "msg_rate": metrics.get("msg_rate"),
    "msgs_total": metrics.get("message_count"),
    "arenas": a.get("arenas_current"),
    "arena_mb": round((a.get("arena_bytes") or 0) / 1048576, 1),
    "py_blocks_in_use": a.get("blocks_in_use_total"),
    "py_pools": a.get("pools_total"),
    "unused_pools": a.get("unused_pools"),
    "anon_big_mb": alloc.get("anon_rss_mb"),
    "biggest_mb": big.get("rss_mb"),
    "biggest_what": (big.get("what") or "")[:40],
    "threads": alloc.get("threads"),
}
with open(f"{base}/mem_watch.jsonl", "a") as f:
    f.write(json.dumps(row) + "\n")
PY
    sleep 300
done
