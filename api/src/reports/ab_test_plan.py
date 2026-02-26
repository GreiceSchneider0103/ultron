from __future__ import annotations

from typing import Any

from api.src.experiments.ab_rules import enforce_single_change


def generate_ab_test_plan(hypotheses: list[dict[str, Any]], priority_rules: dict[str, Any]) -> dict[str, Any]:
    tests = []
    for hyp in hypotheses:
        tests.append(enforce_single_change(hypothesis=hyp, rules=priority_rules))
    return {"tests": tests}
