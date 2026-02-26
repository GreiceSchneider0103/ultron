from __future__ import annotations


def generate_audit_report(scores: dict, recommendations: list, metadata: dict) -> dict:
    """Stub de relatório de auditoria."""
    return {
        "type": "audit_report",
        "scores": scores,
        "recommendations": recommendations,
        "metadata": metadata,
    }
