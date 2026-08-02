#!/bin/bash
# p2p-dash v0.5.2 — single entry point
# Uses flock for true mutual exclusion across parallel invocations

LOCKFILE=/tmp/p2p-dash.lock

# — Atomic lock via flock —
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "[start] another start.sh is running (flock busy) — exiting"
    exit 0
fi

echo "[start] $(date) — acquired lock, starting"

# — Start mesh_peer (only if not already running) —
if ! pgrep -f "mesh_peer.py" > /dev/null 2>&1; then
    cd /home/agent/data/sites/p2p-dash/bridge
    nohup python3 mesh_peer.py > mesh_peer.log 2>&1 &
    echo "[start] mesh_peer PID=$!"
else
    echo "[start] mesh_peer already running"
fi

# — Start nostr_mesh_bridge (only if not already running) —
if ! pgrep -f "nostr_mesh_bridge.py" > /dev/null 2>&1; then
    cd /home/agent/data/sites/p2p-dash/bridge
    nohup python3 nostr_mesh_bridge.py > bridge.log 2>&1 &
    echo "[start] bridge PID=$!"
else
    echo "[start] bridge already running"
fi

sleep 2

# — Start app.py (foreground, lock stays via fd 9) —
cd /home/agent/data/sites/p2p-dash
exec python3 app.py
