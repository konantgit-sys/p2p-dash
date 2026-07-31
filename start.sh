#!/bin/bash
cd /home/agent/data/sites/p2p-dash
exec python3 app.py >> /home/agent/data/sites/p2p-dash/server.log 2>&1
