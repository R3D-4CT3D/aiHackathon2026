"""
url_reputation.py — Multi-source URL reputation enrichment.

Sources (all run in parallel; each skipped gracefully if key is absent)
-----------------------------------------------------------------------
  VirusTotal (v3)       — engine vote counts        (via virustotal_client.py)
  Google Safe Browsing  — Google real-time threat classification
  URLScan.io            — passive domain search      (no submission / no async wait)

Keys are read from environment variables:
  VIRUSTOTAL_API_KEY
  GOOGLE_SAFE_BROWSING_API_KEY
  URLSCAN_API_KEY   (optional — key grants higher rate limits only)

Per-source verdict states
-------------------------
  flagged    — source actively found a threat
  clean      — source responded and found nothing
  no_opinion — source was not configured (missing key) or had no data for this URL
  error      — source was configured but the request failed

Aggregation rule (per URL, applied after all sources complete)
---------------------------------------------
  any flagged                         → malicious or suspicious
  no flagged, at least one clean      → clean   (Safe)
  no flagged, no clean (all no_opinion/error) → unverified  (Needs Review)

Overall verdict across all URLs: worst per-URL verdict.
"""
from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import requests

from virustotal_client import check_urls as _vt_check_urls, VTResult

_log = logging.getLogger(__name__)

_TIMEOUT = 8  # seconds per request

_GSB_THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]

_GSB_LABELS: dict[str, str] = {
    "MALWARE":                         "malware",
    "SOCIAL_ENGINEERING":              "phishing / social engineering",
    "UNWANTED_SOFTWARE":               "unwanted software",
    "POTENTIALLY_HARMFUL_APPLICATION": "potentially harmful app",
}

# Trailing characters that are never part of a URL (sentence punctuation)
_TRAILING_PUNCT = re.compile(r"[.,;:!?)\]>\"']+$")

# Verdict rank — used only to pick the worst verdict when sources disagree on severity.
# "unverified" is intentionally absent: the aggregation logic derives it explicitly
# rather than computing it as a rank.
_FLAG_RANK = {"malicious": 2, "suspicious": 1}


def _clean_url(url: str) -> str:
    """Strip trailing sentence punctuation that regex may have captured."""
    return _TRAILING_PUNCT.sub("", url.strip())


# ── Per-URL result ─────────────────────────────────────────────────────────

@dataclass
class URLReputation:
    url: str
    verdict: str = "unverified"                       # malicious | suspicious | clean | unverified
    sources: list[str] = field(default_factory=list)  # services that returned a real verdict
    flags: list[str] = field(default_factory=list)    # human-readable findings
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "url":     self.url,
            "verdict": self.verdict,
            "sources": self.sources,
            "flags":   self.flags,
            "summary": self.summary,
        }


# ── Aggregate result ───────────────────────────────────────────────────────

@dataclass
class ReputationResult:
    urls: list[URLReputation] = field(default_factory=list)
    overall_verdict: str = "unverified"
    any_malicious:   bool = False
    any_suspicious:  bool = False
    summary: str = ""
    checked: bool = False
    services_used: list[str] = field(default_factory=list)
    vt_raw: Optional[dict] = None  # VTResult.to_dict() — kept for backward-compat UI card

    def to_dict(self) -> dict:
        return {
            "urls":            [u.to_dict() for u in self.urls],
            "overall_verdict": self.overall_verdict,
            "any_malicious":   self.any_malicious,
            "any_suspicious":  self.any_suspicious,
            "summary":         self.summary,
            "checked":         self.checked,
            "services_used":   self.services_used,
        }


# ── Source checkers ────────────────────────────────────────────────────────

def _run_vt(urls: list[str], api_key: str) -> VTResult:
    """VirusTotal check. Returns a VTResult (available=False if no key)."""
    return _vt_check_urls(urls, api_key=api_key)


@dataclass
class _GSBResult:
    """Internal result from a Google Safe Browsing lookup."""
    key_present:  bool
    request_made: bool
    http_status:  Optional[int]
    raw_body:     str                         # first 500 chars for debug
    threats:      dict[str, list[str]]        # url → [threat_type] for flagged URLs
    reached:      bool                        # True = HTTP 200 received


def _run_gsb(urls: list[str], api_key: str) -> _GSBResult:
    """
    Google Safe Browsing v4 lookup.

    State mapping:
      key missing                → no_opinion  (reached=False, key_present=False)
      HTTP 200 + empty body      → clean       (reached=True, threats={})
      HTTP 200 + matches         → flagged     (reached=True, threats={url: [...]})
      HTTP error / timeout / exc → error       (reached=False, key_present=True)
    """
    base = _GSBResult(
        key_present=bool(api_key),
        request_made=False,
        http_status=None,
        raw_body="",
        threats={},
        reached=False,
    )

    _log.debug("GSB | key_present=%s", base.key_present)

    if not api_key or not urls:
        _log.debug("GSB | skipped (no key or no urls)")
        return base

    endpoint = (
        "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        f"?key={api_key}"
    )
    payload = {
        "client": {"clientId": "luman-claude", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes":      _GSB_THREAT_TYPES,
            "platformTypes":    ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries":    [{"url": u} for u in urls],
        },
    }

    try:
        base.request_made = True
        _log.debug("GSB | request_made=True, urls=%s", urls)

        resp = requests.post(endpoint, json=payload, timeout=_TIMEOUT)
        base.http_status = resp.status_code
        base.raw_body = resp.text[:500]

        _log.debug("GSB | http_status=%s", base.http_status)
        _log.debug("GSB | raw_body=%s", base.raw_body)

        if resp.status_code != 200:
            _log.debug("GSB | verdict=error (non-200)")
            return base  # reached stays False → error state

        base.reached = True
        for m in resp.json().get("matches", []):
            url = m.get("threat", {}).get("url", "")
            threat = m.get("threatType", "THREAT")
            base.threats.setdefault(url, []).append(threat)

        _log.debug("GSB | verdict=%s, threats=%s",
                   "flagged" if base.threats else "clean", base.threats)

    except requests.exceptions.Timeout:
        _log.debug("GSB | verdict=error (timeout)")
    except requests.exceptions.ConnectionError:
        _log.debug("GSB | verdict=error (connection error)")
    except Exception as exc:
        _log.debug("GSB | verdict=error (%s)", exc)

    return base


def _run_urlscan(urls: list[str], api_key: str) -> dict[str, dict]:
    """
    URLScan.io passive domain search (no submission, no async wait).
    Returns url → {malicious, score, tags} for any domain hits found.
    No record for a URL = no_opinion (not added to result dict).
    """
    if not urls:
        return {}
    headers = {"API-Key": api_key} if api_key else {}
    out: dict[str, dict] = {}
    for url in urls[:3]:
        try:
            domain = url.split("//")[-1].split("/")[0].split("?")[0]
            resp = requests.get(
                f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=1",
                headers=headers,
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                continue
            hits = resp.json().get("results", [])
            if not hits:
                continue
            overall = hits[0].get("verdicts", {}).get("overall", {})
            out[url] = {
                "malicious": overall.get("malicious", False),
                "score":     overall.get("score", 0),
                "tags":      overall.get("tags", []),
            }
        except Exception:
            continue
    return out


# ── Per-URL verdict builder ────────────────────────────────────────────────

def _build_url_reputation(
    url: str,
    vt_result:  VTResult,
    gsb_result: _GSBResult,
    us_map:     dict[str, dict],
) -> URLReputation:
    """
    Merge source results for one URL into a single URLReputation.

    Aggregation:
      any flagged                         → malicious or suspicious
      no flagged, at least one clean      → clean
      no flagged, no clean                → unverified (Needs Review)
    """
    rep = URLReputation(url=url)

    flag_verdicts: list[str] = []   # "malicious" / "suspicious" from each flagging source
    any_clean:     bool = False

    # ── VirusTotal ────────────────────────────────────────────────────────
    vt_report = next((r for r in vt_result.urls_checked if r.url == url), None)
    if vt_report and vt_result.available and not vt_report.error:
        vt_v = vt_report.verdict
        if vt_v in ("malicious", "suspicious"):
            flag_verdicts.append(vt_v)
            rep.sources.append("VirusTotal")
            rep.flags.append(f"VirusTotal: {vt_report.flag_count} flagged this link")
        elif vt_v == "clean":
            # VT returned harmless engine votes — explicit clean signal
            any_clean = True
            rep.sources.append("VirusTotal")
            rep.flags.append("VirusTotal: no threats found")
        # vt_v == "unknown" → VT has no record → no_opinion, nothing added

    # ── Google Safe Browsing ──────────────────────────────────────────────
    if gsb_result.reached:
        gsb_threats = gsb_result.threats.get(url, [])
        if gsb_threats:
            flag_verdicts.append("malicious")
            rep.sources.append("Google Safe Browsing")
            for t in gsb_threats:
                label = _GSB_LABELS.get(t, t.lower().replace("_", " "))
                rep.flags.append(f"Google Safe Browsing: flagged as {label}")
        else:
            # HTTP 200 with no match for this URL = explicitly not in threat database
            any_clean = True
            rep.sources.append("Google Safe Browsing")
            rep.flags.append("Google Safe Browsing: no threats found")
    # gsb_result.reached == False → no_opinion or error — neither clears nor flags

    # ── URLScan.io ────────────────────────────────────────────────────────
    us = us_map.get(url)
    if us is not None:
        if us.get("malicious"):
            flag_verdicts.append("malicious")
            rep.sources.append("URLScan.io")
            rep.flags.append(f"URLScan.io: flagged as unsafe (score {us['score']}/100)")
        elif us.get("score", 0) > 50:
            flag_verdicts.append("suspicious")
            rep.sources.append("URLScan.io")
            rep.flags.append(f"URLScan.io: risk score {us['score']}/100")
        else:
            any_clean = True
            rep.sources.append("URLScan.io")
            rep.flags.append("URLScan.io: no threats found")
    # No URLScan record for this domain → no_opinion, nothing added

    # ── Derive verdict ────────────────────────────────────────────────────
    if flag_verdicts:
        rep.verdict = max(flag_verdicts, key=lambda v: _FLAG_RANK.get(v, 0))
    elif any_clean:
        rep.verdict = "clean"
    else:
        rep.verdict = "unverified"

    # ── Plain-English summary ─────────────────────────────────────────────
    _SUMMARIES = {
        "malicious":  "Confirmed dangerous. Do not click this link.",
        "suspicious": "Flagged as unsafe by at least one source. Do not click this link.",
        "clean":      "No threats detected.",
        "unverified": "This link could not be verified.",
    }
    rep.summary = _SUMMARIES[rep.verdict]

    return rep


# ── Overall verdict across URLs ────────────────────────────────────────────

def _aggregate_overall(urls: list[URLReputation]) -> str:
    """
    Worst-case verdict across all URLs.
    Precedence: malicious > suspicious > unverified > clean.
    Initialise from the first URL rather than a fixed sentinel so a single
    clean URL correctly yields an overall verdict of 'clean'.
    """
    if not urls:
        return "unverified"
    _RANK = {"malicious": 4, "suspicious": 3, "unverified": 2, "clean": 1}
    return max((u.verdict for u in urls), key=lambda v: _RANK.get(v, 0))


# ── Public entry point ─────────────────────────────────────────────────────

def check_reputation(
    urls: list[str],
    vt_key:      str = "",
    gsb_key:     str = "",
    urlscan_key: str = "",
) -> ReputationResult:
    """
    Check up to 5 URLs across all configured reputation sources in parallel.
    All sources run independently — results are merged after all complete.
    Always returns a ReputationResult — never raises.
    """
    result = ReputationResult()

    # Clean and deduplicate URLs
    clean_urls = list(dict.fromkeys(_clean_url(u) for u in urls if u.strip()))[:5]

    if not clean_urls:
        result.summary = "No links were found in this message."
        return result

    # Resolve keys from environment when not supplied directly
    vt_key      = vt_key      or os.getenv("VIRUSTOTAL_API_KEY", "")
    gsb_key     = gsb_key     or os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    urlscan_key = urlscan_key or os.getenv("URLSCAN_API_KEY", "")

    # Track which services are configured (at least attempted)
    if vt_key:
        result.services_used.append("VirusTotal")
    if gsb_key:
        result.services_used.append("Google Safe Browsing")
    result.services_used.append("URLScan.io")  # runs without a key
    result.checked = True

    # ── Run all sources in parallel ───────────────────────────────────────
    vt_result:  VTResult   = VTResult(available=False)
    gsb_result: _GSBResult = _GSBResult(
        key_present=bool(gsb_key), request_made=False,
        http_status=None, raw_body="", threats={}, reached=False,
    )
    us_map: dict[str, dict] = {}

    tasks = {
        "vt":      (_run_vt,       clean_urls, vt_key),
        "gsb":     (_run_gsb,      clean_urls, gsb_key),
        "urlscan": (_run_urlscan,  clean_urls, urlscan_key),
    }

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(fn, urls_arg, key_arg): name
            for name, (fn, urls_arg, key_arg) in tasks.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                data = future.result()
                if name == "vt":
                    vt_result = data
                    result.vt_raw = vt_result.to_dict()
                elif name == "gsb":
                    gsb_result = data
                elif name == "urlscan":
                    us_map = data
            except Exception as exc:
                _log.debug("source %s raised: %s", name, exc)

    # ── Merge per-URL ─────────────────────────────────────────────────────
    for url in clean_urls:
        rep = _build_url_reputation(url, vt_result, gsb_result, us_map)
        result.urls.append(rep)

    result.overall_verdict = _aggregate_overall(result.urls)
    result.any_malicious   = result.overall_verdict == "malicious"
    result.any_suspicious  = result.overall_verdict in ("malicious", "suspicious")

    # ── Plain-English overall summary ─────────────────────────────────────
    sources_str      = ", ".join(result.services_used)
    flagged_count    = sum(1 for u in result.urls if u.verdict in ("malicious", "suspicious"))
    clean_count      = sum(1 for u in result.urls if u.verdict == "clean")
    unverified_count = sum(1 for u in result.urls if u.verdict == "unverified")
    total            = len(result.urls)

    link_word     = "link" if total == 1 else "links"
    flagged_word  = "link" if flagged_count == 1 else "links"
    unverif_word  = "link" if unverified_count == 1 else "links"

    if flagged_count > 0:
        if flagged_count == 1:
            result.summary = "This link was flagged as unsafe."
        else:
            result.summary = f"{flagged_count} links were flagged as unsafe."
    elif clean_count > 0 and unverified_count == 0:
        result.summary = f"{total} {link_word} checked — no threats detected."
    elif clean_count > 0:
        appear = "link appears" if clean_count == 1 else "links appear"
        unverif_clause = (
            "1 couldn't be verified"
            if unverified_count == 1
            else "The others couldn't be verified"
        )
        result.summary = (
            f"{clean_count} of {total} {appear} safe. "
            f"{unverif_clause} — only proceed if you trust the source."
        )
    else:
        result.summary = "We couldn't verify the links in this message. Only proceed if you trust the source."

    return result
