"""
Layer 1: Deterministic phishing-feature extractor.
Runs fast regex and keyword checks before the LLM sees the message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Signal word lists
# ---------------------------------------------------------------------------

URGENCY_PHRASES = [
    "act immediately", "act now", "action required", "action needed",
    "expires today", "expire soon", "immediate action", "immediately",
    "last chance", "limited time", "must act", "time sensitive",
    "urgent", "urgency", "verify now", "verify today",
    "within 24 hours", "within 2 hours", "within 48 hours",
    "within 15 minutes", "within 10 minutes", "within 30 minutes",
    "account will be", "will be terminated", "suspended", "on hold",
    "closing soon", "final notice", "deadline", "failure to act",
    "will be locked", "will be closed", "your account",
]

CREDENTIAL_PHRASES = [
    "verify your", "confirm your", "update your", "re-enter",
    "provide your", "enter your password", "enter your account",
    "banking details", "credit card", "social security", "ssn",
    "login credentials", "username and password", "sign in to verify",
    "validate your account", "confirm identity", "confirm your details",
    "update your information", "confirm your address",
    "reset your password", "reset password", "your password",
    "account credentials", "your credentials",
]

PAYMENT_PHRASES = [
    "gift card", "wire transfer", "bitcoin", "cryptocurrency",
    "payment required", "send money", "pay now", "invoice attached",
    "payment is pending", "pending payment", "bank account",
    "direct deposit", "paycheck", "payroll",
    "billing information", "payment method",
]

KNOWN_BRAND_DOMAINS: dict[str, str] = {
    "paypal": "paypal.com",
    "amazon": "amazon.com",
    "apple": "apple.com",
    "microsoft": "microsoft.com",
    "google": "google.com",
    "docusign": "docusign.com",
    "fedex": "fedex.com",
    "ups": "ups.com",
    "usps": "usps.com",
    "netflix": "netflix.com",
    "chase": "chase.com",
    "bank of america": "bankofamerica.com",
    "wells fargo": "wellsfargo.com",
    "irs": "irs.gov",
}

SUSPICIOUS_TLDS = {
    ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top",
    ".click", ".work", ".loan", ".help", ".support", ".info",
}

SUSPICIOUS_DOMAIN_KEYWORDS = {
    "secure", "verify", "update", "login",
    "payroll", "confirm", "helpdesk",
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "short.to", "buff.ly", "rebrand.ly", "rb.gy",
}

URL_RE = re.compile(r"https?://[^\s<>\"'{}|\\^`\[\]]+")
EMAIL_DOMAIN_RE = re.compile(r"@([\w.\-]+)")

# Matches bare domains with suspicious TLDs that have no protocol prefix.
# e.g. "company-payroll.help/verify-now" or "reset.corp-helpdesk.info"
# Negative lookbehind avoids re-matching already-captured https:// URLs.
_BARE_DOMAIN_RE = re.compile(
    r"(?<![:/\w])([\w][\w\-]*\.(?:tk|ml|ga|cf|gq|xyz|top|click|work|loan|help|support|info)"
    r"(?:/[^\s<>\"'{}|\\^`\[\]]*)?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HeuristicResult:
    urgency: bool = False
    credential_request: bool = False
    payment_pressure: bool = False
    brand_impersonation: bool = False
    suspicious_domain: bool = False
    shortened_url: bool = False
    sender_mismatch: bool = False
    matched_phrases: list[str] = field(default_factory=list)
    extracted_urls: list[str] = field(default_factory=list)
    score: int = 0

    def to_dict(self) -> dict:
        return {
            "urgency": self.urgency,
            "credential_request": self.credential_request,
            "payment_pressure": self.payment_pressure,
            "brand_impersonation": self.brand_impersonation,
            "suspicious_domain": self.suspicious_domain,
            "shortened_url": self.shortened_url,
            "sender_mismatch": self.sender_mismatch,
            "score": self.score,
            "matched_phrases": self.matched_phrases,
            "extracted_urls": self.extracted_urls,
        }


# ---------------------------------------------------------------------------
# Checkers
# ---------------------------------------------------------------------------

def _check(text_lower: str, phrases: list[str]) -> tuple[bool, list[str]]:
    found = [p for p in phrases if p in text_lower]
    return bool(found), found


def _check_domain(sender_email: str, urls: list[str]) -> bool:
    combined = (sender_email + " " + " ".join(urls)).lower()
    for tld in SUSPICIOUS_TLDS:
        if tld in combined:
            return True
    m = EMAIL_DOMAIN_RE.search(combined)
    if m:
        domain = m.group(1)
        for kw in SUSPICIOUS_DOMAIN_KEYWORDS:
            if kw in domain:
                return True
    return False


def _check_shortened(urls: list[str]) -> bool:
    for url in urls:
        for shortener in URL_SHORTENERS:
            if shortener in url:
                return True
    return False


def _check_sender_mismatch(sender_name: str, sender_email: str) -> bool:
    name_lower = sender_name.lower()
    email_lower = sender_email.lower()
    for brand, domain in KNOWN_BRAND_DOMAINS.items():
        if brand in name_lower and domain not in email_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_heuristics(
    body_text: str,
    sender_name: str = "",
    sender_email: str = "",
    subject: str = "",
) -> HeuristicResult:
    full_text = f"{subject} {body_text}".strip()
    text_lower = full_text.lower()

    result = HeuristicResult()
    result.extracted_urls = URL_RE.findall(full_text)

    # Also pick up bare suspicious-TLD domains (no https:// prefix).
    # Strip already-captured full URLs first so the regex doesn't re-match
    # substrings inside them (e.g. "payroll.help" inside "https://company-payroll.help/...").
    text_without_urls = URL_RE.sub(" ", full_text)
    seen = set(result.extracted_urls)
    for bare in _BARE_DOMAIN_RE.findall(text_without_urls):
        # Strip trailing punctuation that the greedy match may have absorbed
        bare = bare.rstrip(".,;:)")
        normalized = "https://" + bare
        if normalized not in seen:
            result.extracted_urls.append(normalized)
            seen.add(normalized)

    # Urgency
    hit, phrases = _check(text_lower, URGENCY_PHRASES)
    result.urgency = hit
    result.matched_phrases.extend(phrases[:2])

    # Credential request
    hit, phrases = _check(text_lower, CREDENTIAL_PHRASES)
    result.credential_request = hit
    result.matched_phrases.extend(phrases[:2])

    # Payment pressure
    hit, phrases = _check(text_lower, PAYMENT_PHRASES)
    result.payment_pressure = hit
    result.matched_phrases.extend(phrases[:2])

    # Brand impersonation (name in body vs known domain)
    text_plus_sender = text_lower + " " + sender_name.lower()
    result.brand_impersonation = any(brand in text_plus_sender for brand in KNOWN_BRAND_DOMAINS)

    # Domain/URL checks
    result.suspicious_domain = _check_domain(sender_email, result.extracted_urls)
    result.shortened_url = _check_shortened(result.extracted_urls)
    result.sender_mismatch = _check_sender_mismatch(sender_name, sender_email)

    # Weighted score
    result.score = sum([
        result.urgency * 2,
        result.credential_request * 3,
        result.payment_pressure * 2,
        result.brand_impersonation * 1,
        result.suspicious_domain * 2,
        result.shortened_url * 1,
        result.sender_mismatch * 3,
    ])

    return result
