# Model dataset card

## Purpose and provenance

`training_scenarios.csv` contains 40 manually reviewed, fictional support scenarios. It has
no customer records or personal data. `serviceops_ai.dataset` deterministically combines each
scenario with five intake channels and five operating contexts to produce the tracked
`training_tickets.csv` corpus.

The generated corpus contains 1,000 unique rows: 250 for each category, with 350 `LOW`, 325
`MEDIUM`, and 325 `HIGH` labels. Its SHA-256 digest is
`e4eab186ac369f49209a5fbe4fdfaeb6505a6cb3a5796deefae97d2ef5ae3455`.

Regenerate it from the `ai-service` directory after an editable project install:

```bash
python -m serviceops_ai.dataset
python -m pytest tests/test_dataset.py
```

The test requires byte-for-byte reproducibility and the fixed digest, so seed or generator
changes must be intentional and reviewed together with the generated corpus.

## Validation design

Every generated row retains its source `scenario_id`. The model selects one whole scenario
from each category/priority combination for validation. This produces 700 training rows from
28 scenarios and 300 validation rows from 12 scenarios. Variants of one scenario therefore
cannot leak across the split, and every supported category/priority combination is represented
in validation.

The model cache records the complete generated-file digest. A changed corpus invalidates the
cached artifact even when the model code version is unchanged.

## Intended and prohibited use

This corpus is for deterministic development, integration, and regression checks. It is not
representative of real ticket frequency, language, geography, customer impact, or label noise,
and it must not be used to claim production accuracy or fairness.

Production training requires an approved, representative labeled dataset; privacy and retention
review; documented label quality; temporal validation; subgroup and bias analysis; and monitored
data/model drift. A replacement dataset must keep the required `scenario_id`, `title`,
`description`, `category`, and `priority` columns and provide at least two independent scenarios
for every category/priority combination.
