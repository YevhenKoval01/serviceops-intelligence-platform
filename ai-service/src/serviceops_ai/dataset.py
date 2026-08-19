from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Final

AI_SERVICE_ROOT = next(
    (
        candidate
        for candidate in (
            Path.cwd(),
            Path.cwd() / "ai-service",
            Path(__file__).resolve().parents[2],
        )
        if (candidate / "data" / "training_scenarios.csv").is_file()
    ),
    Path.cwd(),
)
DEFAULT_SEED_PATH = AI_SERVICE_ROOT / "data" / "training_scenarios.csv"
DEFAULT_OUTPUT_PATH = AI_SERVICE_ROOT / "data" / "training_tickets.csv"

SEED_COLUMNS: Final = ("scenario_id", "title", "description", "category", "priority")
DATASET_COLUMNS: Final = SEED_COLUMNS
ALLOWED_CATEGORIES: Final = {"ACCESS", "BILLING", "DELIVERY", "TECHNICAL"}
ALLOWED_PRIORITIES: Final = {"LOW", "MEDIUM", "HIGH"}

CHANNELS: Final = (
    ("support portal", "portal"),
    ("email", "email"),
    ("telephone", "phone"),
    ("live chat", "chat"),
    ("monitoring alert", "monitoring"),
)
CONTEXTS: Final = (
    ("customer web portal", "web portal"),
    ("mobile application", "mobile app"),
    ("partner integration", "partner integration"),
    ("internal operations console", "operations console"),
    ("regional service desk", "service desk"),
)
VARIANTS_PER_SCENARIO: Final = len(CHANNELS) * len(CONTEXTS)


def read_scenarios(seed_path: Path) -> list[dict[str, str]]:
    with seed_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != SEED_COLUMNS:
            raise ValueError(f"Scenario file must contain columns {list(SEED_COLUMNS)}")
        scenarios = [dict(row) for row in reader]

    if not scenarios:
        raise ValueError("Scenario file must contain at least one scenario")
    for row_number, scenario in enumerate(scenarios, start=2):
        if any(not scenario[column].strip() for column in SEED_COLUMNS):
            raise ValueError(f"Scenario file contains an empty value on row {row_number}")

    scenario_ids = [scenario["scenario_id"] for scenario in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Scenario ids must be unique")
    if {scenario["category"] for scenario in scenarios} != ALLOWED_CATEGORIES:
        raise ValueError("Scenario file must contain exactly the four baseline categories")
    if not {scenario["priority"] for scenario in scenarios}.issubset(ALLOWED_PRIORITIES):
        raise ValueError("Scenario file contains an unsupported priority")
    return scenarios


def generate_rows(scenarios: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for scenario in scenarios:
        for channel_description, channel_title in CHANNELS:
            for context_description, context_title in CONTEXTS:
                rows.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "title": (
                            f"{scenario['title']} ({context_title}, {channel_title})"
                        ),
                        "description": (
                            f"{scenario['description']} Reported through {channel_description} "
                            f"for the {context_description}."
                        ),
                        "category": scenario["category"],
                        "priority": scenario["priority"],
                    }
                )
    return rows


def write_dataset(seed_path: Path, output_path: Path) -> int:
    if seed_path.resolve() == output_path.resolve():
        raise ValueError("Seed and output paths must be different")
    rows = generate_rows(read_scenarios(seed_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as destination:
            writer = csv.DictWriter(
                destination,
                fieldnames=DATASET_COLUMNS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return len(rows)


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic ServiceOps model regression dataset."
    )
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    row_count = write_dataset(args.seed, args.output)
    print(f"Generated {row_count} training rows at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
