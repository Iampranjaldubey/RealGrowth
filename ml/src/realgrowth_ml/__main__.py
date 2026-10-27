"""``python -m realgrowth_ml {train,anomaly,all}``.

Typical refresh, from the repo root::

    python -m realgrowth.ingest                 # 1. fetch fresh API snapshots
    python -m realgrowth.etl                    # 2. build the warehouse
    python -m realgrowth_ml all                 # 3. train, evaluate, write data/models/
    python -m realgrowth.etl                    # 4. rebuild so the API serves the new models

Step 4 is a rebuild rather than an update because the warehouse is always a
pure function of committed files.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from realgrowth_ml import anomaly, forecasting
from realgrowth_ml.config import DEFAULT_DB, DEFAULT_MODELS_DIR
from realgrowth_ml.data import load_panel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m realgrowth_ml")
    parser.add_argument("command", choices=("train", "anomaly", "all"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--no-tune", action="store_true", help="skip hyperparameter search")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s", stream=sys.stderr)

    panel = load_panel(args.db)

    if args.command in {"anomaly", "all"}:
        result = anomaly.evaluate(panel)
        out = anomaly.write_artifacts(result, args.models)
        d = result.card["detectors"]
        print(f"anomaly: labels {result.card['labels']['imputed_cells']} imputed cells")
        for name, det in d.items():
            budget = det["at_rule_budget"]
            print(
                f"  {name:<17} PR-AUC {det['pr_auc'] or float('nan'):.3f}  "
                f"precision {budget['precision']:.3f}  recall {budget['recall']:.3f}"
            )
        print(f"  -> {out}")

    if args.command in {"train", "all"}:
        experiment = forecasting.run_experiment(panel, tune_models=not args.no_tune)
        out = forecasting.write_artifacts(experiment, args.models)
        card = experiment.card
        print(f"forecasting: champion {card['champion']}")
        for key, m in card["champion_test"].items():
            print(
                f"  test {key}: MAE {m['mae']:.2f}pp  median AE {m['median_ae']:.2f}pp  "
                f"skill vs naive {m['skill_vs_naive']:+.1%}  80% coverage {m['coverage_80']:.1%}"
            )
        print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
