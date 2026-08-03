#!/bin/bash
cd /home/agent/data/sites/p2p-dash/bridge
nohup python3 mesh_peer.py > mesh_peer.log 2>&1 &
echo "mesh_peer started (PID $!)"
