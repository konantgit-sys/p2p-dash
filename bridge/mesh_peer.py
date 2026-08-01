#!/usr/bin/env python3
"""
Mesh Peer — регистрируется как TCP-пир + шлёт heartbeats через HTTP /api/emit.
Виден в peers list, mesh graph, и создаёт реальный трафик.

Usage: python3 mesh_peer.py
"""

import asyncio, json, time
import urllib.request

PEER_NAME = "observer-1"
PEER_ID = f"did:p2p:{PEER_NAME}"
MESH_HOST = "127.0.0.1"
MESH_PORT = 39001
DASHBOARD_API = "http://127.0.0.1:8090/api/emit"
INTERVAL = 10  # seconds between heartbeats


def emit_via_api():
    """Send message via HTTP API (goes through mesh.emit → proper routing)."""
    seq = int(time.time() * 1000) % 100000
    payload = json.dumps({
        "capability": "observer",
        "payload": {"seq": seq, "ts": time.time(), "msg": f"Heartbeat {seq} from {PEER_NAME}"}
    }).encode()
    try:
        req = urllib.request.Request(DASHBOARD_API, data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        return False


async def tcp_connect():
    """Connect to dashboard mesh as TCP peer."""
    reader, writer = await asyncio.open_connection(MESH_HOST, MESH_PORT)

    # Hello
    hello = json.dumps({"type": "hello", "node_id": PEER_NAME, "peer_id": PEER_ID}) + "\n"
    writer.write(hello.encode()); await writer.drain()
    resp = json.loads((await reader.readline()).decode().strip())
    remote = resp.get("peer_id", "?")
    print(f"[{PEER_NAME}] ✅ Handshake with {remote}")

    # Subscribe
    for topic in ["agent:all", "agent:cryter", "agent:v2bot", "agent:echo", "agent:observer"]:
        sub = json.dumps({"type": "sub", "topic": topic, "node_id": PEER_NAME}) + "\n"
        writer.write(sub.encode())
    await writer.drain()

    return reader, writer


async def read_loop(reader):
    """Silently read incoming TCP messages to keep connection alive."""
    while True:
        line = await reader.readline()
        if not line:
            break


async def main():
    print(f"[{PEER_NAME}] Starting...")

    reconnect_delay = 2
    while True:
        try:
            reader, writer = await tcp_connect()
            reconnect_delay = 2
            print(f"[{PEER_NAME}] Peer registered")

            # Background reader
            asyncio.create_task(read_loop(reader))

            # Heartbeat loop
            seq = 0
            while True:
                await asyncio.sleep(INTERVAL)
                seq += 1
                ok = emit_via_api()
                if seq <= 3 or seq % 30 == 0:
                    print(f"[{PEER_NAME}] → heartbeat #{seq} {'✓' if ok else '✗'}")
                # Check if still connected
                if writer.is_closing():
                    raise ConnectionResetError("writer closed")

        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[{PEER_NAME}] ⚠️ Connection lost ({e}), reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)
        except Exception as e:
            print(f"[{PEER_NAME}] ❌ Error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
