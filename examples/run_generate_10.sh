#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== Normalizing entities ==="
python3 -m taskgen.cli normalize --input data/entities --output data/normalized/entities.json

echo "=== Generating 10 curated examples (mock LLM) ==="
python3 -m taskgen.cli generate-examples --count 10 --mock-llm --entities data/normalized/entities.json --output data/outputs/examples/generated_10_examples.json

echo "Done!"
