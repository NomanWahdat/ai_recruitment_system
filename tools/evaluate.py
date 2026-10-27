"""Run a versioned labelled-data benchmark. Offline by default."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django

django.setup()
from apps.recruitment.services.evaluation import evaluate_dataset


def evaluate():
    return evaluate_dataset(ROOT / "evaluation/dataset.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(ROOT / "evaluation/dataset.json"))
    parser.add_argument("--split", default="all")
    parser.add_argument("--output")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-lsa", action="store_true")
    parser.add_argument(
        "--live-ai",
        action="store_true",
        help="Send structured, de-identified scoring fields to configured providers.",
    )
    parser.add_argument(
        "--allow-external-data",
        action="store_true",
        help="Acknowledge sending custom dataset fields to providers.",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    builtin = Path(args.dataset).resolve() == (ROOT / "evaluation/dataset.json").resolve()
    if not builtin and not args.output:
        parser.error("Custom datasets require --output, preferably under ignored .runtime/.")
    if args.live_ai and not builtin and not args.allow_external_data:
        parser.error(
            "Live custom evaluations require --allow-external-data after de-identification and consent."
        )
    if not args.output and (args.live_ai or args.split != "all" or args.limit):
        parser.error(
            "Partial/live evaluations require a separate --output; preserve the bundled offline report."
        )
    output = Path(args.output) if args.output else ROOT / "docs/evaluation-results.json"
    public = (ROOT / "docs/evaluation-results.json").resolve()
    if output.resolve() == public and (
        not builtin or args.live_ai or args.split != "all" or args.limit
    ):
        parser.error("The public report is reserved for the complete offline bundled dataset.")
    try:
        result = evaluate_dataset(
            args.dataset, args.split, args.k, args.live_ai, args.limit, args.include_lsa
        )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.error(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(result, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "records",
                    "mode",
                    "email_accuracy",
                    "experience_mae_years",
                    "skill_f1",
                    "by_split",
                    "checks",
                    "external_requests",
                ]
            },
            indent=2,
        )
    )
    if args.check and not result["checks"]["passed"]:
        raise SystemExit("Regression thresholds not met; see the per-case report.")
