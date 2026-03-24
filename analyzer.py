"""
Analysis orchestrator.
Combines heuristics → VT enrichment → LLM → normalization into a single callable.
"""
from __future__ import annotations

import os

from heuristics import run_heuristics
from llm_client import analyze_with_llm
from ml_classifier import classify_email as ml_classify
from normalizer import normalize_label, normalize_confidence, confidence_pct
from url_reputation import check_reputation


def analyze_message(
    body: str,
    sender_name: str = "",
    sender_email: str = "",
    subject: str = "",
    openai_api_key: str = "",
    vt_api_key: str = "",
    gsb_api_key: str = "",
    urlscan_api_key: str = "",
    # legacy kwarg kept for backwards compat
    api_key: str = "",
) -> dict:
    """
    Full analysis pipeline.

    Layer 1 — ML classifier (TF-IDF + LR, supporting signal only)
    Layer 2 — deterministic heuristics (ML score folded in here)
    Layer 3 — URL reputation enrichment (VirusTotal + Google Safe Browsing + URLScan)
    Layer 4 — LLM reasoning (or smart mock)
    Layer 5 — output normalization (enforce 3 approved labels)

    Returns a normalized dict with:
      label               : "Safe" | "Needs Review" | "Likely Phishing"
      confidence_band     : "low" | "medium" | "high"
      confidence_pct      : int (display percentage)
      top_reasons         : list[str] (exactly 3)
      recommended_actions : list[str] (3–5)
      technical_signals   : dict
      heuristic_signals   : dict
      virustotal          : dict  (VTResult for backward-compat UI card)
      reputation          : dict  (multi-source normalized result)
    """
    # Resolve API keys (argument → env fallback)
    llm_key     = openai_api_key or api_key or os.getenv("OPENAI_API_KEY", "")
    vt_key      = vt_api_key      or os.getenv("VIRUSTOTAL_API_KEY", "")
    gsb_key     = gsb_api_key     or os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    us_key      = urlscan_api_key or os.getenv("URLSCAN_API_KEY", "")

    # ── Layer 1: heuristics ──────────────────────────────────────────────
    full_text = f"{subject}\n{sender_name}\n{body}"
    ml_signal = ml_classify(full_text)

    heuristics = run_heuristics(
        body_text=body,
        sender_name=sender_name,
        sender_email=sender_email,
        subject=subject,
    )
    h_dict = heuristics.to_dict()

    # ── Layer 2: multi-source URL reputation ─────────────────────────────
    rep_result = check_reputation(
        heuristics.extracted_urls,
        vt_key=vt_key,
        gsb_key=gsb_key,
        urlscan_key=us_key,
    )

    # Fold ML signal into heuristic score so LLM sees it
    if ml_signal:
        ml_verdict = ml_signal["verdict"]
        if ml_verdict == "Likely Phishing":
            h_dict["score"] = h_dict.get("score", 0) + 2
        elif ml_verdict == "Needs Review":
            h_dict["score"] = h_dict.get("score", 0) + 1

    # Fold reputation signal into heuristic score so LLM sees it
    if rep_result.any_malicious:
        h_dict["vt_malicious_url"] = True
        h_dict["score"] += 4          # strong boost for confirmed malicious URL
    elif rep_result.any_suspicious:
        h_dict["vt_suspicious_url"] = True
        h_dict["score"] += 2

    # ── Layer 3: LLM reasoning (or smart mock) ───────────────────────────
    # Append reputation summary as extra context so the LLM can reference it
    enriched_body = body
    if rep_result.checked and rep_result.urls:
        rep_lines = [f"URL reputation check: {rep_result.summary}"]
        for u in rep_result.urls:
            if u.sources:
                srcs = ", ".join(u.sources)
                rep_lines.append(f"  {u.url[:80]} → {u.verdict} (checked by {srcs})")
                for flag in u.flags:
                    rep_lines.append(f"    • {flag}")
        enriched_body = body + "\n\n" + "\n".join(rep_lines)

    result = analyze_with_llm(
        body=enriched_body,
        sender_name=sender_name,
        sender_email=sender_email,
        subject=subject,
        urls=heuristics.extracted_urls,
        heuristics=h_dict,
        api_key=llm_key,
    )

    # ── Layer 4: normalization ────────────────────────────────────────────
    label = normalize_label(result.get("label", ""))
    # Confirmed malicious URL — never downgrade below Needs Review
    if rep_result.any_malicious and label == "Safe":
        label = "Needs Review"

    result["label"] = label
    band = normalize_confidence(result.get("confidence", "medium"))
    result["confidence_band"] = band
    result["confidence_pct"] = confidence_pct(band, label)

    # Ensure exactly 3 reasons
    reasons = result.get("top_reasons") or []
    while len(reasons) < 3:
        reasons.append("No additional signals detected.")
    result["top_reasons"] = reasons[:3]

    # Ensure 3–5 recommended actions
    actions = result.get("recommended_actions") or []
    while len(actions) < 3:
        actions.append("Review this message carefully before acting.")
    result["recommended_actions"] = actions[:5]

    # Attach signals for the UI
    result["heuristic_signals"] = h_dict
    result["ml_signal"]         = ml_signal            # classifier supporting signal
    result["virustotal"]        = rep_result.vt_raw   # backward-compat VT card
    result["reputation"]        = rep_result.to_dict() # full multi-source result

    return result
