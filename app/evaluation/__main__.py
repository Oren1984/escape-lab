"""Run the fixed evaluation suite from the command line.

    python -m app.evaluation [output.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.evaluation.suite import fault_cases, run_suite, suite_report


def main() -> int:
    outcomes = run_suite()
    report = {**suite_report(outcomes), "fault_cases": fault_cases()}
    for row in report["results"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'}  replay={row['reproducible']}  {row['id']:34s} {row['outcome']}")
    print(f"{report['passed']}/{report['scenarios']} scenarios met expectations, "
          f"{report['reproducible']}/{report['scenarios']} replayed identically, "
          f"{sum(c['ok'] for c in report['fault_cases'])}/{len(report['fault_cases'])} adapter fault cases safe")
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return 0 if report["passed"] == report["scenarios"] == report["reproducible"] else 1


if __name__ == "__main__":
    sys.exit(main())
