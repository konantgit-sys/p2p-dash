#!/bin/bash
cd /home/agent/data/sites/p2p-dash/bridge
exec python3 nostr_mesh_bridge.py >> /home/agent/data/sites/p2p-dash/bridge/bridge.log 2>&1
