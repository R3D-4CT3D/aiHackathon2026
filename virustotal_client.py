"""
Layer 2b: VirusTotal URL enrichment.
Looks up each URL extracted from a message and returns engine vote counts.
Degrades gracefully — analysis continues even if VT is unavailable or times out.
"""
from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

VT_BASE = "https://www.virustotal.com/api/v3"
_DEFAULT_TIMEOUT = 8  # seconds per request


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class URLReport:
    url: str
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    total: int = 0
    reputation: int = 0
    last_analysis_date: str = ""
    categories: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def verdict(self) -> str:
        """Human-readable one-word verdict based on vote counts."""
        if self.error:
            return "unavailable"
        if self.malicious >= 3:
            return "malicious"
        if self.malicious >= 1 or self.suspicious >= 2:
            return "suspicious"
        if self.harmless > 0:
            return "clean"
        return "unknown"

    @property
    def flag_count(self) -> str:
        if self.error or self.total == 0:
            return "—"
        return f"{self.malicious + self.suspicious}/{self.total} engines"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "malicious": self.malicious,
            "suspicious": self.suspicious,
            "harmless": self.harmless,
            "undetected": self.undetected,
            "total": self.total,
            "reputation": self.reputation,
            "last_analysis_date": self.last_analysis_date,
            "categories": self.categories,
            "verdict": self.verdict,
            "flag_count": self.flag_count,
            "error": self.error,
        }


@dataclass
class VTResult:
    urls_checked: list[URLReport] = field(default_factory=list)
    any_malicious: bool = False
    any_suspicious: bool = False
    summary: str = ""
    available: bool = True

    def to_dict(self) -> dict:
        return {
            "urls_checked": [r.to_dict() for r in self.urls_checked],
            "any_malicious": self.any_malicious,
            "any_suspicious": self.any_suspicious,
            "summary": self.summary,
            "available": self.available,
        }


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _url_id(url: str) -> str:
    """VirusTotal URL identifier: base64url-encoded URL without padding."""
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _headers(api_key: str) -> dict:
    return {"x-apikey": api_key, "Accept": "application/json"}


def _get_report(url: str, api_key: str) -> URLReport:
    """Fetch an existing VT URL report. Submit if not found, then fetch."""
    report = URLReport(url=url)
    uid = _url_id(url)

    try:
        resp = requests.get(
            f"{VT_BASE}/urls/{uid}",
            headers=_headers(api_key),
            timeout=_DEFAULT_TIMEOUT,
        )

        if resp.status_code == 404:
            # URL not yet in VT — submit it for analysis
            submit = requests.post(
                f"{VT_BASE}/urls",
                headers=_headers(api_key),
                data={"url": url},
                timeout=_DEFAULT_TIMEOUT,
            )
            if submit.status_code not in (200, 201):
                report.error = f"submit failed ({submit.status_code})"
                return report

            # Brief pause then fetch (analysis is usually instant for known domains)
            time.sleep(2)
            resp = requests.get(
                f"{VT_BASE}/urls/{uid}",
                headers=_headers(api_key),
                timeout=_DEFAULT_TIMEOUT,
            )

        if resp.status_code != 200:
            report.error = f"HTTP {resp.status_code}"
            return report

        data = resp.json().get("data", {}).get("attributes", {})
        stats = data.get("last_analysis_stats", {})
        report.malicious = stats.get("malicious", 0)
        report.suspicious = stats.get("suspicious", 0)
        report.harmless = stats.get("harmless", 0)
        report.undetected = stats.get("undetected", 0)
        report.total = (
            report.malicious + report.suspicious + report.harmless + report.undetected
        )
        report.reputation = data.get("reputation", 0)

        # Convert epoch timestamp
        ts = data.get("last_analysis_date")
        if ts:
            import datetime
            dt = datetime.datetime.utcfromtimestamp(ts)
            report.last_analysis_date = dt.strftime("%Y-%m-%d")

        # Categories (e.g. "phishing", "malware")
        raw_cats = data.get("categories", {})
        report.categories = list(set(raw_cats.values()))[:5]

    except requests.exceptions.Timeout:
        report.error = "timeout"
    except requests.exceptions.ConnectionError:
        report.error = "connection error"
    except Exception as exc:  # noqa: BLE001
        report.error = str(exc)[:80]

    return report


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_urls(
    urls: list[str],
    api_key: str = "",
    max_urls: int = 3,
) -> VTResult:
    """
    Check up to `max_urls` URLs against VirusTotal.
    Always returns a VTResult — errors are captured per-URL, not raised.
    """
    result = VTResult()
    key = api_key or os.getenv("VIRUSTOTAL_API_KEY", "")

    if not key:
        result.available = False
        result.summary = "VirusTotal not configured."
        return result

    if not urls:
        result.summary = "No URLs found in this message."
        return result

    for url in urls[:max_urls]:
        report = _get_report(url, key)
        result.urls_checked.append(report)
        if not report.error:
            if report.malicious >= 1:
                result.any_malicious = True
            if report.suspicious >= 1:
                result.any_suspicious = True

    # Build summary sentence
    checked = [r for r in result.urls_checked if not r.error]
    errored = [r for r in result.urls_checked if r.error]

    link_word = "link" if len(errored) == 1 else "links"
    if not checked and errored:
        result.summary = f"VirusTotal check failed for {len(errored)} {link_word}."
    elif result.any_malicious:
        mal_count = sum(r.malicious for r in checked)
        engine_word = "engine" if mal_count == 1 else "engines"
        result.summary = f"{mal_count} {engine_word} flagged a link in this message as unsafe."
    elif result.any_suspicious:
        result.summary = "One or more links were flagged as suspicious."
    elif checked:
        n = len(checked)
        result.summary = f"{n} {'link' if n == 1 else 'links'} checked — no threats found."
    else:
        result.summary = "VirusTotal returned no results."

    return result
