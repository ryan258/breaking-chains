"""Run and report the deterministic version-one acceptance gate."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
CHECKLIST = PROJECT_ROOT / "docs/acceptance-checklist.md"
EVIDENCE = {
    1: "locked uv environment and configuration tests",
    2: "secret-safe config-check tests",
    3: "CLI completion and resume tests",
    4: "Streamlit deterministic completion tests",
    5: "source and prior-investigation seed tests",
    6: "depth-budget unit and integration tests",
    7: "three-checkpoint acceptance scenario",
    8: "epistemic and Markdown traceability tests",
    9: "Skeptic contract and completed acceptance record",
    10: "Experiment Designer contract and completed acceptance record",
    11: "restart and provider-recovery tests",
    12: "readable Markdown and SQLite search tests",
    13: "projection rebuild and relationship tests",
    14: "no-credential suite with separate optional smoke",
    15: "secret tests and prohibited-search source scan",
    16: "source consent and isolation tests",
    17: "shared A-E contract and recorded decision kinds",
    18: "responsive Chromium accessibility tests",
}
REQUIRED_PATHS = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / ".env.example",
    PROJECT_ROOT / "tests/e2e/test_acceptance.py",
    PROJECT_ROOT / "tests/e2e/test_streamlit_accessibility.py",
)
FORBIDDEN_SEARCH_MARKERS = ("search_query", "web_search", "duckduckgo", "serpapi", "tavily")


def _run(command: list[str]) -> None:
    print(f"\n$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _validate_evidence() -> None:
    checklist = CHECKLIST.read_text(encoding="utf-8")
    numbered_rows = {
        int(match.group(1))
        for match in re.finditer(r"^\|\s*(\d+)\s*\|", checklist, flags=re.MULTILINE)
    }
    if numbered_rows != set(EVIDENCE):
        raise RuntimeError("acceptance checklist must contain exactly criteria 1 through 18")
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in REQUIRED_PATHS if not path.is_file()]
    if missing:
        raise RuntimeError("missing acceptance evidence: " + ", ".join(missing))

    application_text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (PROJECT_ROOT / "src/forge").rglob("*.py")
    )
    present_markers = [marker for marker in FORBIDDEN_SEARCH_MARKERS if marker in application_text]
    if present_markers:
        raise RuntimeError("general web-search marker found: " + ", ".join(present_markers))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and report evidence without rerunning the executable test gates.",
    )
    arguments = parser.parse_args()

    _validate_evidence()
    if not arguments.check_only:
        _run([sys.executable, "-m", "pytest"])
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "tests/integration",
                "tests/e2e",
                "--cov=forge.domain",
                "--cov-fail-under=90",
            ]
        )
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "tests/integration",
                "tests/e2e",
                "--cov=forge.application",
                "--cov-fail-under=90",
            ]
        )
        _run([sys.executable, "-m", "ruff", "check", "."])
        _run([sys.executable, "-m", "ruff", "format", "--check", "."])

    for criterion, evidence in EVIDENCE.items():
        print(f"[{criterion:02d}/18] PASS — {evidence}")
    print("\nAutomated version-one acceptance evidence is complete.")
    print("Human physical-usability review and the optional paid smoke remain separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
