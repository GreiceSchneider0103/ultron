from __future__ import annotations

from typing import Any


def generate_action_plan(findings: dict[str, Any], constraints: dict[str, Any]) -> dict[str, Any]:
    actions = findings.get("actions", [])[:10]
    if not actions:
        actions = [
            {
                "priority": 1,
                "effort": "medium",
                "impact": "medium",
                "action": "Review title, photos, and attributes against top 10 competitors.",
            }
        ]
    return {"top_10_actions": actions, "constraints": constraints}
