#!/bin/bash
# p2p-dash v0.5.2 — single entry point
# Uses lock file to prevent duplicate instances

LOCKFILE=/tmp/p2p-dash-start.lock

# — Lock: prevent concurrent starts —
if [ -f "$LOCKFILE" ]; then
    # Check if the lock holder is still alive
    LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "[start] already starting (PID=$LOCK_PID), exiting"
        exit 0
    fi
    # Stale lock — remove it
    rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"

cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

# — Start mesh_peer (only if not already running) —
if ! pgrep -f "mesh_peer.py" > /dev/null; then
    cd /home/agent/data/sites/p2p-dash/bridge
    nohup python3 mesh_peer.py > mesh_peer.log 2>&1 &
    echo "[start] mesh_peer PID=$!"
else
    echo "[start] mesh_peer already running (PID=$(pgrep -f mesh_peer.py | head -1))"
fi

# — Start nostr_mesh_bridge (only if not already running) —
if ! pgrep -f "nostr_mesh_bridge.py" > /dev/null; then
    cd /home/agent/data/sites/p2p-dash/bridge
    nohup python3 nostr_mesh_bridge.py > bridge.log 2>&1 &
    echo "[start] bridge PID=$!"
else
    echo "[start] bridge already running (PID=$(pgrep -f nostr_mesh_bridge.py | head -1))"
fi

sleep 2

# — Start app.py (foreground) —
cd /home/agent/data/sites/p2p-dash
exec python3 app.py
