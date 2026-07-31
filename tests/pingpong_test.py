#!/usr/bin/env python3
"""Agent-to-agent ping-pong test through mesh transport.

Cryter emits → transport.publish → subscription callback → message_history.
Measures full end-to-end delivery time: emit → received.
"""

import time, json, statistics
from urllib.request import Request, urlopen

MESH_API = "http://127.0.0.1:8090/api/emit"
MSG_API  = "http://127.0.0.1:8090/api/messages?limit=200"

def emit(cap, seq):
    t0 = time.monotonic()
    body = json.dumps({
        "capability": cap,
        "payload": {"seq": seq, "ts_sent": time.time(), "content": f"PING #{seq}"}
    }).encode()
    req = Request(MESH_API, data=body, headers={"Content-Type": "application/json"})
    resp = json.loads(urlopen(req, timeout=10).read())
    return resp.get("msg_id", "?")

def find_msg(seq, timeout=5.0):
    """Poll until message with seq appears in message_history."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            data = json.loads(urlopen(Request(MSG_API), timeout=5).read())
            for m in data.get("data", {}).get("messages", []):
                p = m.get("payload", {})
                if isinstance(p, dict) and p.get("seq") == seq:
                    return m["_received_at"] - p["ts_sent"]
        except:
            pass
        time.sleep(0.02)  # 20ms polling
    return None

# ── Test ──────────────────────────────────────────────────

print("╔══════════════════════════════════════════════╗")
print("║  AGENT-TO-AGENT: Cryter→Mesh→DASHBOARD      ║")
print("╚══════════════════════════════════════════════╝")

ROUNDS = 30
deltas = []
lost = 0

for i in range(1, ROUNDS + 1):
    emit("cryter", i)
    d = find_msg(i, 2.0)
    
    if d is None:
        lost += 1
        print(f"  #{i:>3}: LOST ⚠️")
    else:
        ms = round(d * 1000, 1)
        deltas.append(ms)
        bar = "█" * min(int(ms // 2), 40)
        print(f"  #{i:>3}: {ms:>6.1f}ms {bar}")

deltas.sort()
n = len(deltas)

print(f"\n{'─'*50}")
print(f"Sent: {ROUNDS}  Delivered: {n}  Lost: {lost} ({round(lost/ROUNDS*100,1)}%)")
if n:
    print(f"p50:  {deltas[int(n*0.50)]:.1f}ms")
    print(f"p95:  {deltas[min(int(n*0.95), n-1)]:.1f}ms")
    print(f"p99:  {deltas[min(int(n*0.99), n-1)]:.1f}ms")
    print(f"Min:  {deltas[0]:.1f}ms")
    print(f"Max:  {deltas[-1]:.1f}ms")
    print(f"Avg:  {round(statistics.mean(deltas),1)}ms")
