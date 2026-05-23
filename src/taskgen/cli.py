"""CLI for the browser-use task generation framework."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_inspect_data(args: argparse.Namespace) -> None:
    """Inspect existing raw data files."""
    data_dir = Path(args.data_dir)
    for sub in ["entities", "."]:
        d = data_dir / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                print(f"{f}: list with {len(data)} items")
            elif isinstance(data, dict):
                keys = list(data.keys())[:10]
                print(f"{f}: dict with keys {keys}")
                if "stats" in data:
                    print(f"  stats: {data['stats']}")


def cmd_normalize(args: argparse.Namespace) -> None:
    """Normalize raw data into unified entity format."""
    from .normalizer import normalize_all, save_normalized

    entities = normalize_all(Path(args.input))
    save_normalized(entities, Path(args.output))
    print(f"Normalized {len(entities)} entities -> {args.output}")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate tasks using the full pipeline."""
    from .loaders import RuntimeContext
    from .pipeline import Pipeline
    from .llm import create_provider

    ctx = RuntimeContext(
        config_dir=Path(args.config_dir),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        entities_path=Path(args.entities) if args.entities else None,
    )
    errors = ctx.validate()
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        if args.strict:
            sys.exit(1)

    mode = "fake" if args.mock_llm else "kimi"
    provider = create_provider(mode)

    pipeline = Pipeline(
        entities=ctx.entities,
        task_templates=ctx.task_templates,
        structure_rules=ctx.structure_rules,
        requirement_banks=ctx.requirement_banks,
        generation_plan=ctx.generation_plan,
        llm_provider=provider,
        seed=args.seed,
        strict=args.strict,
    )

    tasks = pipeline.run(target_count=args.count)
    output_dir = Path(args.output).parent
    pipeline.generated = tasks
    pipeline.export_all(output_dir)

    print(f"Generated {len(tasks)} tasks")
    print(f"Outputs written to {output_dir}/")


def cmd_generate_examples(args: argparse.Namespace) -> None:
    """Generate curated example set."""
    from .loaders import RuntimeContext
    from .pipeline import Pipeline
    from .llm import create_provider

    ctx = RuntimeContext(
        config_dir=Path(args.config_dir),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        entities_path=Path(args.entities) if args.entities else None,
    )

    mode = "fake" if args.mock_llm else "kimi"
    provider = create_provider(mode)

    pipeline = Pipeline(
        entities=ctx.entities,
        task_templates=ctx.task_templates,
        structure_rules=ctx.structure_rules,
        requirement_banks=ctx.requirement_banks,
        generation_plan=ctx.generation_plan,
        llm_provider=provider,
        seed=args.seed,
    )

    # Generate a large pool first, then select curated examples
    all_tasks = pipeline.run(target_count=max(args.count * 10, 100))
    pipeline.generated = all_tasks
    from . import diversity as dv
    examples = dv.select_curated_examples(all_tasks, args.count)

    from . import exporter
    output = Path(args.output)
    exporter.export_tasks_json(examples, output)
    md_path = output.with_suffix(".md")
    exporter.export_examples_markdown(examples, md_path)

    print(f"Generated {len(examples)} curated examples -> {output}")


def cmd_report(args: argparse.Namespace) -> None:
    """Generate report from existing task output."""
    from . import diversity as dv
    from . import exporter

    path = Path(args.input)
    tasks = json.loads(path.read_text(encoding="utf-8"))
    stats = dv.check_diversity(tasks)
    if args.output:
        exporter.export_generation_report(tasks, [], stats, Path(args.output))
    else:
        print(json.dumps(stats, indent=2, default=str))


def cmd_evaluate_quality(args: argparse.Namespace) -> None:
    """Compare generated tasks with official WebArena tasks using a deterministic rubric."""
    from .quality_evaluator import compare_task_sets

    generated = json.loads(Path(args.generated).read_text(encoding="utf-8"))
    webarena = json.loads(Path(args.webarena).read_text(encoding="utf-8"))
    report = compare_task_sets(generated, webarena)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="taskgen",
        description="Browser-use task generation framework",
    )
    sub = parser.add_subparsers(dest="command")

    # inspect-data
    p = sub.add_parser("inspect-data", help="Inspect raw data files")
    p.add_argument("--data-dir", default="data", help="Data directory")

    # normalize
    p = sub.add_parser("normalize", help="Normalize raw data")
    p.add_argument("--input", default="data/entities", help="Raw data directory")
    p.add_argument("--output", default="data/normalized/entities.json", help="Output path")

    # generate
    p = sub.add_parser("generate", help="Generate tasks")
    p.add_argument("--count", type=int, default=100, help="Target task count")
    p.add_argument("--output", default="data/outputs/runs/latest/generated_tasks_100.json")
    p.add_argument("--config-dir", default="config")
    p.add_argument("--data-dir", default=None)
    p.add_argument("--entities", default=None, help="Path to normalized entities")
    p.add_argument("--mock-llm", action="store_true", help="Use fake LLM provider")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--strict", action="store_true")

    # generate-examples
    p = sub.add_parser("generate-examples", help="Generate curated examples")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--output", default="data/outputs/examples/generated_10_examples.json")
    p.add_argument("--config-dir", default="config")
    p.add_argument("--data-dir", default=None)
    p.add_argument("--entities", default=None)
    p.add_argument("--mock-llm", action="store_true")
    p.add_argument("--seed", type=int, default=42)

    # report
    p = sub.add_parser("report", help="Show diversity report")
    p.add_argument("--input", default="data/outputs/runs/latest/generated_tasks_100.json")
    p.add_argument("--output", default=None)

    # evaluate-quality
    p = sub.add_parser("evaluate-quality", help="Compare generated tasks with official WebArena tasks")
    p.add_argument("--generated", default="data/outputs/runs/latest/generated_tasks_100.json")
    p.add_argument("--webarena", default="arena_repos/webarena/config_files/test.raw.json")
    p.add_argument("--output", default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "inspect-data": cmd_inspect_data,
        "normalize": cmd_normalize,
        "generate": cmd_generate,
        "generate-examples": cmd_generate_examples,
        "report": cmd_report,
        "evaluate-quality": cmd_evaluate_quality,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
