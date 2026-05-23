#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== Normalizing entities ==="
python3 -m taskgen.cli normalize --input data/entities --output data/normalized/entities.json

echo "=== Generating 100 tasks (mock LLM) ==="
python3 -m taskgen.cli generate --count 100 --mock-llm --entities data/normalized/entities.json --output data/outputs/runs/latest/generated_tasks_100.json

echo "=== Report ==="
python3 -m taskgen.cli report --input data/outputs/runs/latest/generated_tasks_100.json

echo "Done!"
