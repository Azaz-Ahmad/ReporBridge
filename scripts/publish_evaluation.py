"""Publish selected judge-facing figures from a completed PostgreSQL test run."""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def cases(path):
    return [case for case in ElementTree.parse(path).iter("testcase")]


def passed(case):
    return not any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))


def result(selected):
    return f"{sum(map(passed, selected))}/{len(selected)} passed" if selected else "Unavailable"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = args.report.resolve()
    report.relative_to(ROOT / "test-reports")
    summary = json.loads((report / "summary.json").read_text(encoding="utf-8-sig"))
    gates = ("PostgreSQL API", "React components", "TypeScript and Vite build",
             "PostgreSQL browser journey", "PostgreSQL browser replay")
    if any(summary.get(gate) != 0 for gate in gates):
        raise SystemExit("Use a completed, passing PostgreSQL evaluation report.")

    postgres = cases(report / "postgres.xml")
    components = cases(report / "components.xml")

    def select(*names):
        return [case for case in postgres if case.attrib["name"].split("[")[0] in names]

    scenarios = select("test_import_and_evaluate", "test_trigger_abstention")
    browser_reports = ("browser", "browser-replay")
    browser_passes = sum(
        json.loads((report / f"{name}.json").read_text(encoding="utf-8"))["stats"]["expected"]
        for name in browser_reports
    )
    bundles = sum((report / f"{name}-amira-r4.json").is_file() for name in browser_reports)
    automated = {
        "Python checks on PostgreSQL": result(postgres),
        "React checks": result(components),
        "Duplicate transition prevention": result(select("test_transition_concurrent_retry_and_dependency")),
        "Reviewer authorization and verified closure": result(select("test_authorization_approval_and_success")),
        "Unsupported closure prevention": result(select("test_nonfinal_completion_cannot_close",
            "test_conflict_blocks_even_with_approval", "test_coordination_approval_is_not_completion_authorization")),
        "Audit history and reset isolation": result(select("test_amira_reset_archives_completed_work_without_touching_other_patients")),
        "Full browser journeys": f"{browser_passes}/{len(browser_reports)} passed",
        "Validated FHIR downloads": f"{bundles}/{len(browser_reports)} passed",
        "Production frontend build": "Passed",
    }
    report_data = {
        "run": report.name,
        "automated": [{"label": label, "result": value} for label, value in automated.items()],
        "synthetic": (f"{sum(map(passed, scenarios))}/{len(scenarios)} labeled synthetic cases matched the expected "
                      "detection or abstention." if scenarios else "Labeled rule results are unavailable."),
    }
    (ROOT / "frontend" / "src" / "evaluation.json").write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
