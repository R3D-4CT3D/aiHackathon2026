"""
Luman — AI Cyber Safety Coach
Conjoon-inspired three-pane desktop webmail UI
"""
from __future__ import annotations

import datetime
import os
import re
import time
import urllib.parse
from collections import Counter

import streamlit as st
from dotenv import load_dotenv

from analyzer import analyze_message
from demo_data import DEMO_ARRIVAL_TIMES, DEMO_EMAILS
from sample_data import SAMPLE_EMAILS
from url_reputation import check_reputation

_HTTPS_RE         = re.compile(r"https?://[^\s<>\"'{}|\\^`\[\]]+")
_TRAILING_PUNCT   = re.compile(r"[.,;:!?)\]>\"']+$")


def _extract_clean_urls(text: str) -> list[str]:
    """Extract https URLs from text and strip trailing sentence punctuation."""
    return [_TRAILING_PUNCT.sub("", u) for u in _HTTPS_RE.findall(text)]

load_dotenv()

st.set_page_config(
    page_title="Luman · AI Cyber Safety Coach",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens
# ─────────────────────────────────────────────────────────────────────────────

RISK = {
    "Safe": {
        "border": "#27ae60", "bg": "#eaf7ef", "text": "#155a30",
        "chip":   "#c6e9d4", "dot": "#27ae60", "icon": "",
        "banner_border": "#a3d9b8",
    },
    "Needs Review": {
        "border": "#e6990a", "bg": "#fef8ec", "text": "#6b4800",
        "chip":   "#fae6b0", "dot": "#e6990a", "icon": "",
        "banner_border": "#f0cc7a",
    },
    "Likely Phishing": {
        "border": "#e74c3c", "bg": "#fdf1f0", "text": "#7a1f18",
        "chip":   "#f5c5c1", "dot": "#e74c3c", "icon": "",
        "banner_border": "#efaba4",
    },
}

TAGLINE = {
    "Safe":            "No action required.",
    "Needs Review":    "Verify before acting.",
    "Likely Phishing": "Do not click any links or take action.",
}

CONF_CLR = {"high": "#155a30", "medium": "#6b4800", "low": "#7a1f18"}


# ─────────────────────────────────────────────────────────────────────────────
# CSS  ─  conjoon-inspired shell
# ─────────────────────────────────────────────────────────────────────────────

def inject_styles() -> None:
    st.markdown("""
<style>
/* ── tokens ──────────────────────────────────────────────────────────────── */
:root {
  --col-hdr-h:    2.5rem;    /* shared height token — all three column headers */
  --shell:        #1b2333;   /* conjoon-style near-black nav shell          */
  --shell-border: #111827;
  --sidebar:      #222e3a;   /* sidebar, slightly lighter than shell        */
  --sidebar-sel:  #2c3e50;
  --sidebar-txt:  #9fb3bf;
  --sidebar-hi:   #4ab8a0;   /* luman accent on dark bg                    */
  --list-bg:      #f0f2f0;   /* message list panel background               */
  --list-line:    #dde1dd;
  --row-bg:       #ffffff;
  --row-hover:    #f4f7f5;
  --row-sel:      #e8f1ff;   /* neutral blue — clearly not a risk color */
  --row-sel-line: #2563eb;
  --pane-bg:      #ffffff;
  --panel-bg:     #f6f8f6;
  --panel-line:   #e0e4e0;
  --accent:       #264d49;
  --accent-hi:    #1d3c38;
  --text:         #1a2320;
  --text-soft:    #2e3f3a;
  --muted:        #5c706b;
  --muted-soft:   #8a9e99;
  --line:         #dde1dd;
  --line-soft:    rgba(26,35,32,0.08);
  --safe:   #27ae60;
  --review: #e6990a;
  --phish:  #e74c3c;
}

/* ── reset Streamlit chrome ──────────────────────────────────────────────── */
.stApp           { background: var(--list-bg); color: var(--text); }
.block-container { max-width: 100%; padding: 0 !important; }
/* hide native header bar (deploy button, hamburger menu) */
[data-testid="stHeader"]          { display: none !important; }
[data-testid="stStatusWidget"]    { display: none !important; }
/* remove the top gap that Streamlit reserves for the header */
.stApp { padding-top: 0 !important; margin-top: 0 !important; }
/* nested columns inside the reading / analysis panes should be transparent
   (prevents nth-child column-bg rules from darkening the reading-pane header row) */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(n+3)
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  background: transparent !important;
  border: none !important;
  min-height: 0 !important;
  padding: 0 !important;
}
/* collapse default element-container gap inside the reading pane header row */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(n+3)
  [data-testid="stHorizontalBlock"] {
  gap: 0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  background: transparent !important;
  border: none !important; border-radius: 0 !important;
  box-shadow: none !important; padding: 0 !important;
}
.stMarkdown p { margin: 0; }
hr { border-color: var(--line-soft) !important; margin: 0 !important; }

/* ── top chrome  (dark shell applied via column-bg below) ───────────────── */
.lm-chrome {
  height: 56px;
  background: var(--shell);
  border-bottom: 1px solid var(--shell-border);
  display: flex; align-items: center;
  padding: 0 1rem; gap: 0.9rem;
  position: sticky; top: 0; z-index: 200;
}
.lm-chrome-logo {
  width: 33px; height: 33px; border-radius: 6px;
  background: linear-gradient(135deg,#4ab8a0 0%,#1d3c38 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.94rem; font-weight: 800; color: white;
  flex-shrink: 0;
}
.lm-chrome-brand { color: #ddeae7; font-size: 1.26rem; font-weight: 700; letter-spacing: -0.01em; }
.lm-chrome-sep   { width: 1px; height: 20px; background: rgba(255,255,255,0.10); }
.lm-chrome-sub   { color: var(--sidebar-txt); font-size: 0.90rem; }
.lm-chrome-right { margin-left: auto; display: flex; align-items: center; gap: 1rem; }
.lm-stat         { display:flex; flex-direction:column; align-items:flex-end; line-height:1; }
.lm-stat-n       { color: #ddeae7; font-size: 0.88rem; font-weight: 700; }
.lm-stat-l       { color: var(--sidebar-txt); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 1px; }
.lm-stat-sep     { width: 1px; height: 22px; background: rgba(255,255,255,0.10); }

/* ── tabs (live on the dark shell) ──────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  background: var(--shell) !important;
  border-bottom: 1px solid var(--shell-border) !important;
  padding: 0 1rem !important; gap: 0 !important; margin: 0 !important;
}
[data-testid="stTabs"] button[role="tab"] {
  border-radius: 0 !important; margin: 0 !important;
  font-size: 0.82rem !important; font-weight: 600 !important;
  padding: 0.92rem 1.1rem !important;
  color: var(--sidebar-txt) !important;
  border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] button[role="tab"]:hover  { color: #c8dedd !important; background: rgba(255,255,255,0.04) !important; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color: #ddeae7 !important;
  border-bottom-color: var(--sidebar-hi) !important;
  background: transparent !important;
}
[data-testid="stTabs"] [data-testid="stTabsContent"] { padding: 0 !important; }

/* ── column backgrounds — scoped via :has() markers injected per column ──── */
/* Each render function injects an invisible lm-col-* sentinel div.          */
/* :has() is supported in all modern browsers and does not depend on         */
/* Streamlit's internal tab-panel DOM structure.                              */

[data-testid="stColumn"]:has(.lm-col-sb) {
  background: var(--sidebar) !important;
  border-right: 2px solid var(--sidebar-hi) !important;
  min-height: calc(100vh - 96px) !important;
}
[data-testid="stColumn"]:has(.lm-col-list) {
  background: var(--list-bg) !important;
  border-right: 1px solid var(--list-line) !important;
  min-height: calc(100vh - 96px) !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}
/* Kill padding on every wrapper Streamlit nests inside the list column */
[data-testid="stColumn"]:has(.lm-col-list) > div,
[data-testid="stColumn"]:has(.lm-col-list) > div > *,
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stVerticalBlockBorderWrapper"] {
  padding-left: 0 !important;
  padding-right: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
[data-testid="stColumn"]:has(.lm-col-read) {
  background: var(--pane-bg) !important;
  border-right: 1px solid var(--panel-line) !important;
  min-height: calc(100vh - 96px) !important;
}
[data-testid="stColumn"]:has(.lm-col-panel) {
  background: var(--panel-bg) !important;
  border-left: 1px solid var(--panel-line) !important;
  min-height: calc(100vh - 96px) !important;
}
/* sentinel divs are invisible */
.lm-col-sb, .lm-col-list, .lm-col-read, .lm-col-panel {
  display: none;
}

/* ── sidebar buttons ─────────────────────────────────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1)
  [data-testid="stButton"] button {
  background: transparent !important; box-shadow: none !important;
  border: none !important; border-left: 3px solid transparent !important;
  border-radius: 0 !important; padding: 0.42rem 0.9rem !important;
  text-align: left !important; justify-content: flex-start !important;
  color: var(--sidebar-txt) !important; font-size: 0.85rem !important;
  font-weight: 500 !important; min-height: unset !important; width: 100% !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1)
  [data-testid="stButton"] button:hover {
  background: rgba(255,255,255,0.06) !important; color: #ccddd9 !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1)
  [data-testid="stButton"] button[kind="primary"] {
  background: var(--sidebar-sel) !important;
  border-left-color: var(--sidebar-hi) !important; color: #ddeae7 !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1)
  [data-testid="stButton"] button p { color: inherit !important; }

/* ── message-list row buttons ────────────────────────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button {
  background: var(--row-bg) !important; box-shadow: none !important;
  border: none !important;
  border-bottom: 1px solid var(--list-line) !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 !important;
  padding: 0.55rem 0.75rem 1.65rem 0.8rem !important;
  text-align: left !important; justify-content: flex-start !important;
  color: var(--text) !important; font-size: 0.83rem !important;
  font-weight: 400 !important; min-height: 72px !important;
  width: 100% !important; line-height: 1.45 !important;
  white-space: pre-line !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button:hover {
  background: var(--row-hover) !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button[kind="primary"] {
  background: var(--row-sel) !important;
  border-left-color: var(--row-sel-line) !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button p {
  color: inherit !important; white-space: pre-line !important;
  font-size: 0.83rem !important; line-height: 1.45 !important;
}
/* collapse element-container and markdown gaps between list rows */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="element-container"],
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important;
  margin-top: 0 !important;
}
/* chip overlays the bottom of each row button */
.lm-row-chip-wrap {
  position: relative; z-index: 2;
  margin-top: -2.45rem !important;
  margin-bottom: 0 !important;
  padding: 0 0.9rem 0 0.45rem;
  pointer-events: none;
}

/* ── reading-pane action buttons ─────────────────────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stButton"] button {
  background: #f3f5f3 !important; box-shadow: none !important;
  border: 1px solid var(--line) !important; border-radius: 4px !important;
  padding: 0 0.75rem !important; min-height: 1.95rem !important;
  font-size: 0.78rem !important; font-weight: 600 !important;
  color: var(--muted) !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stButton"] button:hover {
  background: #eaeeea !important; color: var(--text) !important;
}
/* ── pane-toggle button ──────────────────────────────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button {
  background: white !important; border: 1px solid var(--line) !important;
  border-radius: 3px !important; padding: 0.22rem 0.65rem !important;
  min-height: unset !important; height: 1.75rem !important;
  font-size: 0.75rem !important; font-weight: 600 !important;
  color: var(--muted) !important; box-shadow: none !important;
  width: auto !important; opacity: 0.85; margin-top: 0.32rem !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button:hover {
  background: #f3f5f3 !important; color: var(--text) !important; opacity: 1;
}
/* ── analysis panel (col 4): horizontal padding ─────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stMarkdownContainer"] {
  padding-left: 0.85rem !important; padding-right: 0.85rem !important;
}
/* ── reading pane (col 3): code block and caption padding ───────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stCodeBlock"],
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3)
  [data-testid="stCaptionContainer"] {
  margin-left: 1rem !important; margin-right: 1rem !important;
}

/* ── expanders ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  border: 1px solid var(--panel-line) !important;
  border-radius: 8px !important;
  background: white !important;
  margin-top: 0 !important;
  margin-bottom: 10px !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
}
[data-testid="stExpander"] summary {
  font-size: 0.72rem !important; font-weight: 700 !important;
  letter-spacing: 0.07em !important; text-transform: uppercase !important;
  color: var(--muted) !important; padding: 0.5rem 0.8rem !important;
}
[data-testid="stExpander"] summary:hover {
  color: var(--text) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 0.1rem 0.8rem 0.6rem !important;
}

/* ── code block ──────────────────────────────────────────────────────────── */
[data-testid="stCodeBlock"] {
  border-radius: 3px !important;
  border: 1px solid var(--line) !important;
  font-size: 0.82rem !important;
}

/* ── sidebar text helpers ────────────────────────────────────────────────── */
.sb-account  { padding: 0.75rem 0.9rem 0.6rem; border-bottom: 1px solid rgba(255,255,255,0.07); }
.sb-acct-name { color: #c5d8d4; font-size: 0.86rem; font-weight: 700; }
.sb-acct-sub  { color: var(--sidebar-txt); font-size: 0.72rem; margin-top: 0.1rem; }
.sb-section   { padding: 0.55rem 0.9rem 0.2rem; color: rgba(155,178,172,0.65); font-size: 0.64rem; font-weight: 700; letter-spacing: 0.11em; text-transform: uppercase; }
.sb-legend    { padding: 0.45rem 0.9rem; }
.sb-legend-row { display:flex; align-items:center; gap:0.5rem; padding: 0.22rem 0; font-size: 0.79rem; color: var(--sidebar-txt); }
.sb-dot       { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
.sb-footer    { padding: 0.65rem 0.9rem; border-top: 1px solid rgba(255,255,255,0.07); margin-top: auto; color: rgba(155,178,172,0.5); font-size: 0.71rem; line-height: 1.5; }

/* ── list header ─────────────────────────────────────────────────────────── */
.lm-list-hdr {
  background: var(--list-bg); border-bottom: 1px solid var(--list-line);
  padding: 0 0.9rem;
  height: var(--col-hdr-h); min-height: var(--col-hdr-h); box-sizing: border-box;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}
.lm-list-hdr-title { font-size: 0.82rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted); }
.lm-list-hdr-count { font-size: 0.78rem; color: var(--muted-soft); }

/* chip inside row */
.lm-row-chip-wrap { display: flex; justify-content: flex-end; padding: 0 0.75rem 0.4rem 0.8rem; }
.lm-chip {
  display: inline-flex; align-items: center; gap: 0.32rem;
  padding: 0.2rem 0.6rem; border-radius: 3px;
  font-size: 0.76rem; font-weight: 700; white-space: nowrap;
}
.lm-chip-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.75; }

/* ── reading pane ─────────────────────────────────────────────────────────── */
.lm-pane-hdr {
  background: var(--list-bg);
  padding: 0.5rem 0.9rem;
  display: flex; align-items: center; justify-content: space-between;
  /* border handled by parent toolbar row so it spans full column width */
}
.lm-breadcrumb { font-size: 0.82rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted-soft); }
.lm-pane-actions { display: flex; gap: 0.4rem; align-items: center; }
.lm-action-ghost {
  font-size: 0.75rem; font-weight: 600; color: var(--muted);
  background: white; border: 1px solid var(--line); border-radius: 3px;
  padding: 0.22rem 0.65rem; cursor: default; white-space: nowrap; opacity: 0.55;
}
.lm-subject {
  font-size: 1.42rem; font-weight: 700; line-height: 1.18;
  color: var(--text); padding: 0.85rem 1rem 0;
  font-family: -apple-system, 'Segoe UI', sans-serif;
}
.lm-meta {
  display: grid; grid-template-columns: auto 1fr; gap: 0.18rem 0.75rem;
  padding: 0.55rem 1rem 0.7rem; font-size: 0.82rem;
}
.lm-meta-l { color: var(--muted-soft); font-size: 0.70rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; padding-top: 0.1rem; white-space: nowrap; }
.lm-meta-v { color: var(--text-soft); }
.lm-divider { height: 1px; background: var(--list-line); margin: 0; }
.lm-risk-bar {
  display: flex; gap: 0.6rem; align-items: flex-start;
  padding: 0.6rem 1rem; border-bottom: 1px solid;
  font-size: 0.85rem; line-height: 1.48;
}
.lm-risk-icon { font-size: 0.88rem; font-weight: 800; min-width: 1rem; padding-top: 0.05rem; flex-shrink: 0; }
.lm-risk-title { font-weight: 700; }
.lm-body { padding: 0.9rem 1rem 1.4rem; }
.lm-p { font-size: 0.94rem; line-height: 1.78; color: #1e2e29; margin-bottom: 0.7rem; }
.lm-link-section { padding: 0.55rem 1rem 1rem; border-top: 1px solid var(--line-soft); }
.lm-link-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: var(--muted-soft); margin-bottom: 0.3rem; }
.lm-link-blocked { background: #fdf1f0; border: 1px solid #efaba4; border-radius: 3px; padding: 0.42rem 0.65rem; color: #7a1f18; font-size: 0.82rem; margin-bottom: 0.4rem; }

/* ── "back to inbox" clear-result button ─────────────────────────────────── */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button[kind="secondary"] {
  background: transparent !important;
  border: 1px solid var(--panel-line) !important;
  color: var(--muted-soft) !important;
  font-size: 0.74rem !important;
  font-weight: 500 !important;
  min-height: 1.8rem !important;
  box-shadow: none !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button[kind="secondary"]:hover {
  color: var(--muted) !important;
  border-color: var(--muted-soft) !important;
  background: rgba(0,0,0,0.02) !important;
}
/* ── analysis panel ──────────────────────────────────────────────────────── */
.lm-panel-hdr {
  background: var(--list-bg);
  padding: 0.5rem 0.9rem;
  display: flex; align-items: center; gap: 0.48rem;
  /* border handled by parent header row so it spans full column width */
}
.lm-panel-hdr-badge { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.lm-panel-hdr-title { font-size: 0.82rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted); }
.lm-panel-body { padding: 0.8rem 0.9rem 1.2rem; }
.lm-verdict {
  border-radius: 6px; border: 1px solid;
  padding: 1rem 1rem 0.9rem; margin-bottom: 0.85rem;
}
/* Label is the dominant visual — everything else defers to it */
.lm-verdict-label { font-size: 1.78rem; font-weight: 800; line-height: 1.0; margin: 0 0 0.26rem; letter-spacing: -0.025em; }
.lm-verdict-tagline { font-size: 0.81rem; opacity: 0.72; margin-bottom: 0; line-height: 1.4; }
/* Confidence bar: supporting detail, not competing with the label */
.lm-conf-wrap { margin-top: 0.75rem; padding-top: 0.55rem; border-top: 1px solid rgba(0,0,0,0.08); }
.lm-conf-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom: 0.28rem; }
.lm-conf-label { font-size: 0.60rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; opacity: 0.75; }
.lm-conf-val { font-size: 0.74rem; font-weight: 600; opacity: 0.85; }
.lm-conf-track { height: 3px; border-radius: 999px; background: rgba(0,0,0,0.08); overflow: hidden; }
.lm-conf-fill  { height: 100%; border-radius: 999px; opacity: 0.7; }
/* Section headers */
.lm-section-hdr {
  font-size: 0.76rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase;
  color: var(--muted); padding: 0.85rem 0 0.45rem;
  border-bottom: 1px solid var(--panel-line); margin-bottom: 0.35rem;
}
/* Card wrapper — used by each named section in the analysis panel */
.lm-card {
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid var(--panel-line);
  padding: 0.9rem 1rem;
  margin-bottom: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.lm-card .lm-section-hdr { padding-top: 0; }
/* Reasons: readable, slightly more weight than actions */
.lm-reason { display: flex; gap: 0.55rem; padding: 0.44rem 0; font-size: 0.83rem; color: var(--text); line-height: 1.52; border-bottom: 1px solid var(--line-soft); }
.lm-reason:last-child { border-bottom: none; }
.lm-rn { color: var(--muted-soft); font-size: 0.64rem; font-weight: 700; min-width: 0.85rem; padding-top: 0.22rem; flex-shrink: 0; }
/* Actions: same size as reasons but clearly secondary via color */
.lm-action { display: flex; gap: 0.52rem; align-items: flex-start; padding: 0.40rem 0; font-size: 0.82rem; color: var(--text-soft); line-height: 1.52; border-bottom: 1px solid var(--line-soft); }
.lm-action:last-child { border-bottom: none; }
.lm-ck { color: var(--muted-soft); font-size: 0.68rem; min-width: 0.85rem; padding-top: 0.16rem; flex-shrink: 0; }
.lm-sig { display: flex; align-items: center; gap: 0.45rem; padding: 0.27rem 0; font-size: 0.80rem; color: var(--text-soft); border-bottom: 1px solid var(--line-soft); }
.lm-sig:last-child { border-bottom: none; }
.lm-sig-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.lm-sig-status { margin-left: auto; font-size: 0.68rem; font-weight: 600; color: var(--muted-soft); }

/* ── Disabled primary CTA — always visible, never faded to nothing ────────── */
/* Streamlit/BaseWeb applies opacity:0.4 on :disabled at high specificity.  */
/* We must (1) cancel that opacity entirely, then (2) paint an explicit      */
/* muted colour so the button looks intentionally inactive, not absent.     */
[data-testid="stButton"] button[kind="primary"]:disabled,
[data-testid="stButton"] button[kind="primary"][disabled] {
  opacity: 1 !important;
  background: #6d9e99 !important;   /* desaturated accent — clearly "off"  */
  border-color: #6d9e99 !important;
  color: rgba(255, 255, 255, 0.78) !important;
  cursor: not-allowed !important;
  box-shadow: none !important;
}

/* ── Analyze Message / Check Link tabs (centered, constrained) ───────────── */
.lm-analyze-wrap {
  max-width: 620px; margin: 1.4rem auto 0; padding: 0 1.5rem 3rem;
}
.lm-analyze-title {
  font-size: 1.25rem; font-weight: 700; color: var(--text);
  margin-bottom: 0.3rem; letter-spacing: -0.01em;
}
.lm-analyze-sub {
  font-size: 0.88rem; color: var(--text-soft); margin-bottom: 0.4rem; line-height: 1.55;
}
.lm-analyze-helper {
  font-size: 0.80rem; color: var(--muted); margin-bottom: 1.1rem; line-height: 1.5;
}
.lm-analyze-opt-hdr {
  font-size: 0.70rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted-soft); margin-top: 1.0rem; margin-bottom: 0.3rem;
}
/* VT / link cards shared */
.lm-vt-card { border-radius: 4px; border: 1px solid; padding: 0.6rem 0.75rem; margin-top: 0.55rem; }
.lm-vt-hdr { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.3rem; }
.lm-vt-summary { font-size: 0.82rem; font-weight: 600; margin-bottom: 0.35rem; }
.lm-vt-row { display: flex; justify-content: space-between; gap: 0.5rem; padding: 0.25rem 0; border-top: 1px solid rgba(0,0,0,0.06); font-size: 0.79rem; }
.lm-vt-url { color: var(--muted); word-break: break-all; flex: 1; }
.lm-vt-verdict { font-weight: 700; white-space: nowrap; }

/* ── analysis panel (col 4) buttons ─────────────────────────────────────── */
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button {
  background: white !important; box-shadow: none !important;
  border: 1px solid var(--panel-line) !important; border-radius: 4px !important;
  color: var(--text-soft) !important; font-size: 0.78rem !important;
  font-weight: 500 !important; min-height: 1.9rem !important;
  padding: 0 0.6rem !important; width: 100% !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button:hover {
  background: var(--panel-bg) !important;
  border-color: var(--accent) !important; color: var(--text) !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important; color: white !important;
}
[data-baseweb="tab-panel"]:first-child
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4)
  [data-testid="stButton"] button[kind="primary"]:hover {
  background: var(--accent-hi) !important; border-color: var(--accent-hi) !important;
}

/* ── feedback section ────────────────────────────────────────────────────── */
.lm-feedback-card {
  margin: 0 0 10px;
  padding: 0.9rem 1rem;
  background: #f0f7f5;
  border: 1px solid var(--panel-line);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.lm-feedback-card .lm-section-hdr {
  color: var(--accent); padding-top: 0; border-bottom-color: #c8ddd8;
}
.lm-feedback-sub {
  font-size: 0.78rem; color: var(--muted); padding: 0.25rem 0 0.65rem;
  line-height: 1.5;
}
.lm-feedback-confirm {
  font-size: 0.78rem; color: var(--muted); padding: 0.25rem 0 0;
  font-style: italic;
}

/* ── demo mode ───────────────────────────────────────────────────────────── */
.sb-demo-wrap  { padding: 0.65rem 0.9rem 0.7rem; border-top: 1px solid rgba(255,255,255,0.07); }
.sb-demo-label { font-size: 0.64rem; font-weight: 700; letter-spacing: 0.11em; text-transform: uppercase; color: rgba(155,178,172,0.65); margin-bottom: 0.5rem; }
.sb-demo-status { font-size: 0.72rem; color: var(--sidebar-txt); margin-top: 0.45rem; line-height: 1.5; }

/* ── :has() button rules — version-proof alternatives to tab-panel scoping ── */

/* sidebar (col 1) */
[data-testid="stColumn"]:has(.lm-col-sb) [data-testid="stButton"] button {
  background: transparent !important; box-shadow: none !important;
  border: none !important; border-left: 3px solid transparent !important;
  border-radius: 0 !important; padding: 0.42rem 0.9rem !important;
  text-align: left !important; justify-content: flex-start !important;
  color: var(--sidebar-txt) !important; font-size: 0.85rem !important;
  font-weight: 500 !important; min-height: unset !important; width: 100% !important;
}
[data-testid="stColumn"]:has(.lm-col-sb) [data-testid="stButton"] button:hover {
  background: rgba(255,255,255,0.06) !important; color: #ccddd9 !important;
}
[data-testid="stColumn"]:has(.lm-col-sb) [data-testid="stButton"] button[kind="primary"] {
  background: var(--sidebar-sel) !important;
  border-left-color: var(--sidebar-hi) !important; color: #ddeae7 !important;
}
[data-testid="stColumn"]:has(.lm-col-sb) [data-testid="stButton"] button p {
  color: inherit !important;
}

/* message list (col 2) */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button {
  background: var(--row-bg) !important; box-shadow: none !important;
  border: none !important;
  border-bottom: 1px solid var(--list-line) !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 !important;
  padding: 0.9rem 0.9rem 2.6rem 0.75rem !important;
  text-align: left !important; justify-content: flex-start !important;
  color: var(--text) !important; font-size: 0.92rem !important;
  font-weight: 400 !important; min-height: 136px !important;
  width: 100% !important; line-height: 1.62 !important;
  white-space: pre-line !important;
}
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button:hover {
  background: var(--row-hover) !important;
}
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button[kind="primary"] {
  background: var(--row-sel) !important;
  border-left-color: var(--row-sel-line) !important;
}
/* ── Unified left rail for inbox row text ───────────────────────────────── */
/* Strip every layer between the button edge and the text nodes so sender,  */
/* subject, and preview all share one clean left origin.                    */

/* 1. stMarkdownContainer inside the button: Streamlit default styles may   */
/*    add horizontal padding here; zero all sides so the button's own       */
/*    padding-left (0.9rem) becomes the sole left offset.                   */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"]
  [data-testid="stMarkdownContainer"] {
  margin: 0 !important; padding: 0 !important;
}

/* 2. Inner div wrapper — override Streamlit's flex centering so all rows   */
/*    start from the same left edge regardless of text length / wrapping.   */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button > div {
  margin: 0 !important; padding: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  justify-content: flex-start !important;
  width: 100% !important;
}

/* 3. p: the text block itself — zero all sides, set typography              */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button p {
  margin: 0 !important; padding: 0 !important;
  text-indent: 0 !important;
  text-align: left !important;
  width: 100% !important;
  color: var(--text) !important; white-space: pre-line !important;
  font-size: 0.88rem !important; line-height: 1.62 !important;
  font-weight: 400 !important;
}

/* 4. Subject: <strong> from markdown **text** — inline, no extra offset     */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button p strong {
  margin: 0 !important; padding: 0 !important;
  font-weight: 700 !important;
  font-size: 0.94rem !important;
  color: var(--text) !important;
}

/* 5. Sender/time first line: muted and slightly smaller                     */
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stButton"] button p::first-line {
  font-size: 0.79rem !important;
  color: var(--muted-soft) !important;
  font-weight: 400 !important;
}

/* Zero out Streamlit's default spacing between row elements */
[data-testid="stColumn"]:has(.lm-col-list) > div:first-child { gap: 0 !important; }
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="element-container"],
[data-testid="stColumn"]:has(.lm-col-list) [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important; margin-top: 0 !important;
}

/* reading pane (col 3) — action buttons */
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="stButton"] button {
  background: #f3f5f3 !important; box-shadow: none !important;
  border: 1px solid var(--line) !important; border-radius: 4px !important;
  padding: 0 0.75rem !important; min-height: 1.95rem !important;
  font-size: 0.78rem !important; font-weight: 600 !important;
  color: var(--muted) !important;
}
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="stButton"] button:hover {
  background: #eaeeea !important; color: var(--text) !important;
}
/* reading pane toggle (nested col 2) */
[data-testid="stColumn"]:has(.lm-col-read)
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button {
  background: white !important; border: 1px solid var(--line) !important;
  border-radius: 3px !important; padding: 0.22rem 0.65rem !important;
  min-height: unset !important; height: 1.75rem !important;
  font-size: 0.75rem !important; font-weight: 600 !important;
  color: var(--muted) !important; box-shadow: none !important;
  width: auto !important; opacity: 0.85; margin-top: 0.32rem !important;
}
[data-testid="stColumn"]:has(.lm-col-read)
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button:hover {
  background: #f3f5f3 !important; color: var(--text) !important; opacity: 1;
}
/* reading pane code/caption padding */
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="stCodeBlock"],
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="stCaptionContainer"] {
  margin-left: 1rem !important; margin-right: 1rem !important;
}

/* analysis panel (col 4) — buttons */
[data-testid="stColumn"]:has(.lm-col-panel) [data-testid="stButton"] button {
  background: white !important; box-shadow: none !important;
  border: 1px solid var(--panel-line) !important; border-radius: 4px !important;
  color: var(--text-soft) !important; font-size: 0.78rem !important;
  font-weight: 500 !important; min-height: 1.9rem !important;
  padding: 0 0.6rem !important; width: 100% !important;
}
[data-testid="stColumn"]:has(.lm-col-panel) [data-testid="stButton"] button:hover {
  background: var(--panel-bg) !important;
  border-color: var(--accent) !important; color: var(--text) !important;
}
[data-testid="stColumn"]:has(.lm-col-panel) [data-testid="stButton"] button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important; color: white !important;
}
[data-testid="stColumn"]:has(.lm-col-panel) [data-testid="stButton"] button[kind="primary"]:hover {
  background: var(--accent-hi) !important; border-color: var(--accent-hi) !important;
}
/* analysis panel markdown padding */
[data-testid="stColumn"]:has(.lm-col-panel) [data-testid="stMarkdownContainer"] {
  padding-left: 0.85rem !important; padding-right: 0.85rem !important;
}
/* analysis panel expand button (header row nested col 2) — match Hide/Show style */
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:has(.lm-panel-hdr) > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button {
  background: white !important; border: 1px solid var(--line) !important;
  border-radius: 3px !important; padding: 0.22rem 1.1rem !important;
  min-height: unset !important; height: 1.75rem !important;
  font-size: 0.75rem !important; font-weight: 600 !important;
  color: var(--muted) !important; box-shadow: none !important;
  width: 100% !important; opacity: 0.85; margin-top: 0.32rem !important;
  white-space: nowrap !important; overflow: hidden !important;
  text-overflow: ellipsis !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:has(.lm-panel-hdr) > [data-testid="stColumn"]:nth-child(2)
  [data-testid="stButton"] button:hover {
  background: #f3f5f3 !important; color: var(--text) !important; opacity: 1;
}

/* ── Collapse sentinel marker containers to zero height ─────────────────── */
/* The lm-col-* divs are display:none, but their stMarkdownContainer parent  */
/* can still occupy vertical space. Kill that space in all four columns.     */
[data-testid="stMarkdownContainer"]:has(.lm-col-sb),
[data-testid="stMarkdownContainer"]:has(.lm-col-list),
[data-testid="stMarkdownContainer"]:has(.lm-col-read),
[data-testid="stMarkdownContainer"]:has(.lm-col-panel) {
  margin: 0 !important; padding: 0 !important;
  min-height: 0 !important; max-height: 0 !important;
  height: 0 !important; overflow: hidden !important;
  line-height: 0 !important;
}

/* ── Normalize reading pane vertical spacing — match inbox list column ────── */
/* The list column already collapses element-container margins to 0.         */
/* Apply the same here so both columns start content at the exact same y.   */
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="element-container"],
[data-testid="stColumn"]:has(.lm-col-read) [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important; margin-top: 0 !important;
}
[data-testid="stColumn"]:has(.lm-col-read) > div:first-child {
  padding-top: 0 !important; gap: 0 !important;
}

/* ── Message column: header row spans full column width + shared height ───── */
[data-testid="stColumn"]:has(.lm-col-read)
  [data-testid="stHorizontalBlock"]:has(.lm-pane-hdr) {
  background: var(--list-bg) !important;
  border-bottom: 1px solid var(--list-line) !important;
  min-height: var(--col-hdr-h) !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}
[data-testid="stColumn"]:has(.lm-col-read)
  [data-testid="stHorizontalBlock"]:has(.lm-pane-hdr) > [data-testid="stColumn"] {
  background: transparent !important;
  border: none !important;
}

/* ── Panel column: flush header to top, preserve section breathing room ──── */
/* Only remove the top padding — do NOT zero out gap, sections need it.     */
[data-testid="stColumn"]:has(.lm-col-panel) > div:first-child {
  padding-top: 0 !important;
}

/* ── Security Analysis column: header row spans full column width + shared height */
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:has(.lm-panel-hdr) {
  background: var(--list-bg) !important;
  border-bottom: 1px solid var(--list-line) !important;
  min-height: var(--col-hdr-h) !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:has(.lm-panel-hdr) > [data-testid="stColumn"] {
  background: transparent !important;
  border: none !important;
}

/* ── Feedback buttons: uniform size, clearly outlined in green/red ──────── */
/* Exclude the header row (which also has a button) using :not(:has(.lm-panel-hdr)) */
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(1) [data-testid="stButton"] button,
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button {
  min-height: 2.3rem !important;
  width: 100% !important;
  font-size: 0.80rem !important;
  padding: 0 0.75rem !important;
  border-radius: 4px !important;
  box-shadow: none !important;
  font-weight: 600 !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(1) [data-testid="stButton"] button {
  background: white !important;
  border: 1.5px solid #27ae60 !important;
  color: #155a30 !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button {
  background: white !important;
  border: 1.5px solid #c0392b !important;
  color: #7a1f18 !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(1) [data-testid="stButton"] button:hover {
  background: #f0faf5 !important;
}
[data-testid="stColumn"]:has(.lm-col-panel)
  [data-testid="stHorizontalBlock"]:not(:has(.lm-panel-hdr)):has([data-testid="stButton"])
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button:hover {
  background: #fdf1f0 !important;
}

@keyframes lm-new-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.55; transform: scale(0.96); }
}
.lm-new-badge {
  display: inline-flex; align-items: center;
  background: #27ae60; color: #fff;
  font-size: 0.58rem; font-weight: 800;
  padding: 0.08rem 0.35rem; border-radius: 3px;
  letter-spacing: 0.08em; text-transform: uppercase;
  animation: lm-new-pulse 1.1s ease-in-out infinite;
  vertical-align: middle; margin-left: 0.3rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

def chip(status: str) -> str:
    r = RISK[status]
    bg  = r["chip"]
    txt = r["text"]
    return (
        f"<span class='lm-chip' style='background:{bg};color:{txt};'>"
        f"<span class='lm-chip-dot'></span>{status}</span>"
    )


def conf_bar(pct: int, band: str, color: str) -> str:
    return (
        f"<div class='lm-conf-wrap'>"
        f"<div class='lm-conf-row'>"
        f"<span class='lm-conf-label' style='color:{color};'>Confidence</span>"
        f"<span class='lm-conf-val' style='color:{color};'>{pct}% · {band.capitalize()}</span>"
        f"</div>"
        f"<div class='lm-conf-track'>"
        f"<div class='lm-conf-fill' style='width:{pct}%;background:{color};'></div>"
        f"</div></div>"
    )


def reasons_html(reasons: list[str]) -> str:
    return "".join(
        f"<div class='lm-reason'><span class='lm-rn'>{i+1}.</span><span>{r}</span></div>"
        for i, r in enumerate(reasons)
    )


def actions_html(actions: list[str]) -> str:
    return "".join(
        f"<div class='lm-action'><span class='lm-ck'>☐</span><span>{a}</span></div>"
        for a in actions
    )


def ml_note_html(ml_signal: dict | None) -> str:
    """
    Render a subtle ML classifier note when the signal fires on non-Safe verdicts.
    Returns empty string if there is nothing worth showing.
    """
    if not ml_signal:
        return ""
    reason = ml_signal.get("reason", "")
    if not reason:
        return ""
    return (
        "<div style='"
        "margin-top:0.65rem;"
        "padding:0.5rem 0.7rem;"
        "background:var(--panel-bg);"
        "border-left:2px solid var(--panel-line);"
        "border-radius:4px;"
        "font-size:0.78rem;"
        "color:var(--muted);"
        "line-height:1.45;"
        "'>"
        f"<span style='font-weight:600;color:var(--muted-soft);'>Pattern analysis: </span>{reason}"
        "</div>"
    )


def vt_card_html(vt: dict) -> str:
    if not vt or not vt.get("available"):
        return "<div style='font-size:0.78rem;color:var(--muted-soft);padding:0.3rem 0;'>VirusTotal: not configured</div>"
    urls = vt.get("urls_checked", [])
    if not urls:
        return f"<div style='font-size:0.78rem;color:var(--muted-soft);padding:0.3rem 0;'>{vt.get('summary','No URLs found')}</div>"
    any_m = vt.get("any_malicious", False)
    any_s = vt.get("any_suspicious", False)
    if any_m:
        bc, tc, bg = "#e74c3c", "#7a1f18", "#fdf1f0"
    elif any_s:
        bc, tc, bg = "#e6990a", "#6b4800", "#fef8ec"
    else:
        bc, tc, bg = "#27ae60", "#155a30", "#eaf7ef"
    rows = ""
    for r in urls:
        short = r["url"][:46] + "…" if len(r["url"]) > 49 else r["url"]
        if r.get("error"):
            vc, vt_txt = "var(--muted-soft)", f"error: {r['error']}"
        else:
            v = r.get("verdict", "unknown")
            vc = {"malicious": "#e74c3c", "suspicious": "#e6990a",
                  "clean": "#27ae60", "unknown": "var(--muted)"}.get(v, "var(--muted)")
            vt_txt = f"{r['flag_count']} · {v}"
            if r.get("last_analysis_date"):
                vt_txt += f" · {r['last_analysis_date']}"
        rows += (
            f"<div class='lm-vt-row'>"
            f"<span class='lm-vt-url'>{short}</span>"
            f"<span class='lm-vt-verdict' style='color:{vc};'>{vt_txt}</span>"
            f"</div>"
        )
    return (
        f"<div class='lm-vt-card' style='background:{bg};border-color:{bc};'>"
        f"<div class='lm-vt-hdr' style='color:{tc};'>VirusTotal URL Scan</div>"
        f"<div class='lm-vt-summary' style='color:{tc};'>{vt.get('summary','')}</div>"
        f"{rows}</div>"
    )


def rep_card_html(rep: dict) -> str:
    """Render a compact multi-source link-reputation card."""
    if not rep:
        return ""

    overall = rep.get("overall_verdict", "unknown")
    summary = rep.get("summary", "")
    urls    = rep.get("urls", [])
    checked = rep.get("checked", False)

    # Both malicious and suspicious map to "Likely Phishing" (any flag = danger)
    _VERDICT_COLORS = {
        "malicious":   ("#e74c3c", "#7a1f18", "#fdf1f0"),
        "suspicious":  ("#e74c3c", "#7a1f18", "#fdf1f0"),
        "clean":       ("#27ae60", "#155a30", "#eaf7ef"),
        "unverified":  ("#e6990a", "#6b4800", "#fef8ec"),
    }
    _VERDICT_LABELS = {
        "malicious":  "Likely Phishing",
        "suspicious": "Likely Phishing",
        "clean":      "Safe",
        "unverified": "Needs Review",
    }
    bc, tc, bg = _VERDICT_COLORS.get(overall, _VERDICT_COLORS["unverified"])

    if not checked:
        return (
            f"<div style='font-size:0.78rem;color:var(--muted-soft);"
            f"padding:0.35rem 0;line-height:1.5;'>{summary}</div>"
        )

    rows = ""
    for u in urls:
        raw_url = u.get("url", "")
        short   = raw_url[:50] + "…" if len(raw_url) > 52 else raw_url
        v_raw = u.get("verdict", "unverified")
        v  = _VERDICT_LABELS.get(v_raw, "Needs Review")
        vc = {
            "malicious": "#e74c3c", "suspicious": "#e74c3c",
            "clean": "#27ae60", "unverified": "#e6990a",
        }.get(v_raw, "#e6990a")
        srcs = ", ".join(u.get("sources", [])) or "not checked"
        # Verdict badge uses a bordered inline element so URL and verdict
        # are visually separated even if the parent flex container is stripped
        badge = (
            f"<span style='display:inline-block;margin-left:6px;"
            f"padding:1px 5px;border:1px solid {vc};border-radius:3px;"
            f"font-size:0.68rem;font-weight:700;color:{vc};"
            f"white-space:nowrap;vertical-align:middle;'>{v}</span>"
        )
        flag_html = "".join(
            f"<div style='font-size:0.70rem;color:{vc};"
            f"margin-top:0.1rem;line-height:1.4;'>↳ {f}</div>"
            for f in u.get("flags", [])
        )
        rows += (
            f"<div style='padding:0.3rem 0;"
            f"border-bottom:1px solid rgba(0,0,0,0.06);'>"
            f"<div style='font-size:0.74rem;font-family:monospace;"
            f"color:var(--text-soft);word-break:break-all;line-height:1.5;'>"
            f"{short}{badge}</div>"
            f"<div style='font-size:0.68rem;color:var(--muted);margin-top:0.05rem;'>"
            f"Sources: {srcs}</div>"
            f"{flag_html}"
            f"</div>"
        )

    _svc = rep.get("services_used", [])
    if len(_svc) >= 3:
        services = ", ".join(_svc[:-1]) + ", and " + _svc[-1]
    elif len(_svc) == 2:
        services = " and ".join(_svc)
    else:
        services = _svc[0] if _svc else ""
    services_line = (
        f"<div style='font-size:0.68rem;color:{tc};opacity:0.7;"
        f"margin-bottom:0.35rem;'>Checked using trusted security tools: {services}</div>"
        if services else ""
    )

    return (
        f"<div style='background:{bg};border:1px solid {bc};"
        f"border-radius:6px;padding:0.65rem 0.8rem;margin-top:0.15rem;'>"
        f"<div style='font-size:0.67rem;font-weight:700;color:{tc};"
        f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.2rem;'>"
        f"Link Reputation &nbsp;·&nbsp; {_VERDICT_LABELS.get(overall, 'Needs Review')}</div>"
        f"{services_line}"
        f"<div style='font-size:0.78rem;color:{tc};margin-bottom:0.4rem;'>"
        f"{summary}</div>"
        f"{rows}"
        f"</div>"
    )


def sig_row(label: str, detected: bool) -> str:
    color = "#e74c3c" if detected else "#27ae60"
    status = "Detected" if detected else "Not detected"
    return (
        f"<div class='lm-sig'>"
        f"<span class='lm-sig-dot' style='background:{color};'></span>"
        f"<span>{label}</span>"
        f"<span class='lm-sig-status'>{status}</span>"
        f"</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _all_emails() -> list[dict]:
    """Demo inbox (newest first) prepended to the static sample emails."""
    demo = list(st.session_state.get("demo_inbox", []))
    return demo + SAMPLE_EMAILS


def folder_counts() -> Counter:
    return Counter(e["folder"] for e in _all_emails())


def get_emails(folder: str) -> list[dict]:
    return [e for e in _all_emails() if e["folder"] == folder]


def get_email(eid: str | None) -> dict | None:
    return next((e for e in _all_emails() if e["id"] == eid), None) if eid else None


def inbox_stats() -> tuple[int, int, int]:
    """Return (total, phishing_count, review_count) across all visible emails."""
    all_e    = _all_emails()
    total    = len(all_e)
    threats  = sum(1 for e in all_e if e["status"] == "Likely Phishing")
    reviewed = sum(1 for e in all_e if e["status"] == "Needs Review")
    return total, threats, reviewed


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

def init_state() -> None:
    # ── Demo state (must come first — get_emails() reads demo_inbox) ──────
    if "demo_playing"        not in st.session_state:
        st.session_state.demo_playing        = False
    if "demo_start_time"     not in st.session_state:
        st.session_state.demo_start_time     = 0.0
    if "demo_elapsed_before" not in st.session_state:
        st.session_state.demo_elapsed_before = 0.0
    if "demo_inbox"          not in st.session_state:
        st.session_state.demo_inbox          = []     # delivered demo emails (newest first)
    if "demo_new_id"         not in st.session_state:
        st.session_state.demo_new_id         = None   # id of most-recently-arrived email
    if "demo_new_since"      not in st.session_state:
        st.session_state.demo_new_since      = 0.0    # wall-clock time of last arrival

    if "selected_folder" not in st.session_state:
        st.session_state.selected_folder = "Inbox"
    folder_emails = get_emails(st.session_state.selected_folder)
    if "selected_email_id" not in st.session_state or (
        folder_emails
        and st.session_state.selected_email_id not in {e["id"] for e in folder_emails}
    ):
        st.session_state.selected_email_id = folder_emails[0]["id"] if folder_emails else None
    if "panel_open" not in st.session_state:
        e = get_email(st.session_state.selected_email_id)
        st.session_state.panel_open = bool(e and e["status"] != "Safe")
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    if "panel_wide" not in st.session_state:
        st.session_state.panel_wide = False
    if "analyze_msg_result" not in st.session_state:
        st.session_state.analyze_msg_result = None   # Analyze Message tab result
    if "check_link_result" not in st.session_state:
        st.session_state.check_link_result = None    # Check Link tab result
    if "feedback_log" not in st.session_state:
        st.session_state.feedback_log = []           # list of feedback dicts
    if "feedback_by_id" not in st.session_state:
        st.session_state.feedback_by_id = {}         # msg_id -> user_label


def select_folder(folder: str) -> None:
    st.session_state.selected_folder = folder
    emails = get_emails(folder)
    st.session_state.selected_email_id = emails[0]["id"] if emails else None
    e = get_email(st.session_state.selected_email_id)
    st.session_state.panel_open = bool(e and e["status"] != "Safe")


def open_email(eid: str) -> None:
    st.session_state.selected_email_id = eid
    e = get_email(eid)
    st.session_state.panel_open = bool(e and e["status"] != "Safe")


def toggle_panel() -> None:
    st.session_state.panel_open = not st.session_state.panel_open


def toggle_panel_wide() -> None:
    st.session_state.panel_wide = not st.session_state.panel_wide


# ─────────────────────────────────────────────────────────────────────────────
# Top chrome
# ─────────────────────────────────────────────────────────────────────────────

def render_chrome() -> None:
    analyzed, threats, reviewed = inbox_stats()
    st.markdown(
        f"<div class='lm-chrome'>"
        f"  <div class='lm-chrome-logo'>L</div>"
        f"  <span class='lm-chrome-brand'>Luman</span>"
        f"  <span class='lm-chrome-sep'></span>"
        f"  <span class='lm-chrome-sub'>AI Cyber Safety Coach</span>"
        f"  <div class='lm-chrome-right'>"
        f"    <div class='lm-stat'><span class='lm-stat-n'>{analyzed}</span>"
        f"      <span class='lm-stat-l'>Messages</span></div>"
        f"    <span class='lm-stat-sep'></span>"
        f"    <div class='lm-stat'><span class='lm-stat-n' style='color:#ef9a9a;'>{threats}</span>"
        f"      <span class='lm-stat-l'>Threats</span></div>"
        f"    <span class='lm-stat-sep'></span>"
        f"    <div class='lm-stat'><span class='lm-stat-n' style='color:#ffe082;'>{reviewed}</span>"
        f"      <span class='lm-stat-l'>Review</span></div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Demo-mode helpers
# ─────────────────────────────────────────────────────────────────────────────

def _demo_elapsed() -> float:
    """Total accumulated demo seconds (paused + current session)."""
    ss = st.session_state
    base = ss.demo_elapsed_before
    if ss.demo_playing:
        base += time.time() - ss.demo_start_time
    return base


def _demo_tick() -> None:
    """Deliver any demo emails that are now due. Called once per polling cycle."""
    ss       = st.session_state
    elapsed  = _demo_elapsed()
    delivered = len(ss.demo_inbox)

    if delivered >= len(DEMO_EMAILS):
        ss.demo_playing = False          # all delivered — auto-stop
        return

    next_due = DEMO_ARRIVAL_TIMES[delivered]
    if elapsed < next_due:
        return                           # not yet time

    # Build the email copy with a live timestamp
    email = dict(DEMO_EMAILS[delivered])
    now   = datetime.datetime.now()
    hour  = now.strftime("%I").lstrip("0") or "12"
    email["received"] = f"{hour}:{now.strftime('%M %p')}"

    ss.demo_inbox.insert(0, email)       # prepend so newest appears at top
    ss.demo_new_id    = email["id"]
    ss.demo_new_since = time.time()


def _demo_play() -> None:
    ss = st.session_state
    if len(ss.demo_inbox) >= len(DEMO_EMAILS):
        return   # already done
    ss.demo_start_time = time.time()
    ss.demo_playing    = True


def _demo_pause() -> None:
    ss = st.session_state
    ss.demo_elapsed_before += time.time() - ss.demo_start_time
    ss.demo_playing = False


def _demo_restart() -> None:
    ss = st.session_state
    # Clear cached reputation data for demo emails
    for key in list(ss.keys()):
        if key.startswith("rep_demo-"):
            del ss[key]
    ss.demo_inbox          = []
    ss.demo_playing        = False
    ss.demo_elapsed_before = 0.0
    ss.demo_start_time     = 0.0
    ss.demo_new_id         = None
    ss.demo_new_since      = 0.0
    # Reset reading pane to first regular inbox email
    base = [e for e in SAMPLE_EMAILS if e["folder"] == "Inbox"]
    ss.selected_email_id = base[0]["id"] if base else None
    ss.panel_open = False


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar  (column 1 — dark)
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    st.markdown("<div class='lm-col-sb'></div>", unsafe_allow_html=True)
    counts = folder_counts()

    st.markdown(
        "<div class='sb-account'>"
        "<div class='sb-acct-name'>taylor@luman-demo.com</div>"
        "<div class='sb-acct-sub'>Demo account · Luman MVP</div>"
        "</div>"
        "<div class='sb-section'>Mailboxes</div>",
        unsafe_allow_html=True,
    )

    for folder, icon in [("Inbox", "📥"), ("Archive", "📁")]:
        n = counts.get(folder, 0)
        kind = "primary" if st.session_state.selected_folder == folder else "secondary"
        st.button(
            f"{icon}  {folder}  ({n})",
            key=f"folder-{folder}",
            use_container_width=True,
            on_click=select_folder,
            args=(folder,),
            type=kind,
        )

    st.markdown(
        "<div class='sb-section' style='margin-top:0.55rem;'>Risk key</div>"
        "<div class='sb-legend'>"
        "<div class='sb-legend-row'><span class='sb-dot' style='background:#27ae60;'></span>Safe</div>"
        "<div class='sb-legend-row'><span class='sb-dot' style='background:#e6990a;'></span>Needs Review</div>"
        "<div class='sb-legend-row'><span class='sb-dot' style='background:#e74c3c;'></span>Likely Phishing</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Demo controls ────────────────────────────────────────────────────────
    ss           = st.session_state
    delivered    = len(ss.demo_inbox)
    total        = len(DEMO_EMAILS)
    all_done     = delivered >= total

    st.markdown("<div class='sb-demo-wrap'><div class='sb-demo-label'>Live Demo</div></div>",
                unsafe_allow_html=True)

    if all_done:
        status_txt = f"Demo complete — {total} emails delivered"
        st.markdown(f"<div class='sb-demo-status' style='color:var(--sidebar-hi);'>{status_txt}</div>",
                    unsafe_allow_html=True)
        st.button("↺ Replay", key="demo_restart", use_container_width=True,
                  on_click=_demo_restart)
    else:
        # Play / Pause toggle
        if ss.demo_playing:
            st.button("⏸  Pause", key="demo_pause", use_container_width=True,
                      on_click=_demo_pause, type="primary")
        else:
            label = "▶  Play" if delivered == 0 else "▶  Resume"
            st.button(label, key="demo_play", use_container_width=True,
                      on_click=_demo_play)
        st.button("↺  Restart", key="demo_restart", use_container_width=True,
                  on_click=_demo_restart)
        # Progress status
        if ss.demo_playing:
            status_txt = f"Sending email {delivered + 1} of {total}…"
        elif delivered > 0:
            status_txt = f"Paused · {delivered} of {total} delivered"
        else:
            status_txt = f"{total} scripted emails · ~52 s runtime"
        st.markdown(f"<div class='sb-demo-status'>{status_txt}</div>",
                    unsafe_allow_html=True)

    st.markdown(
        "<div class='sb-footer'>Select a message to review it.<br>"
        "Use the Analyze Message tab to scan your own messages.</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Message list  (column 2 — light)
# ─────────────────────────────────────────────────────────────────────────────

def render_email_list(emails: list[dict]) -> None:
    st.markdown("<div class='lm-col-list'></div>", unsafe_allow_html=True)
    folder = st.session_state.selected_folder
    st.markdown(
        f"<div class='lm-list-hdr'>"
        f"<span class='lm-list-hdr-title'>{folder}</span>"
        f"<span class='lm-list-hdr-count'>{len(emails)} messages</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    ss = st.session_state
    _new_id    = ss.get("demo_new_id")
    _new_since = ss.get("demo_new_since", 0.0)
    _is_fresh  = _new_id and (time.time() - _new_since) < 5.0

    for email in emails:
        selected  = email["id"] == ss.selected_email_id
        is_new    = _is_fresh and email["id"] == _new_id
        received  = email.get("received") or "Just now"
        # Three-line label: sender·time / subject (bold via markdown) / preview
        label = (
            f"{email['sender_email']}  ·  {received}\n"
            f"**{email['subject']}**\n"
            f"{email['preview']}"
        )
        st.button(
            label,
            key=f"email-{email['id']}",
            use_container_width=True,
            on_click=open_email,
            args=(email["id"],),
            type="primary" if selected else "secondary",
        )
        # Colored pill (+ NEW badge for freshly arrived demo emails)
        new_badge = "<span class='lm-new-badge'>NEW</span>" if is_new else ""
        st.markdown(
            f"<div class='lm-row-chip-wrap'>{chip(email['status'])}{new_badge}</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Reading pane  (column 3 — white)
# ─────────────────────────────────────────────────────────────────────────────

def render_email_view(email: dict | None) -> None:
    st.markdown("<div class='lm-col-read'></div>", unsafe_allow_html=True)
    if not email:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;"
            "height:55vh;flex-direction:column;gap:0.5rem;'>"
            "<div style='font-size:2.4rem;opacity:0.15;'>✉</div>"
            "<div style='font-size:0.88rem;font-weight:600;color:var(--muted-soft);'>No message selected</div>"
            "<div style='font-size:0.78rem;color:var(--muted-soft);'>Choose a message from the list</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    r = RISK[email["status"]]

    # ── pane toolbar ──────────────────────────────────────────────────────
    # Two-column: wide header | narrow toggle button (nested col CSS keeps transparent)
    hdr_col, btn_col = st.columns([5.5, 1.0], gap="small")
    with hdr_col:
        st.markdown(
            f"<div class='lm-pane-hdr'>"
            f"<span class='lm-breadcrumb'>Message</span>"
            f"<div class='lm-pane-actions'>"
            f"{chip(email['status'])}"
            f"<span class='lm-action-ghost'>Reply</span>"
            f"<span class='lm-action-ghost'>Forward</span>"
            f"<span class='lm-action-ghost'>Archive</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    with btn_col:
        toggle_label = "Hide analysis" if st.session_state.panel_open else "Show analysis"
        st.button(toggle_label, on_click=toggle_panel, use_container_width=True, key="pane-toggle")

    # ── subject ───────────────────────────────────────────────────────────
    st.markdown(f"<div class='lm-subject'>{email['subject']}</div>", unsafe_allow_html=True)

    # ── metadata ──────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='lm-meta'>"
        f"<span class='lm-meta-l'>From</span>"
        f"<span class='lm-meta-v'>{email['sender']} &lt;{email['sender_email']}&gt;</span>"
        f"<span class='lm-meta-l'>To</span>"
        f"<span class='lm-meta-v'>{email['recipient']}</span>"
        f"<span class='lm-meta-l'>Received</span>"
        f"<span class='lm-meta-v'>{email['received']}</span>"
        f"<span class='lm-meta-l'>Folder</span>"
        f"<span class='lm-meta-v'>{email['folder']}</span>"
        f"</div>"
        f"<div class='lm-divider'></div>",
        unsafe_allow_html=True,
    )

    # ── risk banner (non-safe) ────────────────────────────────────────────
    if email["status"] != "Safe":
        if email["status"] == "Likely Phishing":
            title = "Do not click any links or take action."
        else:
            title = "Pause before acting on this message."
        r_bg  = r["bg"]
        r_bb  = r["banner_border"]
        r_txt = r["text"]
        e_exp = email["explanation"]
        st.markdown(
            f"<div class='lm-risk-bar' style='background:{r_bg};"
            f"border-color:{r_bb};color:{r_txt};'>"
            f"<div><span class='lm-risk-title'>{title}</span>"
            f" {e_exp}</div></div>",
            unsafe_allow_html=True,
        )

    # ── body ──────────────────────────────────────────────────────────────
    body_html = "".join(f"<p class='lm-p'>{p}</p>" for p in email["body"])
    st.markdown(f"<div class='lm-body'>{body_html}</div>", unsafe_allow_html=True)

    # "Link in message" removed — links are surfaced in the Link Reputation
    # section of the analysis panel, which is the authoritative place.


# ─────────────────────────────────────────────────────────────────────────────
# Feedback helpers
# ─────────────────────────────────────────────────────────────────────────────

def _submit_feedback(msg_id: str, predicted: str, user_label: str,
                     subject: str, sender_email: str) -> None:
    """Record one feedback entry in session state."""
    entry = {
        "msg_id":       msg_id,
        "predicted":    predicted,
        "user_label":   user_label,
        "timestamp":    datetime.datetime.now().isoformat(),
        "subject":      subject,
        "sender_email": sender_email,
    }
    st.session_state.feedback_log.append(entry)
    st.session_state.feedback_by_id[msg_id] = user_label


def _render_feedback_section(email: dict) -> None:
    """Verdict confirmation widget — matches the visual hierarchy of the analysis panel."""
    msg_id    = email["id"]
    predicted = email["status"]
    subject   = email.get("subject", "")
    sender_em = email.get("sender_email", "")

    existing = st.session_state.feedback_by_id.get(msg_id)

    st.markdown(
        "<div class='lm-feedback-card'>"
        "<div class='lm-section-hdr'>Confirm this result</div>"
        "<div class='lm-feedback-sub'>Help improve future detections by confirming "
        "whether this message is safe or phishing.</div>"
        + ("<div class='lm-feedback-confirm'>Feedback saved.</div>" if existing else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    if not existing:
        fb_l, fb_r = st.columns(2, gap="small")
        with fb_l:
            st.button("Mark as Safe", key=f"fb_{msg_id}_safe",
                      on_click=_submit_feedback,
                      args=(msg_id, predicted, "Safe", subject, sender_em),
                      use_container_width=True)
        with fb_r:
            st.button("Mark as Phishing", key=f"fb_{msg_id}_phish",
                      on_click=_submit_feedback,
                      args=(msg_id, predicted, "Likely Phishing", subject, sender_em),
                      use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Analysis panel  (column 4 — panel)
# ─────────────────────────────────────────────────────────────────────────────

def render_analysis_panel(email: dict | None) -> None:
    st.markdown("<div class='lm-col-panel'></div>", unsafe_allow_html=True)
    if not st.session_state.panel_open:
        return

    dot_color = RISK[email["status"]]["border"] if email else "#27ae60"
    r = RISK[email["status"]] if email else RISK["Safe"]

    # Panel header with expand toggle
    expand_icon = "⟵ Collapse" if st.session_state.panel_wide else "⟷ Expand"
    ph_left, ph_right = st.columns([2.2, 1.8], gap="small")
    with ph_left:
        st.markdown(
            f"<div class='lm-panel-hdr'>"
            f"<span class='lm-panel-hdr-badge' style='background:{dot_color};'></span>"
            f"<span class='lm-panel-hdr-title'>Security Analysis</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with ph_right:
        st.button(expand_icon, key="panel-expand", on_click=toggle_panel_wide,
                  use_container_width=True)

    if not email:
        st.markdown(
            "<div class='lm-panel-body' style='color:var(--muted-soft);font-size:0.82rem;'>"
            "Select a message to view analysis.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("<div class='lm-panel-body'>", unsafe_allow_html=True)

    pct   = email["confidence_pct"]
    band  = email["confidence_band"]
    color = CONF_CLR[band]
    e_status = email["status"]
    st.markdown(
        f"<div class='lm-verdict' style='background:{r['bg']};"
        f"border-color:{r['border']};color:{r['text']};'>"
        f"<div class='lm-verdict-label'>{e_status}</div>"
        f"<div class='lm-verdict-tagline'>{TAGLINE[e_status]}</div>"
        + conf_bar(pct, band, color)
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='lm-card'>"
        "<div class='lm-section-hdr'>Why this verdict</div>"
        + reasons_html(email["top_reasons"])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='lm-card'>"
        "<div class='lm-section-hdr'>What to do next</div>"
        + actions_html(email["recommended_actions"])
        + "</div>",
        unsafe_allow_html=True,
    )

    # Consequences awareness nudge — only shown for non-Safe emails
    if email.get("status") != "Safe":
        st.markdown(
            "<div style='font-size:0.76rem;color:var(--muted);line-height:1.55;"
            "padding:0.55rem 0.65rem;margin:0.5rem 0 0.2rem;"
            "border-left:3px solid #c0392b;background:rgba(192,57,43,0.06);"
            "border-radius:0 4px 4px 0;'>"
            "Phishing scams can lead to identity theft, financial loss, and account takeover. "
            "<a href='https://consumer.ftc.gov/articles/what-do-if-you-were-scammed' "
            "target='_blank' style='color:#c0392b;font-weight:600;'>Learn what's at stake and how to protect yourself →</a>"
            "</div>",
            unsafe_allow_html=True,
        )

    # Report Phishing — only shown for non-Safe emails
    if email.get("status") != "Safe":
        _e_subject   = email.get("subject", "Suspicious message")
        _e_sender    = email.get("sender", "")
        _e_sender_em = email.get("sender_email", "")
        _e_status    = email.get("status", "")
        _e_pct       = email.get("confidence_pct", 0)
        _e_reasons   = email.get("top_reasons", [])
        _e_preview   = email.get("preview", "")
        _e_body      = " ".join(email.get("body", []))

        _reasons_text = "\n".join(f"  - {r}" for r in _e_reasons) if _e_reasons else "  - No specific signals noted."

        _report_body = f"""I am submitting this phishing report for investigation.

LUMAN AI ANALYSIS SUMMARY
--------------------------
Verdict:    {_e_status}
Confidence: {_e_pct}%

Why this was flagged:
{_reasons_text}

REPORTED MESSAGE DETAILS
--------------------------
From (display name): {_e_sender}
From (email address): {_e_sender_em}
Subject: {_e_subject}

Message preview:
{_e_preview}

Full message body:
{_e_body}

---
This report was generated by Luman AI Cyber Safety Coach.
Please investigate the sender address and any links contained in this message.
"""

        _mailto_params = urllib.parse.urlencode({
            "subject": f"Phishing Report: {_e_subject}",
            "bcc":     "spam@uce.gov",
            "body":    _report_body,
        })
        mailto_href = f"mailto:reportphishing@apwg.org?{_mailto_params}"

        st.markdown(
            "<div class='lm-card'>"
            "<div class='lm-section-hdr'>Report This Message</div>"
            "<div style='font-size:0.77rem;color:var(--muted);margin-bottom:0.6rem;line-height:1.5;'>"
            "Opens your email app with a pre-written report addressed to the "
            "Anti-Phishing Working Group (APWG). The FTC is included automatically.</div>"
            f"<a href='{mailto_href}' style='"
            "display:block;text-align:center;padding:0.45rem 0.75rem;"
            "background:#c0392b;color:#fff;border-radius:5px;font-size:0.82rem;"
            "font-weight:700;text-decoration:none;letter-spacing:0.02em;"
            "margin-bottom:0.65rem;'>📧 Report Phishing</a>"
            "<div style='font-size:0.75rem;color:var(--muted-soft);margin-bottom:0.35rem;'>"
            "Also report to a federal agency:</div>"
            "<div style='display:flex;gap:0.5rem;flex-wrap:wrap;'>"
            "<a href='https://reportfraud.ftc.gov/' target='_blank' style='"
            "font-size:0.75rem;color:var(--accent);text-decoration:none;"
            "border:1px solid var(--accent);border-radius:4px;"
            "padding:0.2rem 0.5rem;white-space:nowrap;'>FTC Report Fraud ↗</a>"
            "<a href='https://www.ic3.gov/' target='_blank' style='"
            "font-size:0.75rem;color:var(--accent);text-decoration:none;"
            "border:1px solid var(--accent);border-radius:4px;"
            "padding:0.2rem 0.5rem;white-space:nowrap;'>FBI IC3 ↗</a>"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    # Technical signals expander
    with st.expander("Technical Signals"):
        sig = email.get("technical_signals", {})
        st.markdown(
            sig_row("Urgency language",           sig.get("urgency", False))
            + sig_row("Credential request",        sig.get("credential_request", False))
            + sig_row("Sender domain mismatch",    sig.get("domain_mismatch", False))
            + sig_row("URL shortener detected",    sig.get("shortened_link", False)),
            unsafe_allow_html=True,
        )

    # Link Reputation
    with st.expander("🔗 Link Reputation"):
        _body_text  = " ".join(email.get("body", []))
        _all_text   = f"{email.get('subject', '')} {_body_text}"
        _urls       = _extract_clean_urls(_all_text)
        _sim        = email.get("simulated_link", "")
        if _sim:
            _sim_full = _sim if _sim.startswith("http") else f"https://{_sim}"
            if _sim_full not in _urls:
                _urls.insert(0, _sim_full)

        _rep_key  = f"rep_{email['id']}"
        _rep_data = st.session_state.get(_rep_key)

        if not _urls:
            st.markdown(
                "<div style='font-size:0.78rem;color:var(--muted-soft);'>"
                "No links found in this message.</div>",
                unsafe_allow_html=True,
            )
        elif _rep_data is None:
            st.markdown(
                f"<div style='font-size:0.78rem;color:var(--muted);"
                f"margin-bottom:0.45rem;line-height:1.5;'>"
                f"{len(_urls)} {'link' if len(_urls) == 1 else 'links'} found in this message.</div>",
                unsafe_allow_html=True,
            )
            if st.button("Check Links", key=f"rep-btn-{email['id']}",
                         type="primary", use_container_width=True):
                with st.spinner("Checking links…"):
                    st.session_state[_rep_key] = check_reputation(_urls).to_dict()
                st.rerun()
        else:
            st.markdown(rep_card_html(_rep_data), unsafe_allow_html=True)
            if st.button("Re-check", key=f"rep-rechk-{email['id']}",
                         use_container_width=True):
                st.session_state.pop(_rep_key, None)
                st.rerun()

    _render_feedback_section(email)

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Shared result renderer  (used by Analyze Message tab and analysis panel)
# ─────────────────────────────────────────────────────────────────────────────

def _render_result_block(result: dict) -> None:
    """Verdict block + reasons + actions + reputation card + ML note."""
    lbl   = result["label"]
    rv    = RISK[lbl]
    pct   = result["confidence_pct"]
    band  = result["confidence_band"]
    color = CONF_CLR[band]
    st.markdown(
        f"<div class='lm-verdict' style='background:{rv['bg']};"
        f"border-color:{rv['border']};color:{rv['text']};'>"
        f"<div class='lm-verdict-label'>{lbl}</div>"
        f"<div class='lm-verdict-tagline'>{TAGLINE[lbl]}</div>"
        + conf_bar(pct, band, color)
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='lm-card'>"
        "<div class='lm-section-hdr'>Why this verdict</div>"
        + reasons_html(result["top_reasons"])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='lm-card'>"
        "<div class='lm-section-hdr'>What to do next</div>"
        + actions_html(result["recommended_actions"])
        + "</div>",
        unsafe_allow_html=True,
    )

    if result.get("verdict") != "Safe":
        st.markdown(
            "<div style='font-size:0.76rem;color:var(--muted);line-height:1.55;"
            "padding:0.55rem 0.65rem;margin:0.5rem 0 0.2rem;"
            "border-left:3px solid #c0392b;background:rgba(192,57,43,0.06);"
            "border-radius:0 4px 4px 0;'>"
            "Phishing scams can lead to identity theft, financial loss, and account takeover. "
            "<a href='https://consumer.ftc.gov/articles/what-do-if-you-were-scammed' "
            "target='_blank' style='color:#c0392b;font-weight:600;'>Learn what's at stake and how to protect yourself →</a>"
            "</div>",
            unsafe_allow_html=True,
        )

    rep = result.get("reputation")
    if rep:
        st.markdown(rep_card_html(rep), unsafe_allow_html=True)
    elif result.get("virustotal"):
        st.markdown(vt_card_html(result["virustotal"]), unsafe_allow_html=True)
    note = ml_note_html(result.get("ml_signal"))
    if note:
        st.markdown(note, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Analyze Message tab
# ─────────────────────────────────────────────────────────────────────────────

def render_analyze_tab() -> None:
    _, col, _ = st.columns([1, 3, 1], gap="small")
    with col:
        st.markdown(
            "<div class='lm-analyze-title'>Analyze Message</div>"
            "<div class='lm-analyze-sub'>Paste a suspicious email or message to check "
            "for phishing patterns, risky language, and unsafe links.</div>"
            "<div class='lm-analyze-helper'>We review the full message content and any "
            "links it contains, then explain the result in plain language.</div>",
            unsafe_allow_html=True,
        )

        result = st.session_state.analyze_msg_result

        if result:
            _render_result_block(result)
            st.markdown(
                "<div style='height:1px;background:var(--line);margin:1.2rem 0 0.9rem;'></div>",
                unsafe_allow_html=True,
            )
            if st.button("← Analyze another message", key="am_clear",
                         on_click=lambda: st.session_state.update(analyze_msg_result=None),
                         use_container_width=True):
                pass
        else:
            st.text_area(
                "Message content",
                height=200,
                placeholder="Paste the full message text here…",
                key="am_body",
                label_visibility="collapsed",
            )
            body_val = st.session_state.get("am_body", "")
            if st.button("Analyze →", key="am_run", type="primary",
                         use_container_width=True, disabled=not bool(body_val.strip())):
                with st.spinner("Analyzing…"):
                    r = analyze_message(
                        body=st.session_state.get("am_body", ""),
                        sender_name=st.session_state.get("am_sname", ""),
                        sender_email=st.session_state.get("am_semail", ""),
                        subject=st.session_state.get("am_sub", ""),
                    )
                st.session_state.analyze_msg_result = r
                st.rerun()

            with st.expander("Add more context (optional)"):
                st.text_input("Subject line", key="am_sub",
                              placeholder="e.g. Your account has been suspended")
                c1, c2 = st.columns(2, gap="small")
                with c1:
                    st.text_input("Sender name", key="am_sname",
                                  placeholder="Display name")
                with c2:
                    st.text_input("Sender email", key="am_semail",
                                  placeholder="address@domain.com")


# ─────────────────────────────────────────────────────────────────────────────
# Check Link tab
# ─────────────────────────────────────────────────────────────────────────────

def render_check_link_tab() -> None:
    _, col, _ = st.columns([1, 3, 1], gap="small")
    with col:
        st.markdown(
            "<div class='lm-analyze-title'>Check Link</div>"
            "<div class='lm-analyze-sub'>Paste a link to see whether trusted security "
            "tools flag it as unsafe.</div>"
            "<div class='lm-analyze-helper'>This checks the link directly using security "
            "reputation sources. It is best for standalone URLs rather than full "
            "messages.</div>",
            unsafe_allow_html=True,
        )

        result = st.session_state.check_link_result

        if result:
            st.markdown(rep_card_html(result), unsafe_allow_html=True)
            st.markdown(
                "<div style='height:1px;background:var(--line);margin:1.2rem 0 0.9rem;'></div>",
                unsafe_allow_html=True,
            )
            if st.button("← Check another link", key="cl_clear",
                         on_click=lambda: st.session_state.update(check_link_result=None),
                         use_container_width=True):
                pass
        else:
            st.text_input(
                "URL",
                key="cl_url",
                placeholder="https://example.com  or  example.com/path",
                label_visibility="collapsed",
            )
            url_val = st.session_state.get("cl_url", "")
            if st.button("Check Link →", key="cl_run", type="primary",
                         use_container_width=True, disabled=not bool(url_val.strip())):
                raw = url_val.strip()
                if raw and not raw.startswith(("http://", "https://")):
                    raw = "https://" + raw
                with st.spinner("Checking…"):
                    rep = check_reputation([raw])
                st.session_state.check_link_result = rep.to_dict()
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    inject_styles()
    init_state()
    render_chrome()

    tab_inbox, tab_analyze, tab_checklink = st.tabs(["Inbox", "Analyze Message", "Check Link"])

    with tab_inbox:
        current_emails = get_emails(st.session_state.selected_folder)
        selected_email  = get_email(st.session_state.selected_email_id)

        if st.session_state.panel_open:
            if st.session_state.panel_wide:
                c_sb, c_list, c_read, c_panel = st.columns([0.85, 1.50, 2.10, 2.55], gap="small")
            else:
                c_sb, c_list, c_read, c_panel = st.columns([0.85, 1.50, 3.30, 1.35], gap="small")
        else:
            c_sb, c_list, c_read = st.columns([0.85, 1.60, 4.55], gap="small")
            c_panel = None

        with c_sb:
            render_sidebar()
        with c_list:
            render_email_list(current_emails)
        with c_read:
            render_email_view(selected_email)
        if c_panel:
            with c_panel:
                render_analysis_panel(selected_email)

    with tab_analyze:
        render_analyze_tab()

    with tab_checklink:
        render_check_link_tab()

    # ── Demo polling ─────────────────────────────────────────────────────────
    # While the demo is playing, tick once per second to check for due emails.
    if st.session_state.demo_playing:
        _demo_tick()
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
