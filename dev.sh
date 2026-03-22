#!/bin/bash
trap 'kill 0' EXIT

uv run uvicorn server:app --port 8000 &
cd web && pnpm dev &

wait
