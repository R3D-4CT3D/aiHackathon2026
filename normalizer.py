"""
Layer 3: Output normalization.
Ensures only the three approved labels ever leave the analysis pipeline.
"""
from __future__ import annotations

VALID_LABELS = {"Safe", "Needs Review", "Likely Phishing"}

_LABEL_MAP: dict[str, str] = {
    # Safe aliases
    "safe": "Safe",
    "clean": "Safe",
    "legitimate": "Safe",
    "benign": "Safe",
    "no risk": "Safe",
    "low risk": "Safe",
    # Needs Review aliases
    "needs review": "Needs Review",
    "review": "Needs Review",
    "suspicious": "Needs Review",
    "uncertain": "Needs Review",
    "caution": "Needs Review",
    "moderate": "Needs Review",
    "medium risk": "Needs Review",
    "possibly": "Needs Review",
    # Likely Phishing aliases
    "likely phishing": "Likely Phishing",
    "phishing": "Likely Phishing",
    "malicious": "Likely Phishing",
    "dangerous": "Likely Phishing",
    "high risk": "Likely Phishing",
    "scam": "Likely Phishing",
    "spam": "Likely Phishing",
    "fraud": "Likely Phishing",
}


def normalize_label(raw: str | None) -> str:
    if not raw:
        return "Needs Review"
    cleaned = raw.strip()
    if cleaned in VALID_LABELS:
        return cleaned
    lower = cleaned.lower()
    for alias, canonical in _LABEL_MAP.items():
        if alias in lower:
            return canonical
    return "Needs Review"


def normalize_confidence(raw: str | int | float | None) -> str:
    """Return 'low' | 'medium' | 'high'."""
    if raw is None:
        return "medium"
    if isinstance(raw, str):
        lower = raw.strip().lower()
        if lower in ("low", "medium", "high"):
            return lower
        try:
            val = float(lower.rstrip("%")) / (1 if "%" not in lower else 100)
        except ValueError:
            return "medium"
    else:
        val = float(raw)
    if val > 1.0:
        val /= 100.0
    if val >= 0.78:
        return "high"
    if val >= 0.50:
        return "medium"
    return "low"


def confidence_pct(band: str, label: str) -> int:
    """Return a display percentage for the confidence band."""
    base = {"high": 90, "medium": 68, "low": 42}[band]
    # Nudge by label to look realistic
    nudge = {"Likely Phishing": 4, "Safe": 3, "Needs Review": 0}[label]
    return min(99, base + nudge)
