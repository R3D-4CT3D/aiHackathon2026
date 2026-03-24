#!/usr/bin/env bash
cd "$(dirname "$0")"
venv/bin/streamlit run app.py --server.port 8503 --server.headless false
