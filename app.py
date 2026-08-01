"""P2P Mesh Dashboard Backend — FastAPI + AgentMesh.
v0.5.1 — Shows real mesh-node state: subscriptions, WAL, DHT, peers, latency.
API endpoints for frontend.
"""

import asyncio
import collections
import json
import os
import statistics
import sys
import time

# Add project to path
sys.path.insert(0, "/home/agent/data/projects/p2p-agent-mesh")

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from sdk.agent import AgentMesh
from phase0.transport import _bus, _bus_lock

app = FastAPI(title="P2P Mesh Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
mesh: AgentMesh = None
message_history: list[dict] = []
MAX_HISTORY = 200

# Latency tracking (last 1000 request durations in ms)
_request_latencies: list[float] = []
MAX_LATENCY_SAMPLES = 1000


# --- Middleware: track all request latencies ---
@app.middleware("http")
async def track_latency(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    dt = (time.time() - t0) * 1000  # ms
    _request_latencies.append(dt)
    if len(_request_latencies) > MAX_LATENCY_SAMPLES:
        _request_latencies[:] = _request_latencies[-MAX_LATENCY_SAMPLES:]
    return response


class EmitRequest(BaseModel):
    capability: str
    payload: dict


@app.on_event("startup")
async def startup():
    global mesh
    db_path = "/tmp/p2p_dash_mesh.db"
    mesh = AgentMesh("dashboard", ["dash", "ping", "echo"],
                     db_path=db_path)
    try:
        await mesh.start()
        print(f"[dash] AgentMesh started: {mesh.did}")

        # Добавляем агентов в allowlist (DHT публикации без подписи)
        mesh.sig_gate.set_allowlist(["dashboard", "cryter-agent", "forecaster-agent", "archivist-agent", "mesh-connector", "relay-mesh-bridge"])

        # Включаем relay mode — форвард сообщений между пирами
        try:
            mesh.transport._relay = True
            print("[dash] Relay mode enabled")
        except AttributeError:
            pass

        # Save P2P port for init.sh
        try:
            p2p_port = mesh.transport._tcp_port
            with open("/home/agent/data/p2p_dash_port.txt", "w") as f:
                f.write(str(p2p_port))
            print(f"[dash] P2P port saved: {p2p_port}")
        except Exception as e:
            print(f"[dash] Failed to save P2P port: {e}")

        # Subscribe directly to agent topics BEFORE mesh.listen
        # (mesh.listen подписывает транспорт на agent:echo — наш бы пропустился)
        def on_agent_msg(data):
            """Прямая подписка на всех агентов (все сообщения от них)."""
            try:
                msg = json.loads(data) if isinstance(data, bytes) else data
                msg["_received_at"] = time.time()
                msg["_topic"] = "agent:*"
                message_history.append(msg)
                if len(message_history) > MAX_HISTORY:
                    message_history[:] = message_history[-MAX_HISTORY:]
                print(f"[dash] AGENT MSG: {msg.get('from','?')[:16]} type={msg.get('type','?')}")
            except Exception as e:
                print(f"[dash] on_agent_msg error: {e}")

        for agent_topic in ["agent:all", "agent:cryter", "agent:v2bot", "agent:forecaster", "agent:archivist"]:
            await mesh.transport.subscribe(agent_topic, on_agent_msg)
            mesh._subscribed_topics.add(agent_topic)  # sync mesh-level topic tracking

        # Subscribe to echo for the live demo
        def on_msg(msg):
            """Синхронный callback — вызывается из transport."""
            msg["_received_at"] = time.time()
            message_history.append(msg)
            if len(message_history) > MAX_HISTORY:
                message_history[:] = message_history[-MAX_HISTORY:]

        await mesh.listen({"capability": "echo"}, on_msg)
        print("[dash] Subscribed to echo")

        # Подписываемся на agent:echo уже после mesh.listen — напрямую в _bus
        # (потому что топик уже добавлен mesh.listen, subscribe его пропустит)
        on_echo_serializer = lambda data: on_agent_msg(data)
        async with _bus_lock:
            if "agent:echo" in _bus:
                _bus["agent:echo"].append(("dashboard-on_agent_msg", on_echo_serializer))
            else:
                # fallback: если топика нет — делаем subscribe
                await mesh.transport.subscribe("agent:echo", on_agent_msg)

        # Periodic heartbeat — emit to show mesh is alive
        asyncio.create_task(heartbeat_loop())
        # Discovery scanner — log DHT lookups for the dashboard
        asyncio.create_task(discovery_scanner())

    except Exception as e:
        print(f"[dash] Startup error: {e}")
        mesh = None


async def heartbeat_loop():
    """Периодический heartbeat — показывает что mesh жив."""
    while True:
        await asyncio.sleep(30)
        if mesh and mesh._running:
            try:
                await mesh.emit("echo", {
                    "type": "heartbeat",
                    "from": "dashboard",
                    "ts": time.time(),
                    "uptime": round(time.time() - _start_time, 1),
                })
                print(f"[dash] Heartbeat sent (uptime: {round(time.time() - _start_time, 1)}s)")
            except Exception as e:
                print(f"[dash] Heartbeat error: {e}")


_start_time = time.time()

# Discovery log — track DHT lookup attempts
_discovery_log: collections.deque = collections.deque(maxlen=50)

# Time-series history for sparklines/charts (last 60 points ~ 3 min at 3s polling)
_metrics_history: collections.deque = collections.deque(maxlen=60)
_msg_rate_samples: collections.deque = collections.deque(maxlen=60)


@app.get("/api/discovery")
async def get_discovery():
    """Peer discovery log — recent DHT lookups and connection attempts."""
    return {
        "status": "ok",
        "data": {
            "count": len(_discovery_log),
            "attempts": list(_discovery_log),
        }
    }


async def discovery_scanner():
    """Periodically scan for peers and log attempts."""
    while True:
        await asyncio.sleep(15)
        if not mesh or not mesh._running:
            continue
        try:
            # Check DHT
            dht_size = len(mesh.dht._cache)
            tcp_conns = len(mesh.transport._tcp_connections)
            _discovery_log.append({
                "ts": time.time(),
                "dht_size": dht_size,
                "tcp_connections": tcp_conns,
                "peer_id": mesh.transport.peer_id if hasattr(mesh.transport, 'peer_id') else "?",
                "local_port": mesh.transport._tcp_port,
            })
        except Exception:
            pass


@app.get("/api/metrics/history")
async def get_metrics_history():
    """Time-series metrics for line charts."""
    return {
        "status": "ok",
        "data": {
            "points": [
                {
                    "ts": p["ts"],
                    "msg_count": p.get("msg_count", 0),
                    "wal_count": p.get("wal_count", 0),
                    "peers": p.get("peers", 0),
                    "msg_rate": p.get("msg_rate", 0),
                }
                for p in _metrics_history
            ]
        }
    }


@app.get("/api/messages/stats")
async def get_message_stats():
    """Message type distribution and capability frequency."""
    cap_counts = collections.Counter()
    type_counts = collections.Counter()
    for msg in message_history:
        cap = msg.get("capability") or msg.get("payload", {}).get("capability") or msg.get("type", "?")
        cap_counts[cap] += 1
        mtype = msg.get("type") or msg.get("payload", {}).get("type", "event")
        type_counts[mtype] += 1
    return {
        "status": "ok",
        "data": {
            "by_capability": dict(cap_counts.most_common(10)),
            "by_type": dict(type_counts.most_common(10)),
            "total": len(message_history),
        }
    }


@app.get("/api/system")
async def get_system():
    """System resource info."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/home/agent/data")
        proc_count = len(psutil.pids())
        return {
            "status": "ok",
            "data": {
                "memory_used_gb": round(mem.used / (1024**3), 1),
                "memory_total_gb": round(mem.total / (1024**3), 1),
                "memory_pct": mem.percent,
                "disk_used_gb": round(disk.used / (1024**3), 1),
                "disk_total_gb": round(disk.total / (1024**3), 1),
                "disk_pct": disk.percent,
                "processes": proc_count,
                "load_avg": os.getloadavg()[0],
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "p2p_dash", "port": 8090}

@app.get("/api")
async def api_root():
    return {"status": "ok", "service": "p2p-mesh-dashboard", "version": "0.5.1", "endpoints": ["/api/status", "/api/peers", "/api/topics", "/api/wal", "/api/timeline", "/api/dht", "/api/messages", "/api/messages/stats", "/api/metrics", "/api/metrics/history", "/api/discovery", "/api/system", "/api/emit", "/api/mesh/graph", "/"]}


@app.get("/api/status")
async def get_status():
    if not mesh:
        return {"error": "mesh not initialized", "status": "error"}
    try:
        s = mesh.status()
        s["did"] = mesh.did
        s["agent_id"] = mesh.agent_id
        s["uptime"] = round(time.time() - _start_time, 1)
        s["capabilities"] = mesh.capabilities
        s["peer_id"] = mesh.transport.peer_id if hasattr(mesh.transport, 'peer_id') else "?"
        s["mqtt_topics"] = list(mesh._subscribed_topics)
        return {"status": "ok", "data": s}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/mesh/graph")
async def get_mesh_graph():
    """Топология P2P сети: кто с кем соединён."""
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        connections = {}
        for peer_id, writer in mesh.transport._tcp_connections.items():
            addr = mesh.transport._tcp_peer_addrs.get(peer_id, ("?", 0))
            connections[peer_id] = {
                "host": addr[0],
                "port": addr[1],
                "local_port": mesh.transport._tcp_port,
            }
        return {
            "status": "ok",
            "data": {
                "local_peer_id": mesh.transport.peer_id,
                "local_node_id": mesh.transport.node_id,
                "local_port": mesh.transport._tcp_port,
                "connections": connections,
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/peers")
async def get_peers():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        # Используем TCP connections напрямую (peers() включает _bus subscribers)
        tcp_peers = list(mesh.transport._tcp_connections.keys())
        # Маппинг peer_id → читаемое имя
        name_map = {
            "dashboard": "dashboard",
            "cryter-agent": "cryter",
            "forecaster-agent": "forecaster",
            "archivist-agent": "archivist",
            "mesh-connector": "mesh-connector",
            "relay-mesh-bridge": "relay-mesh-bridge",
        }
        peer_names = [
            {"peer_id": p, "name": name_map.get(p, p)}
            for p in tcp_peers
        ]
        return {
            "status": "ok",
            "data": {
                "count": len(tcp_peers),
                "peers": tcp_peers[:50],
                "peer_names": peer_names,
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/topics")
async def get_topics():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        topics = list(mesh._subscribed_topics)
        return {"status": "ok", "data": {"count": len(topics), "topics": topics}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/wal")
async def get_wal():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        count = mesh.wal.count()
        return {"status": "ok", "data": {"count": count, "entries": []}}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/timeline")
async def get_timeline():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        events = mesh.wal.replay("_dht", limit=200)
        timeline = []
        for e in events:
            if isinstance(e, dict):
                ts = e.get("ts", 0) or e.get("received_at", 0)
                sender = e.get("sender", "") or e.get("from", "") or "?"
                payload = e.get("payload", "")
                # Extract peer info from payload if it's a dict/JSON
                if isinstance(payload, dict):
                    sender = payload.get("from", sender)
                timeline.append({
                    "ts": ts,
                    "sender": str(sender)[:40],
                    "event": "announce"
                })
        return {"status": "ok", "data": {"events": timeline, "count": len(timeline)}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_dht():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        cache = dict(mesh.dht._cache)
        entries = []
        for key, val in cache.items():
            entries.append({
                "key": key,
                "value": val.get("value", {}),
                "ts": round(val.get("ts", 0), 1),
                "ttl": val.get("ttl", 0),
            })
        return {"status": "ok", "data": {"count": len(entries), "entries": entries}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/messages")
async def get_messages(limit: int = 50):
    global message_history
    msgs = message_history[-limit:]
    return {
        "status": "ok",
        "data": {
            "count": len(msgs),
            "total": len(message_history),
            "messages": msgs,
        }
    }


@app.get("/api/metrics")
async def get_metrics():
    if not mesh:
        return {"error": "mesh not initialized"}
    try:
        wal_count = mesh.wal.count()
        topic_count = len(mesh._subscribed_topics)
        msg_count = len(message_history)
        peers = await mesh.transport.peers()
        dht_count = len(mesh.dht._cache)
        sig_stats = mesh.sig_gate.stats()

        # Latency stats
        lats = _request_latencies.copy() if _request_latencies else [0]
        lats_sorted = sorted(lats)
        n = len(lats_sorted)
        p50 = lats_sorted[int(n * 0.50)]
        p99 = lats_sorted[min(int(n * 0.99), n - 1)]
        avg = round(statistics.mean(lats), 1)

        # Message rate (per minute, based on recent 30 seconds)
        msg_rate = 0
        if len(_metrics_history) >= 2:
            prev = _metrics_history[-2]
            delta_msgs = msg_count - prev.get("msg_count", 0)
            delta_time = time.time() - prev.get("ts", time.time())
            if delta_time > 0:
                msg_rate = round(delta_msgs / delta_time * 60, 1)  # msg/min

        # Save history point
        _metrics_history.append({
            "ts": time.time(),
            "msg_count": msg_count,
            "wal_count": wal_count,
            "peers": len(peers),
            "msg_rate": msg_rate,
        })

        return {
            "status": "ok",
            "data": {
                "wal_count": wal_count,
                "topic_count": topic_count,
                "message_count": msg_count,
                "peers": len(peers),
                "dht_entries": dht_count,
                "sig_stats": sig_stats,
                "uptime": round(time.time() - _start_time, 1),
                "msg_rate": msg_rate,
                "latency": {
                    "p50_ms": round(p50, 1),
                    "p99_ms": round(p99, 1),
                    "avg_ms": avg,
                    "samples": n,
                },
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/emit")
async def emit_message(req: EmitRequest):
    global message_history
    if not mesh:
        raise HTTPException(status_code=503, detail="mesh not initialized")
    try:
        msg_id = await mesh.emit(req.capability, req.payload)
        # Message will be added to message_history by the transport callback
        # (on_agent_msg handles agent:* topics including agent:cryter, agent:v2bot)
        return {"status": "ok", "msg_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Agent-to-Agent ping-pong ──────────────────────────

_pingpong_results = []  # list of {ts, latency_ms}


@app.get("/api/latency/pingpong")
async def get_pingpong():
    """Return recent A2A ping-pong results + run a new one."""
    global _pingpong_results
    if not mesh:
        return {"status": "error", "error": "mesh not initialized"}

    # Run one ping-pong
    seq = int(time.time() * 1000) % 1000000
    ts_sent = time.time()
    try:
        await mesh.emit("cryter", {"type": "ping", "seq": seq, "ts_sent": ts_sent})
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Wait for it to appear in message_history (poll 100ms, 2s timeout)
    found = None
    for _ in range(20):
        await asyncio.sleep(0.1)
        for m in message_history:
            p = m.get("payload", {})
            if isinstance(p, dict) and p.get("seq") == seq:
                found = m["_received_at"]
                break
        if found:
            break

    if found:
        latency_ms = round((found - ts_sent) * 1000, 1)
        _pingpong_results.append({"ts": time.time(), "latency_ms": latency_ms})
    else:
        latency_ms = -1
        _pingpong_results.append({"ts": time.time(), "latency_ms": -1})

    # Keep last 200 results
    if len(_pingpong_results) > 200:
        _pingpong_results = _pingpong_results[-200:]

    # Calculate distribution buckets
    vals = [r["latency_ms"] for r in _pingpong_results if r["latency_ms"] > 0]
    buckets = [0] * 10  # 0-2, 2-4, 4-8, 8-16, 16-32, 32-64, 64-128, 128-256, 256-512, 512+
    for v in vals:
        if v <= 2: buckets[0] += 1
        elif v <= 4: buckets[1] += 1
        elif v <= 8: buckets[2] += 1
        elif v <= 16: buckets[3] += 1
        elif v <= 32: buckets[4] += 1
        elif v <= 64: buckets[5] += 1
        elif v <= 128: buckets[6] += 1
        elif v <= 256: buckets[7] += 1
        elif v <= 512: buckets[8] += 1
        else: buckets[9] += 1

    vals.sort()
    n = len(vals)
    return {
        "status": "ok",
        "data": {
            "latest_ms": latency_ms,
            "samples": n,
            "distribution": buckets,
            "buckets": ["0-2", "2-4", "4-8", "8-16", "16-32", "32-64", "64-128", "128-256", "256-512", "512+"],
            "p50": round(vals[int(n * 0.50)], 1) if n else None,
            "p99": round(vals[min(int(n * 0.99), n - 1)], 1) if n else None,
            "avg": round(statistics.mean(vals), 1) if n else None,
        }
    }


# Serve frontend — статика по /app/ пути, API по /api/
from pathlib import Path
site_dir = Path("/home/agent/data/sites/p2p-dash")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((site_dir / "index.html").read_text())


app.mount("/static/", StaticFiles(directory=str(site_dir / "static")), name="static")
app.mount("/css/", StaticFiles(directory=str(site_dir / "css")), name="css")
app.mount("/js/", StaticFiles(directory=str(site_dir / "js")), name="js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
