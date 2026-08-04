from __future__ import annotations

import json
from pathlib import Path

REQUIRED_MEASURES = {
    "SLA Compliance %",
    "Average Backlog Age (Hours)",
    "First Response Time (Hours)",
    "MTTR (Hours)",
    "Reopen Rate",
    "Category Trend %",
}
REQUIRED_TABLES = {"Ticket Performance.tmdl", "Calendar.tmdl"}


def main() -> None:
    analytics_root = Path(__file__).resolve().parents[1]
    model_root = analytics_root / "power-bi" / "ServiceOpsAnalytics.SemanticModel"
    definition_root = model_root / "definition"
    metadata = json.loads((model_root / "definition.pbism").read_text(encoding="utf-8"))
    if float(metadata["version"]) < 4.0:
        raise ValueError("Power BI semantic model must use TMDL-compatible definition version 4+")

    table_files = {path.name for path in (definition_root / "tables").glob("*.tmdl")}
    missing_tables = REQUIRED_TABLES - table_files
    if missing_tables:
        raise ValueError(f"Missing Power BI tables: {sorted(missing_tables)}")

    ticket_model = (definition_root / "tables" / "Ticket Performance.tmdl").read_text(
        encoding="utf-8"
    )
    missing_measures = {
        measure for measure in REQUIRED_MEASURES if f"measure '{measure}'" not in ticket_model
    }
    if missing_measures:
        raise ValueError(f"Missing Power BI measures: {sorted(missing_measures)}")

    combined_model = "\n".join(
        path.read_text(encoding="utf-8") for path in definition_root.rglob("*.tmdl")
    )
    for relation in ("analytics_mart", "fct_ticket_performance", "dim_date"):
        if relation not in combined_model:
            raise ValueError(f"Power BI model does not reference {relation}")
    forbidden = ("serviceops_dev", "serviceops_ci", "password=")
    if any(value in combined_model.lower() for value in forbidden):
        raise ValueError("Power BI model contains a credential-like value")

    print(
        f"Validated Power BI TMDL model with {len(table_files)} tables and "
        f"{len(REQUIRED_MEASURES)} required analytics measures."
    )


if __name__ == "__main__":
    main()
