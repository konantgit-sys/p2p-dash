# P2P Agent Mesh Dashboard

Real-time monitoring dashboard for [P2P Agent Mesh](https://github.com/konantgit-sys/p2p-agent-mesh).

## Features

- Live agent discovery map
- Message throughput graphs per channel
- Relay health status (uptime, latency, errors)
- Node reputation scores
- Latency heatmaps (p50/p95/p99)

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:8050

## Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML/CSS/JS, vis-network, Chart.js
- **Transport:** TCP + JSON-lines (P2P Agent Mesh v0.5.1)

## Architecture

```
Mesh Agents (TCP:9133) → FastAPI API (:8050) → Dashboard (Browser)
```

## Related

- [P2P Agent Mesh Core](https://github.com/konantgit-sys/p2p-agent-mesh)
- [SNIN Protocol](https://github.com/konantgit-sys/snin-core)
- [Relay Mesh](https://github.com/konantgit-sys/relay-mesh)

## License

MIT © 2026 Anton
