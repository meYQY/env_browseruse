# CLAUDE.md

## Project

Browser-use task generation framework. Generates structured, verifiable browser-use tasks from an environment entity database using controlled templates, difficulty rules, and deterministic ground truth/verifier generation.

## Key Architecture Decisions

- LLM is ONLY used for natural-language rendering (Stage 9). All ground truth, verifiers, and task structure are deterministic.
- Difficulty is controlled BEFORE generation via structure rules, not assigned afterward.
- Requirements come from controlled banks, never LLM-invented.
- Verifier templates are NOT executed without a live backend. `execution_status: "not_executed"` is honest.

## Commands

```bash
# Run tests (no API key needed)
PYTHONPATH=src python3 -m pytest tests/ -v

# Normalize entities
PYTHONPATH=src python3 -m taskgen.cli normalize --input data/entities --output data/normalized/entities.json

# Generate 100 tasks (mock LLM)
PYTHONPATH=src python3 -m taskgen.cli generate --count 100 --mock-llm --entities data/normalized/entities.json --output data/outputs/runs/latest/generated_tasks_100.json

# Generate 10 curated examples (mock LLM)
PYTHONPATH=src python3 -m taskgen.cli generate-examples --count 10 --mock-llm --entities data/normalized/entities.json --output data/outputs/examples/generated_10_examples.json

# Diversity report
PYTHONPATH=src python3 -m taskgen.cli report --input data/outputs/runs/latest/generated_tasks_100.json
```

## Environment Variables (for Kimi API production mode)

- `KIMI_API_KEY` — required for production
- `KIMI_BASE_URL` — optional, defaults to Moonshot AI endpoint
- `KIMI_MODEL` — optional, defaults to `kimi-k2.6`

## Source Layout

- `src/taskgen/` — main package (schemas, loaders, pipeline stages 0-12, CLI)
- `config/` — YAML configs (generation plan, structure rules, templates, requirement banks)
- `data/entities/` — raw WebArena extractions (gitlab, shopping, reddit JSON)
- `data/normalized/` — normalized entity database
- `data/outputs/examples/` — curated example outputs
- `data/outputs/baseline/` — fixed-seed baseline outputs
- `data/outputs/runs/` — per-run generated outputs
- `data/outputs/cache/` — LLM cache and other intermediate output artifacts
- `legacy/` — archived prototype scripts/configs/outputs not used by the main pipeline
- `tests/` — 76 tests covering all pipeline stages

## Pipeline Stages

0. Load assets (loaders.py, RuntimeContext)
1. Build generation cells (planning.py)
2. Select structure variant (structure_rules.py)
3. Select task template (template_registry.py)
4. Select target entity (entity_selector.py)
5. Fill controlled requirements (requirement_selector.py)
6. Build structured task spec (pipeline.py)
7. Generate ground truth (ground_truth.py)
8. Generate verifier template (verifier.py)
9. Generate NL instruction (instruction_generator.py + llm/)
10. Quality checks (quality.py)
11. Diversity enforcement (diversity.py)
12. Export (exporter.py)
