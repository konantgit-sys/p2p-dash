#!/usr/bin/env python3
"""P2P Agent Mesh — stress test: throughput & latency."""

import time
import json
import statistics
import sys
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed

MESH_API = "http://127.0.0.1:8090/api/emit"
METRICS_API = "http://127.0.0.1:8090/api/metrics"

# ── helpers ──────────────────────────────────────────────

def emit(capability: str, payload: dict) -> tuple[float, str]:
    """Emit one message, return (latency_ms, msg_id or error)."""
    t0 = time.monotonic()
    body = json.dumps({"capability": capability, "payload": payload}).encode()
    try:
        req = Request(MESH_API, data=body, headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        lat = (time.monotonic() - t0) * 1000
        return lat, data.get("msg_id", "?")
    except Exception as e:
        lat = (time.monotonic() - t0) * 1000
        return lat, f"ERR:{e}"


def get_metrics():
    try:
        return json.loads(urlopen(Request(METRICS_API), timeout=5).read())
    except:
        return {}


def run_level(rate_per_sec: int, duration: float = 8.0, cap: str = "stress"):
    """Send messages at ~rate_per_sec for `duration` seconds.
    
    Returns dict with stats.
    """
    total = max(int(rate_per_sec * duration), 5)
    interval = 1.0 / rate_per_sec if rate_per_sec > 0 else 1.0
    
    latencies = []
    errors = 0
    t_start = time.monotonic()
    
    if rate_per_sec <= 10:
        # Sequential for low rates
        for i in range(total):
            lat, mid = emit(cap, {"seq": i, "payload": f"Stress test msg #{i}", "ts": time.time()})
            if lat is not None:
                latencies.append(lat)
            if "ERR" in str(mid):
                errors += 1
            if i < total - 1:
                time.sleep(interval)
    else:
        # Threaded for high rates
        with ThreadPoolExecutor(max_workers=min(rate_per_sec, 20)) as pool:
            futures = []
            for i in range(total):
                f = pool.submit(emit, cap, {"seq": i, "payload": f"Stress test msg #{i}", "ts": time.time()})
                futures.append(f)
                if i < total - 1:
                    time.sleep(interval)
            for f in as_completed(futures):
                lat, mid = f.result()
                if lat is not None:
                    latencies.append(lat)
                if "ERR" in str(mid):
                    errors += 1
    
    elapsed = time.monotonic() - t_start
    actual_rate = len(latencies) / elapsed if elapsed > 0 else 0
    
    latencies.sort()
    n = len(latencies)
    
    return {
        "target_rate": rate_per_sec,
        "actual_rate": round(actual_rate, 1),
        "sent": total,
        "ok": n,
        "errors": errors,
        "elapsed_s": round(elapsed, 2),
        "latency_ms": {
            "min": round(latencies[0], 1) if n else None,
            "p50": round(latencies[int(n * 0.50)], 1) if n else None,
            "p75": round(latencies[int(n * 0.75)], 1) if n else None,
            "p95": round(latencies[min(int(n * 0.95), n - 1)], 1) if n else None,
            "p99": round(latencies[min(int(n * 0.99), n - 1)], 1) if n else None,
            "max": round(latencies[-1], 1) if n else None,
            "avg": round(statistics.mean(latencies), 1) if n else None,
        }
    }


# ── main ─────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  P2P AGENT MESH — STRESS TEST                  ║")
    print("╚══════════════════════════════════════════════════╝")
    
    # Baseline
    m = get_metrics()
    if m.get("status") == "ok":
        d = m["data"]
        print(f"\n📊 BASELINE: msgs={d['message_count']} wal={d['wal_count']} peers={d['peers']}")
    
    LEVELS = [
        (1, 10.0, "🥶 1 msg/s"),
        (5, 8.0, "😐 5 msg/s"),
        (10, 8.0, "🙂 10 msg/s"),
        (20, 6.0, "😤 20 msg/s"),
        (50, 5.0, "🔥 50 msg/s"),
        (100, 4.0, "💀 100 msg/s"),
        (200, 3.0, "☠️ 200 msg/s"),
        (500, 2.0, "⚡ 500 msg/s"),
    ]
    
    results = []
    print("\n" + "─" * 55)
    print(f"{'Level':<20} {'Actual':>7} {'p50':>7} {'p99':>7} {'Max':>7} {'Errors':>7}")
    print("─" * 55)
    
    for rate, dur, label in LEVELS:
        print(f"\n{label} ({rate}×{dur}s)...", end=" ", flush=True)
        r = run_level(rate, dur)
        results.append(r)
        
        lat = r["latency_ms"]
        print(f"\r{label:<20} {r['actual_rate']:>5.0f}/s {lat['p50']:>6.1f}ms {lat['p99']:>6.1f}ms {lat['max']:>6.1f}ms {r['errors']:>5}err")
        
        # Check if mesh is still alive
        if r["errors"] > r["sent"] * 0.5:
            print(f"\n⚠️  >50% errors at {rate} msg/s — CEILING FOUND")
            break
        
        # Brief cooldown
        time.sleep(1.5)
    
    # ── Final report ──
    print("\n" + "═" * 55)
    print("FINAL REPORT")
    print("═" * 55)
    print(f"{'Level':<20} {'Act/s':>6} {'p50':>7} {'p99':>7} {'Max':>7} {'Err':>5}")
    print("─" * 55)
    
    for r in results:
        lat = r["latency_ms"]
        print(f"{r['target_rate']:>3} msg/s{' ':<13} {r['actual_rate']:>4.0f}  {lat['p50']:>6.1f} {lat['p99']:>6.1f} {lat['max']:>6.1f} {r['errors']:>4}")
    
    # Find ceiling: where p99 exceeds 500ms
    ceiling = None
    for r in results:
        lat = r["latency_ms"]
        if lat["p99"] and lat["p99"] > 500:
            ceiling = r["target_rate"]
            break
    
    m2 = get_metrics()
    if m2.get("status") == "ok":
        d2 = m2["data"]
        total_sent = sum(r["sent"] for r in results)
        print(f"\n📊 AFTER: msgs={d2['message_count']} wal={d2['wal_count']} (+{total_sent} stress msgs)")

    if ceiling:
        print(f"\n🔴 CEILING: ~{ceiling} msg/s (p99 breaks 500ms)")
    else:
        print(f"\n🟢 NO CEILING FOUND — wire protocol sustains all test levels")
    
    return results


if __name__ == "__main__":
    main()
