#!/usr/bin/env python3
"""
Mesh Peer — регистрируется как TCP-пир + шлёт heartbeats через HTTP /api/emit.
Виден в peers list, mesh graph, и создаёт реальный трафик.

Usage: python3 mesh_peer.py
"""

import asyncio, json, time, sys, os
import urllib.request

# Unbuffered output — logs appear in file immediately
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

PEER_NAME = os.environ.get("PEER_NAME", "observer-1")
PEER_ID = f"did:p2p:{PEER_NAME}"
MESH_HOST = os.environ.get("MESH_HOST", "127.0.0.1")
MESH_PORT = int(os.environ.get("MESH_PORT", "39001"))
DASHBOARD_API = os.environ.get("DASHBOARD_API", "http://127.0.0.1:8090")
DASHBOARD_HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
INTERVAL = 10  # seconds between heartbeats


def emit_via_api():
    """Send message via HTTP API (goes through mesh.emit → proper routing)."""
    seq = int(time.time() * 1000) % 100000
    payload = json.dumps({
        "capability": "observer",
        "payload": {"seq": seq, "ts": time.time(), "msg": f"Heartbeat {seq} from {PEER_NAME}"}
    }).encode()
    try:
        req = urllib.request.Request(f"{DASHBOARD_API}/api/emit", data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        return False


def register_peer():
    """Register this peer with the dashboard API (NAT Traversal v0.6.0)."""
    try:
        payload = json.dumps({
            "peer_id": PEER_ID,
            "name": PEER_NAME,
            "addr": MESH_HOST,
            "port": MESH_PORT,
        }).encode()
        req = urllib.request.Request(f"{DASHBOARD_API}/api/register_peer", data=payload,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        print(f"[{PEER_NAME}] Registered with dashboard: {data.get('status','?')}")
        return True
    except Exception as e:
        print(f"[{PEER_NAME}] ⚠️ Registration failed: {e}")
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
    print(f"[{PEER_NAME}] Starting... (host={MESH_HOST}, port={MESH_PORT}, api={DASHBOARD_API})")

    reconnect_delay = 2
    while True:
        try:
            reader, writer = await tcp_connect()
            reconnect_delay = 2
            print(f"[{PEER_NAME}] ✅ TCP connected, registered as peer")

            # Register via HTTP API (NAT Traversal v0.6.0)
            register_peer()

            # Background reader — track task to detect disconnects
            reader_task = asyncio.create_task(read_loop(reader))

            # Heartbeat loop
            seq = 0
            while True:
                await asyncio.sleep(INTERVAL)
                seq += 1

                # TCP dead-check: if reader died, connection is broken
                if reader_task.done():
                    exc = reader_task.exception()
                    raise ConnectionResetError(f"reader died: {exc}" if exc else "reader closed")

                # Active liveness check: try writing a ping
                try:
                    ping = json.dumps({"type": "ping", "node_id": PEER_NAME, "ts": time.time()}) + "\n"
                    writer.write(ping.encode())
                    await asyncio.wait_for(writer.drain(), timeout=5)
                except Exception:
                    raise ConnectionResetError("ping failed — connection dead")

                ok = emit_via_api()
                if seq <= 3 or seq % 30 == 0:
                    print(f"[{PEER_NAME}] → heartbeat #{seq} {'✓' if ok else '✗'}")

        except (ConnectionResetError, BrokenPipeError, OSError, asyncio.TimeoutError) as e:
            print(f"[{PEER_NAME}] ⚠️ Connection lost ({e}), reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)
        except Exception as e:
            print(f"[{PEER_NAME}] ❌ Error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
