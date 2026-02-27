from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from api.src.utils.measurements import parse_length_to_cm, parse_weight_to_kg


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_field_confidence(found: bool, strong_pattern: bool = False) -> float:
    if not found:
        return 0.0
    return 0.9 if strong_pattern else 0.65


def _extract_warranty_months(text: str) -> float | None:
    m = re.search(r"garanti[a-z]*\s*(?:de)?\s*(\d+)\s*(mes|meses|m[eê]s)", text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))
    y = re.search(r"garanti[a-z]*\s*(?:de)?\s*(\d+)\s*(ano|anos)", text, flags=re.IGNORECASE)
    if y:
        return float(y.group(1)) * 12.0
    return None


def _extract_density(text: str) -> str | None:
    m = re.search(r"(densidade|dens\.)\s*[:\-]?\s*([0-9]{1,3}\s*(?:kg\/m3|kg\/m\^3|d\d{2}|d\s*\d{2}))", text, flags=re.IGNORECASE)
    if m:
        return _to_text(m.group(2)).replace(" ", "")
    return None


def _extract_material(text: str) -> str | None:
    m = re.search(r"(material|revestimento|estrutura)\s*[:\-]\s*([^\n\r;|]{3,80})", text, flags=re.IGNORECASE)
    if m:
        return _to_text(m.group(2))
    return None


def _extract_dimensions(text: str) -> tuple[dict[str, float | None], bool]:
    # L x A x P
    pattern = re.search(
        r"(?:dimens(?:[aã]o|[oõ]es)?|medidas?)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",
        text,
        flags=re.IGNORECASE,
    )
    if pattern:
        u = pattern.group(4) or "cm"
        w = parse_length_to_cm(f"{pattern.group(1)} {u}")
        h = parse_length_to_cm(f"{pattern.group(2)} {u}")
        d = parse_length_to_cm(f"{pattern.group(3)} {u}")
        return {"largura_cm": w, "altura_cm": h, "profundidade_cm": d}, True

    fields = {"largura_cm": None, "altura_cm": None, "profundidade_cm": None}
    lw = re.search(r"(largura|larg\.)\s*[:\-]?\s*([0-9][0-9., ]*(?:mm|cm|m)?)", text, flags=re.IGNORECASE)
    lh = re.search(r"(altura|alt\.)\s*[:\-]?\s*([0-9][0-9., ]*(?:mm|cm|m)?)", text, flags=re.IGNORECASE)
    ld = re.search(r"(profundidade|prof\.)\s*[:\-]?\s*([0-9][0-9., ]*(?:mm|cm|m)?)", text, flags=re.IGNORECASE)
    if lw:
        fields["largura_cm"] = parse_length_to_cm(lw.group(2))
    if lh:
        fields["altura_cm"] = parse_length_to_cm(lh.group(2))
    if ld:
        fields["profundidade_cm"] = parse_length_to_cm(ld.group(2))
    return fields, False


def _extract_weight(text: str) -> tuple[float | None, bool]:
    m = re.search(r"(peso)\s*[:\-]?\s*([0-9][0-9., ]*(?:kg|g)?)", text, flags=re.IGNORECASE)
    if not m:
        return None, False
    return parse_weight_to_kg(m.group(2)), True


def _extract_simple_tables(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t") if p.strip()]
        else:
            parts = re.split(r"\s{2,}", line)
            parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            rows.append({"key": parts[0], "value": parts[1]})
    return rows[:200]


def extract_structured_spec_from_text(text: str) -> Dict[str, Any]:
    norm_text = _to_text(text)
    dims, strong_dims = _extract_dimensions(norm_text)
    weight_kg, strong_weight = _extract_weight(norm_text)
    material = _extract_material(norm_text)
    density = _extract_density(norm_text)
    warranty_months = _extract_warranty_months(norm_text)
    table_rows = _extract_simple_tables(norm_text)

    attributes = {
        "largura_cm": dims.get("largura_cm"),
        "altura_cm": dims.get("altura_cm"),
        "profundidade_cm": dims.get("profundidade_cm"),
        "peso_kg": weight_kg,
        "material": material,
        "densidade": density,
        "garantia_meses": warranty_months,
    }

    confidence = {
        "largura_cm": _norm_field_confidence(attributes["largura_cm"] is not None, strong_dims),
        "altura_cm": _norm_field_confidence(attributes["altura_cm"] is not None, strong_dims),
        "profundidade_cm": _norm_field_confidence(attributes["profundidade_cm"] is not None, strong_dims),
        "peso_kg": _norm_field_confidence(attributes["peso_kg"] is not None, strong_weight),
        "material": _norm_field_confidence(attributes["material"] is not None),
        "densidade": _norm_field_confidence(attributes["densidade"] is not None),
        "garantia_meses": _norm_field_confidence(attributes["garantia_meses"] is not None),
    }

    # Compatível com ListingNormalized.attributes
    listing_attributes = {
        "material": attributes["material"],
        "largura_cm": attributes["largura_cm"],
        "altura_cm": attributes["altura_cm"],
        "profundidade_cm": attributes["profundidade_cm"],
        "peso_kg": attributes["peso_kg"],
        "densidade": attributes["densidade"],
    }

    return {
        "structured_spec": {
            "attributes": attributes,
            "listing_attributes": listing_attributes,
            "table_rows": table_rows,
        },
        "confidence": confidence,
    }


def _category_shot_checklist(category: str) -> list[str]:
    c = _to_text(category).lower()
    if "sofa" in c or "sofá" in c:
        return ["capa_frontal", "lateral", "traseira", "close_tecido", "dimensoes", "ambiente"]
    if "cadeira" in c:
        return ["capa_frontal", "lateral", "traseira", "assento", "detalhe_material", "dimensoes"]
    if "banqueta" in c:
        return ["capa_frontal", "lateral", "base", "assento", "detalhe_material", "dimensoes"]
    return ["capa_frontal", "lateral", "detalhe_material", "dimensoes", "ambiente"]


def _infer_shot_tags(url: str) -> list[str]:
    p = urlparse(url)
    text = f"{p.path} {p.query}".lower()
    tags: list[str] = []
    mapping = {
        "capa_frontal": ["front", "frontal", "cover", "hero"],
        "lateral": ["side", "lateral"],
        "traseira": ["back", "traseira", "rear"],
        "close_tecido": ["close", "zoom", "tecido", "fabric"],
        "assento": ["seat", "assento"],
        "base": ["base", "foot", "pe", "pé"],
        "dimensoes": ["dimens", "medida", "size", "measure"],
        "ambiente": ["room", "ambiente", "decor", "lifestyle"],
        "detalhe_material": ["material", "detail", "detalhe", "texture"],
    }
    for tag, keys in mapping.items():
        if any(k in text for k in keys):
            tags.append(tag)
    return tags


def _quality_issues_for_url(url: str) -> list[str]:
    issues: list[str] = []
    low_res = re.search(r"(320x|480x|640x|_small|thumb|thumbnail)", url.lower())
    if low_res:
        issues.append("possible_low_resolution")
    if "watermark" in url.lower() or "logo" in url.lower():
        issues.append("possible_overlay_or_watermark")
    if not url.startswith("http"):
        issues.append("invalid_or_non_http_url")
    return issues


def analyze_image_set(image_urls: List[str], category: str | None = None) -> Dict[str, Any]:
    urls = [u for u in image_urls if _to_text(u)]
    checklist = _category_shot_checklist(category or "")
    detected_tags: list[str] = []
    quality_issues: list[str] = []
    per_image: list[dict[str, Any]] = []

    for url in urls:
        tags = _infer_shot_tags(url)
        detected_tags.extend(tags)
        issues = _quality_issues_for_url(url)
        quality_issues.extend(issues)
        per_image.append({"url": url, "tags": tags, "issues": issues})

    missing = [shot for shot in checklist if shot not in detected_tags]
    coverage = 1.0 - (len(missing) / max(len(checklist), 1))
    cover_strength_score = round(max(0.0, min(1.0, coverage)) * 100, 1)

    angle_tags = {"capa_frontal", "lateral", "traseira", "base"}
    unique_angle_count = len({tag for tag in detected_tags if tag in angle_tags})
    angle_variety_score = round((unique_angle_count / max(len(angle_tags), 1)) * 100, 1)

    # penaliza score se houver issues de qualidade recorrentes
    issue_counter = Counter(quality_issues)
    recurring_penalty = sum(5 for _, cnt in issue_counter.items() if cnt >= 2)
    cover_strength_score = max(0.0, cover_strength_score - recurring_penalty)

    return {
        "missing_shots": missing,
        "quality_issues": sorted(dict.fromkeys(quality_issues)),
        "cover_strength_score": cover_strength_score,
        "angle_variety_score": angle_variety_score,
        "checklist": checklist,
        "items": per_image,
    }
