"""
Lightweight TF-IDF + Logistic Regression email classifier.
Trained by train_classifier.py — loads model.joblib and vectorizer.joblib at startup.

Public API:
    classify_email(text: str) -> dict | None
        Returns {"verdict": str, "probability": float, "reason": str}
        or None if the model is not available.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy model loading — only once, at first call
# ---------------------------------------------------------------------------

_MODEL = None
_VEC   = None
_READY = False
_ERROR = ""

_MODEL_DIR = Path(__file__).parent

LABELS = ["Safe", "Needs Review", "Likely Phishing"]

_REASONS: dict[str, str] = {
    "Likely Phishing": (
        "The wording and structure of this message closely match known phishing patterns."
    ),
    "Needs Review": (
        "Some language patterns in this message are worth a closer look before acting."
    ),
    "Safe": "",  # supporting-signal only — suppress for Safe
}

# Two-tier thresholds:
#   _SCORE_THRESHOLD — minimum probability to contribute to the heuristic score
#                      (silent internal signal, more sensitive)
#   _UI_THRESHOLD    — minimum probability to show the "Pattern analysis" note
#                      (visible to user, more conservative)
_SCORE_THRESHOLD = 0.38
_UI_THRESHOLD    = 0.50


def _load() -> None:
    global _MODEL, _VEC, _READY, _ERROR
    try:
        import joblib  # noqa: PLC0415
        model_path = _MODEL_DIR / "model.joblib"
        vec_path   = _MODEL_DIR / "vectorizer.joblib"
        if not model_path.exists() or not vec_path.exists():
            _ERROR = "model files not found — run train_classifier.py"
            return
        _MODEL = joblib.load(str(model_path))
        _VEC   = joblib.load(str(vec_path))
        _READY = True
    except Exception as exc:  # noqa: BLE001
        _ERROR = str(exc)[:120]


def classify_email(text: str) -> Optional[dict]:
    """
    Classify an email body and return a supporting signal dict.

    Returns:
        {
            "verdict":     "Safe" | "Needs Review" | "Likely Phishing",
            "probability": float (0–1),
            "reason":      str   (human-readable, empty for Safe),
        }
        or None if the model is unavailable or confidence is below threshold.
    """
    global _READY
    if not _READY:
        _load()
    if not _READY:
        return None

    try:
        X = _VEC.transform([text])
        proba = _MODEL.predict_proba(X)[0]
        pred_idx = int(proba.argmax())
        prob = float(proba[pred_idx])
        verdict = LABELS[pred_idx]

        if prob < _SCORE_THRESHOLD:
            return None  # too uncertain to use even as a silent signal

        # reason is empty when below UI threshold or for Safe verdicts —
        # ml_note_html() will produce no output in both cases
        reason = _REASONS[verdict] if prob >= _UI_THRESHOLD else ""

        return {
            "verdict":     verdict,
            "probability": prob,
            "reason":      reason,
        }
    except Exception:  # noqa: BLE001
        return None


def is_available() -> bool:
    """Return True if the model is loaded and ready."""
    if not _READY:
        _load()
    return _READY
