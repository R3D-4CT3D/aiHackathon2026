"""
Layer 2: LLM reasoning engine.
Uses OpenAI when an API key is available; falls back to a smart mock
driven by heuristic scores so the demo never breaks.
"""
from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
    _OPENAI_IMPORTABLE = True
except ImportError:
    _OPENAI_IMPORTABLE = False

from normalizer import normalize_label

# ---------------------------------------------------------------------------
# Prompt contract
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI Cyber Safety Coach helping everyday people understand whether an email or message is safe.

Analyze the provided message and return a JSON object with EXACTLY this structure:
{
  "label": "Safe" | "Needs Review" | "Likely Phishing",
  "confidence": "low" | "medium" | "high",
  "top_reasons": ["reason 1", "reason 2", "reason 3"],
  "recommended_actions": ["action 1", "action 2", "action 3", "action 4"],
  "technical_signals": {
    "urgency": true/false,
    "credential_request": true/false,
    "domain_mismatch": true/false,
    "shortened_link": true/false
  }
}

Rules:
- Use ONLY these three exact labels: Safe, Needs Review, Likely Phishing
- Write top_reasons in plain, friendly language a non-technical person can understand (max 20 words each)
- Write recommended_actions as clear, concrete next steps (max 15 words each)
- Never use jargon without a plain-language explanation
- If genuinely unsure, prefer "Needs Review" over a definitive label
- For Safe emails, keep the tone calm — do not over-alarm
- For Likely Phishing, be direct and protective
- Return ONLY the JSON object, no additional text or markdown
"""

_USER_TEMPLATE = """Analyze this message:

Subject: {subject}
From: {sender_name} <{sender_email}>

{body}

{url_section}
Heuristic pre-scan:
{heuristic_summary}
"""


def _heuristic_summary(h: dict) -> str:
    signals = []
    if h.get("urgency"):
        signals.append("- Urgency language detected")
    if h.get("credential_request"):
        signals.append("- Credential or verification request detected")
    if h.get("payment_pressure"):
        signals.append("- Payment-related pressure language detected")
    if h.get("brand_impersonation"):
        signals.append("- Possible impersonation of a known brand")
    if h.get("suspicious_domain"):
        signals.append("- Suspicious sender domain pattern")
    if h.get("shortened_url"):
        signals.append("- URL shortener detected")
    if h.get("sender_mismatch"):
        signals.append("- Sender name does not match the email domain")
    return "\n".join(signals) if signals else "- No obvious signals detected"


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _call_openai(
    body: str,
    sender_name: str,
    sender_email: str,
    subject: str,
    urls: list[str],
    heuristics: dict,
    api_key: str,
) -> dict:
    client = OpenAI(api_key=api_key)
    url_section = (
        "URLs found in message:\n" + "\n".join(f"- {u}" for u in urls)
        if urls
        else ""
    )
    prompt = _USER_TEMPLATE.format(
        subject=subject or "(no subject)",
        sender_name=sender_name or "Unknown",
        sender_email=sender_email or "unknown@unknown.com",
        body=body[:3000],
        url_section=url_section,
        heuristic_summary=_heuristic_summary(heuristics),
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=800,
    )
    raw: dict[str, Any] = json.loads(response.choices[0].message.content)
    raw["label"] = normalize_label(raw.get("label", ""))
    raw["_source"] = "openai"
    return raw


# ---------------------------------------------------------------------------
# Smart mock (heuristic-driven, no API key required)
# ---------------------------------------------------------------------------

_MOCK_RESPONSES: dict[str, dict] = {
    "Likely Phishing": {
        "label": "Likely Phishing",
        "confidence": "high",
        "top_reasons": [
            "Multiple strong warning signs were found in this message.",
            "It pushes you to act quickly or share sensitive information.",
            "The sender address does not match a trustworthy source.",
        ],
        "recommended_actions": [
            "Do not click any links in this message.",
            "Do not enter any personal or financial information.",
            "Report this email to your IT department or email provider.",
            "If you already clicked a link, change your passwords immediately.",
        ],
        "technical_signals": {
            "urgency": True,
            "credential_request": True,
            "domain_mismatch": True,
            "shortened_link": False,
        },
    },
    "Needs Review": {
        "label": "Needs Review",
        "confidence": "medium",
        "top_reasons": [
            "This message has some characteristics worth a closer look.",
            "It may be legitimate, but it asks you to click a link or confirm details.",
            "When in doubt, contact the sender through a channel you already trust.",
        ],
        "recommended_actions": [
            "Do not click any links until you verify the sender.",
            "Look up the organization's official website directly.",
            "Contact the sender through a trusted phone number or email you know.",
            "Check whether you were expecting this kind of message.",
        ],
        "technical_signals": {
            "urgency": False,
            "credential_request": True,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
    "Safe": {
        "label": "Safe",
        "confidence": "medium",
        "top_reasons": [
            "No warning signs were detected in this message.",
            "The tone is routine and does not push you to act urgently.",
            "No requests for sensitive information or unusual links were found.",
        ],
        "recommended_actions": [
            "No immediate action is required.",
            "You can respond or follow the instructions as normal.",
            "Stay alert to follow-up messages asking for personal details.",
        ],
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
}


def _mock_response(heuristics: dict, error: str = "") -> dict:
    score = heuristics.get("score", 0)
    if score >= 5:
        label = "Likely Phishing"
    elif score >= 2:
        label = "Needs Review"
    else:
        label = "Safe"

    result = dict(_MOCK_RESPONSES[label])
    result["technical_signals"] = {
        "urgency": heuristics.get("urgency", False),
        "credential_request": heuristics.get("credential_request", False),
        "domain_mismatch": heuristics.get("suspicious_domain", False),
        "shortened_link": heuristics.get("shortened_url", False),
    }
    result["_source"] = "mock" if not error else f"mock (error: {error[:80]})"
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_with_llm(
    body: str,
    sender_name: str = "",
    sender_email: str = "",
    subject: str = "",
    urls: list[str] | None = None,
    heuristics: dict | None = None,
    api_key: str = "",
) -> dict:
    h = heuristics or {}
    key = api_key or os.getenv("OPENAI_API_KEY", "")

    if _OPENAI_IMPORTABLE and key:
        try:
            return _call_openai(
                body=body,
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                urls=urls or [],
                heuristics=h,
                api_key=key,
            )
        except Exception as exc:  # noqa: BLE001
            return _mock_response(h, error=str(exc))

    return _mock_response(h)
