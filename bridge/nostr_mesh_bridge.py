#!/usr/bin/env python3
"""
Nostr → P2P Mesh Bridge
Lightweight bridge: watches Cryter & V2Bot Nostr posts, emits them into P2P Agent Mesh.
Minimal RAM (~20MB), single websocket + HTTP POST.

Usage: python3 nostr_mesh_bridge.py
"""

import asyncio
import json
import time
import sys
import os
from urllib.request import Request, urlopen
from urllib.error import URLError

# Force unbuffered output for logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# ═══ CONFIG ═══
RELAY = "wss://nos.lol"
MESH_API = "http://127.0.0.1:8090/api/emit"
AGENTS = {
    "cryter": "8ae7965af1b61347bb9900b91cfa9487e4da2400bdb063521ad0850706ff5f96",
    "v2bot": "39c15ed9502a781fa15abc132d39044c1df2a2262bdf86c7ac1d1f9d52baf2f4",
}
# Max seen IDs to keep in memory
MAX_SEEN = 500
# Reconnect backoff
INITIAL_BACKOFF = 2
MAX_BACKOFF = 120

seen_ids = set()


def emit_to_mesh(agent_name, event):
    """HTTP POST a Nostr event as a Mesh message."""
    content = event.get("content", "")
    event_id = event.get("id", "?")
    created_at = event.get("created_at", 0)
    kind = event.get("kind", 1)

    payload = json.dumps({
        "capability": f"{agent_name}",
        "payload": {
            "event_id": event_id,
            "kind": kind,
            "content_preview": content[:200],
            "content_len": len(content),
            "created_at": created_at,
            "tags": [t for t in event.get("tags", []) if t and t[0] in ("t", "r", "e")][:5],
        },
    })

    try:
        req = Request(MESH_API, data=payload.encode(), headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return data.get("msg_id") or data.get("status") or "ok"
    except Exception as e:
        return f"err: {e}"


async def run_bridge():
    """Main loop: connect to Nostr relay, bridge events to Mesh."""
    import websockets

    print(f"[bridge] Starting Nostr→Mesh bridge")
    print(f"[bridge] Relay: {RELAY}")
    print(f"[bridge] Agents: {', '.join(AGENTS.keys())}")
    print(f"[bridge] Mesh API: {MESH_API}")

    backoff = INITIAL_BACKOFF
    sub_id = f"mesh-bridge-{int(time.time())}"

    while True:
        try:
            print(f"[bridge] Connecting to {RELAY}...")
            async with websockets.connect(
                RELAY,
                ping_interval=None,
                ping_timeout=10,
                close_timeout=5,
                open_timeout=15,
            ) as ws:
                backoff = INITIAL_BACKOFF
                print(f"[bridge] ✅ Connected")

                # Subscribe to both agents, recent + live
                authors = list(AGENTS.values())
                sub = ["REQ", sub_id, {"authors": authors, "kinds": [1], "limit": 10}]
                await ws.send(json.dumps(sub))
                print(f"[bridge] Subscribed to {len(authors)} authors (kinds=[1], limit=10)")

                recv_count = 0
                emit_count = 0

                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=120)
                        msg = json.loads(raw)
                    except asyncio.TimeoutError:
                        # No messages in 2 min — ping to keep alive
                        await ws.send(json.dumps(["REQ", f"ping-{int(time.time())}", {"limit": 0}]))
                        continue

                    if msg[0] == "EVENT":
                        event = msg[2]
                        eid = event.get("id", "")

                        if eid in seen_ids:
                            continue

                        seen_ids.add(eid)

                        # Trim seen set if too large
                        if len(seen_ids) > MAX_SEEN:
                            seen_ids.clear()
                            seen_ids.add(eid)

                        # Identify which agent
                        pubkey = event.get("pubkey", "")
                        agent_name = "unknown"
                        for name, pk in AGENTS.items():
                            if pk == pubkey:
                                agent_name = name
                                break

                        content = event.get("content", "")[:120].replace("\n", " ")

                        # Emit to mesh
                        result = emit_to_mesh(agent_name, event)
                        emit_count += 1
                        recv_count += 1

                        if emit_count <= 5 or emit_count % 10 == 0:
                            print(f"[bridge] #{recv_count} [{agent_name}] {content[:80]}... → mesh: {result}")

                        # Keep seen IDs manageable
                        if len(seen_ids) > MAX_SEEN * 2:
                            # Keep only newest
                            seen_ids.clear()

                    elif msg[0] == "EOSE":
                        print(f"[bridge] Caught up with stored events ({recv_count} received, {emit_count} emitted)")
                    elif msg[0] == "NOTICE":
                        print(f"[bridge] Relay notice: {msg[1]}")
                    elif msg[0] == "OK":
                        pass  # our REQ was acknowledged
                    else:
                        pass  # other message types

        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedError,
                ConnectionRefusedError,
                OSError) as e:
            print(f"[bridge] ⚠️ Disconnected: {e}")
        except Exception as e:
            print(f"[bridge] ⚠️ Error: {type(e).__name__}: {e}")

        print(f"[bridge] Reconnecting in {backoff}s...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF)
        sub_id = f"mesh-bridge-{int(time.time())}"


if __name__ == "__main__":
    asyncio.run(run_bridge())
