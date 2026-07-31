#!/usr/bin/env python3
"""Full cycle stress: emit → transport → callback → message_history.

Uses a subscribed topic (cryter) to force the full mesh cycle.
"""

import time, json, statistics
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed

MESH_API = "http://127.0.0.1:8090/api/emit"
MSG_API  = "http://127.0.0.1:8090/api/messages?limit=5"
METRICS  = "http://127.0.0.1:8090/api/metrics"

def emit_fullcycle(seq):
    """Emit with full payload like Cryter would."""
    t0 = time.monotonic()
    body = json.dumps({
        "capability": "cryter",
        "payload": {
            "event_id": f"test_{seq:06d}",
            "kind": 1,
            "content_preview": f"Full-cycle stress message #{seq} — testing transport→callback pipeline",
            "content_len": 120,
            "created_at": int(time.time()),
            "tags": [["t", "stress"], ["t", "benchmark"]],
        }
    }).encode()
    try:
        req = Request(MESH_API, data=body, headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        lat = (time.monotonic() - t0) * 1000
        return lat, data.get("msg_id", "?")
    except Exception as e:
        return (time.monotonic() - t0) * 1000, f"ERR:{e}"


def count_cryter_msgs():
    """Count how many cryter messages in message_history."""
    try:
        data = json.loads(urlopen(Request(MSG_API), timeout=5).read())
        msgs = data.get("data", {}).get("messages", [])
        return sum(1 for m in msgs if m.get("topic") == "agent:cryter")
    except:
        return -1


print("╔══════════════════════════════════════════════════╗")
print("║  FULL CYCLE: emit→transport→callback→history    ║")
print("╚══════════════════════════════════════════════════╝")

before = count_cryter_msgs()
print(f"\nCryter msgs before: {before}")

LEVELS = [1, 5, 10, 20, 50, 100, 200]
print(f"\n{'Rate':>6} {'Fact/s':>7} {'p50':>7} {'p99':>7} {'Max':>7} {'Err':>5}  {'InHistory':>10}")
print("─" * 58)

for rate in LEVELS:
    total = max(rate * 4, 10)
    interval = 1.0 / rate if rate > 0 else 1.0
    
    t0 = time.monotonic()
    lats = []
    errs = 0
    
    with ThreadPoolExecutor(max_workers=min(rate + 2, 20)) as pool:
        futures = []
        for i in range(total):
            f = pool.submit(emit_fullcycle, i)
            futures.append(f)
            if i < total - 1:
                time.sleep(interval)
        for f in as_completed(futures):
            lat, mid = f.result()
            lats.append(lat)
            if "ERR" in str(mid):
                errs += 1
    
    elapsed = time.monotonic() - t0
    actual = len(lats) / elapsed if elapsed > 0 else 0
    
    lats.sort()
    n = len(lats)
    p50 = lats[int(n*0.5)] if n else 0
    p99 = lats[min(int(n*0.99), n-1)] if n else 0
    mx  = lats[-1] if n else 0
    
    time.sleep(2)
    after = count_cryter_msgs()
    delta = after - before
    
    print(f"{rate:>4}/s {actual:>6.0f}  {p50:>6.1f} {p99:>6.1f} {mx:>6.1f} {errs:>4}  {delta:>10}")

print("\n✅ Full cycle test done")
