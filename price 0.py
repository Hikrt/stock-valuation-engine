"""
================================================================================
  STOCK VALUATION DASHBOARD  –  Streamlit App
  Run with:  streamlit run stock_valuation_app.py
================================================================================
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass
from typing import Optional, List
import warnings
import requests
from bs4 import BeautifulSoup
import time

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Stock Valuation Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

  .main { background: #0d1117; }
  .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
  }
  .metric-label { color: #8b949e; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.25rem; }
  .metric-value { color: #e6edf3; font-size: 1.6rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
  .metric-delta-up   { color: #3fb950; font-size: 0.85rem; font-weight: 600; }
  .metric-delta-down { color: #f85149; font-size: 0.85rem; font-weight: 600; }
  .metric-delta-flat { color: #d29922; font-size: 0.85rem; font-weight: 600; }

  /* Verdict banner */
  .verdict-undervalued { background: linear-gradient(90deg,#1a3a2a,#0d2418); border-left: 4px solid #3fb950; border-radius:8px; padding:1rem 1.5rem; color:#3fb950; font-size:1.1rem; font-weight:700; margin: 1rem 0; }
  .verdict-overvalued  { background: linear-gradient(90deg,#3a1a1a,#240d0d); border-left: 4px solid #f85149; border-radius:8px; padding:1rem 1.5rem; color:#f85149; font-size:1.1rem; font-weight:700; margin: 1rem 0; }
  .verdict-fair        { background: linear-gradient(90deg,#3a2e0d,#241d00); border-left: 4px solid #d29922; border-radius:8px; padding:1rem 1.5rem; color:#d29922; font-size:1.1rem; font-weight:700; margin: 1rem 0; }

  /* Section headers */
  .section-header { color: #e6edf3; font-size: 1rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0; }

  /* Data quality badge */
  .dq-high   { background:#1a3a2a; color:#3fb950; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
  .dq-medium { background:#3a2e0d; color:#d29922; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
  .dq-low    { background:#3a1a1a; color:#f85149; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stSlider label,
  [data-testid="stSidebar"] .stNumberInput label { color: #8b949e !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.06em; }

  /* Tables */
  .dataframe { background: #161b22 !important; color: #e6edf3 !important; }

  /* Hide streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }

  /* Ticker input styling */
  .stTextInput input { background: #161b22; border: 1px solid #30363d; color: #e6edf3; font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; border-radius: 8px; }
  .stTextInput input:focus { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88,166,255,0.15); }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background: #161b22; border-radius: 8px; padding: 4px; gap: 4px; }
  .stTabs [data-baseweb="tab"] { background: transparent; color: #8b949e; border-radius: 6px; font-weight: 500; }
  .stTabs [aria-selected="true"] { background: #21262d !important; color: #e6edf3 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CURRENCY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

CURRENCY_SYMBOLS = {
    "INR": "₹", "USD": "$", "GBP": "£", "EUR": "€",
    "JPY": "¥", "CNY": "¥", "HKD": "HK$", "AUD": "A$",
    "CAD": "C$", "SGD": "S$", "KRW": "₩", "BRL": "R$",
}

def fmt_large(val: float, currency: str) -> str:
    sym = CURRENCY_SYMBOLS.get(currency, currency + " ")
    if currency == "INR":
        cr = val / 1e7
        return f"₹{cr/1e5:.2f}L Cr" if cr >= 1e5 else f"₹{cr:,.0f} Cr"
    return f"{sym}{val/1e9:.2f}B"

def sym(currency: str) -> str:
    return CURRENCY_SYMBOLS.get(currency, currency + " ")


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValuationConfig:
    wacc: float            = 0.10
    terminal_growth: float = 0.025
    dcf_years: int         = 10
    near_growth: float     = 0.10
    mid_growth: float      = 0.06
    required_return: float = 0.09
    dividend_growth: float = 0.04
    sector_pe:       float = 20.0
    sector_pb:       float = 3.0
    sector_ps:       float = 2.0
    sector_evebitda: float = 12.0
    sector_evrev:    float = 2.5
    sector_pfcf:     float = 20.0
    sector_peg:      float = 1.5
    margin_of_safety: float = 0.20


# ─────────────────────────────────────────────────────────────────────────────
#  COMPETITOR AUTO-DETECTION
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_competitors_yfinance(ticker: str, max_peers: int = 5) -> List[str]:
    """
    Strategy 1 – yfinance recommended_symbols (fastest).
    Strategy 2 – Find peers sharing the same GICS sector + industry
                 from a curated index map.
    Strategy 3 – Scrape Yahoo Finance 'Similar' section as fallback.
    """
    tk = yf.Ticker(ticker)

    # Strategy 1: yfinance built-in
    try:
        recs = tk.recommendations
        # some versions return a "similar" dict
        pass
    except Exception:
        pass

    # Most reliable: use Yahoo Finance's own "Similar Companies" via
    # their query2 endpoint (no scraping needed, same domain as yfinance)
    try:
        url = (f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/"
               f"{ticker.upper()}")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            recs = (data.get("finance", {})
                        .get("result", [{}])[0]
                        .get("recommendedSymbols", []))
            peers = [r["symbol"] for r in recs[:max_peers]]
            if peers:
                return peers
    except Exception:
        pass

    # Fallback: find tickers in the same industry from a broad index
    try:
        info = tk.info
        sector   = info.get("sector", "")
        industry = info.get("industry", "")
        exchange = info.get("exchange", "")

        # Use Yahoo Finance screener API
        url2 = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
        params = {"formatted": "false", "count": 25, "scrIds": "most_actives"}
        resp2  = requests.get(url2, headers={"User-Agent": "Mozilla/5.0"},
                              params=params, timeout=8)
        if resp2.status_code == 200:
            quotes = (resp2.json()
                          .get("finance", {})
                          .get("result", [{}])[0]
                          .get("quotes", []))
            same_sector = [
                q["symbol"] for q in quotes
                if q.get("sector") == sector
                and q["symbol"] != ticker.upper()
            ][:max_peers]
            if same_sector:
                return same_sector
    except Exception:
        pass

    return []


@st.cache_data(ttl=3600, show_spinner=False)
def get_competitors_scrape(ticker: str, max_peers: int = 5) -> List[str]:
    """
    Scrape Yahoo Finance 'People also watch' / similar companies section.
    """
    try:
        url = f"https://finance.yahoo.com/quote/{ticker.upper()}"
        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0 Safari/537.36"),
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for "People also watch" section symbols
        symbols = []
        for tag in soup.find_all("a", {"data-test": "quoteLink"}):
            sym_text = tag.text.strip()
            if sym_text and sym_text != ticker.upper() and len(sym_text) <= 12:
                symbols.append(sym_text)
        return list(dict.fromkeys(symbols))[:max_peers]  # deduplicate, keep order
    except Exception:
        return []


def find_competitors(ticker: str, max_peers: int = 5) -> List[str]:
    """Try multiple strategies; merge results; validate each peer via yfinance."""
    # Try API first (fastest), then scraping
    peers = get_competitors_yfinance(ticker, max_peers * 2)
    if len(peers) < 2:
        peers += get_competitors_scrape(ticker, max_peers * 2)

    # Remove duplicates, remove self
    seen, clean = set(), []
    for p in peers:
        if p.upper() != ticker.upper() and p.upper() not in seen:
            seen.add(p.upper())
            clean.append(p.upper())

    # Validate each peer has a real price
    valid = []
    for p in clean[:max_peers + 3]:
        try:
            info = yf.Ticker(p).info
            if info.get("currentPrice") or info.get("regularMarketPrice"):
                valid.append(p)
        except Exception:
            pass
        if len(valid) >= max_peers:
            break

    return valid


# ─────────────────────────────────────────────────────────────────────────────
#  STOCK DATA CLASS
# ─────────────────────────────────────────────────────────────────────────────

class StockData:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self._tk   = yf.Ticker(self.ticker)
        self.info  = self._tk.info or {}

        if not self.info or (
            self.info.get("regularMarketPrice") is None and
            self.info.get("currentPrice") is None and
            self.info.get("previousClose") is None
        ):
            raise ValueError(f"'{self.ticker}' not found on Yahoo Finance.")

        self.currency        = self.info.get("currency", "USD")
        self.currency_symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency + " ")

        self._load_financials()
        self._stmt_scale = self._compute_stmt_scale()

    def _load_financials(self):
        try:
            self.income_stmt   = self._tk.financials
            self.balance_sheet = self._tk.balance_sheet
            self.cashflow      = self._tk.cashflow
        except Exception:
            self.income_stmt = self.balance_sheet = self.cashflow = pd.DataFrame()

    def _stmt_row_raw(self, stmt, *keys):
        for k in keys:
            if k in stmt.index:
                v = stmt.loc[k].dropna()
                if not v.empty:
                    return float(v.iloc[0])
        return None

    def _compute_stmt_scale(self) -> float:
        """
        Detect unit mismatch between financial statements and ticker.info.

        ROOT CAUSE for INFY.NS and similar NSE tickers:
          yfinance's info["freeCashflow"] and info["ebitda"] sometimes return
          USD values for INR-listed stocks, OR Crore-unit values without the
          ×10^7 multiplier. The cashflow/income statements, however, are always
          in full local-currency units. We compute a correction factor by
          comparing info["netIncomeToCommon"] (always reliable, full INR) against
          the raw Net Income row from the statement.
        """
        import math

        # ── Primary anchor: netIncomeToCommon from info ───────────────────────
        # This field is always in correct local currency (full units, not Crore).
        ni_info = self._get("netIncomeToCommon")
        if ni_info and float(ni_info) > 0:
            ni_info = float(ni_info)
        else:
            # Fallback: derive from trailingEps × sharesOutstanding
            eps    = (self._get("trailingEps") or
                      self._get("epsTrailingTwelveMonths"))
            shares = (self._get("sharesOutstanding") or
                      self._get("impliedSharesOutstanding"))
            if not eps or not shares or float(eps) <= 0 or float(shares) <= 0:
                return 1.0
            ni_info = float(eps) * float(shares)

        # ── Raw Net Income from statement ─────────────────────────────────────
        ni_stmt = self._stmt_row_raw(
            self.income_stmt,
            "Net Income", "Net Income Common Stockholders",
            "Net Income Applicable To Common Shares",
            "Net Income Including Noncontrolling Interests",
        )
        if ni_stmt is None or ni_stmt <= 0:
            return 1.0

        ratio = ni_stmt / ni_info   # ideal = 1.0 when units match

        # ── Find nearest power-of-10 scale factor ─────────────────────────────
        power = round(math.log10(ratio))
        scale = 10.0 ** power

        # Validate: after dividing by scale, statement ≈ info (within 50%)
        if 0.5 <= (ni_stmt / scale) / ni_info <= 2.0:
            return scale

        # Try ±1 power if primary doesn't fit
        for adj in [-1, 1, -2, 2]:
            adj_scale = 10.0 ** (power + adj)
            if adj_scale > 0 and 0.5 <= (ni_stmt / adj_scale) / ni_info <= 2.0:
                return adj_scale

        return 1.0   # no mismatch detected — statements already in correct units

    def _stmt_row(self, stmt, *keys):
        v = self._stmt_row_raw(stmt, *keys)
        return v / self._stmt_scale if v is not None else None

    def _get(self, key, default=None):
        return self.info.get(key, default)

    @property
    def price(self) -> float:
        return float(self._get("currentPrice") or
                     self._get("regularMarketPrice") or
                     self._get("previousClose") or 0.0)

    @property
    def shares(self) -> float:
        return float(self._get("sharesOutstanding") or
                     self._get("impliedSharesOutstanding") or 1)

    @property
    def market_cap(self) -> float:
        mc = self._get("marketCap")
        return float(mc) if mc else self.price * self.shares

    @property
    def revenue(self) -> Optional[float]:
        """
        Total revenue. Prefers statement (scaled) for international tickers,
        falls back to info["totalRevenue"] which is usually reliable.
        """
        # Try statement first (correctly scaled)
        v_stmt = self._stmt_row(self.income_stmt, "Total Revenue", "Revenue", "Net Revenue")
        if v_stmt and v_stmt > 0:
            # Cross-validate: if info also has it, they should be within 30%
            v_info = self._get("totalRevenue")
            if v_info and float(v_info) > 0:
                ratio = v_stmt / float(v_info)
                if 0.7 <= ratio <= 1.3:
                    return v_stmt          # statement and info agree ✓
                else:
                    return float(v_info)   # info is more trusted when they diverge
            return v_stmt
        # Fall back to info
        v = self._get("totalRevenue")
        return float(v) if v else None

    @property
    def ebitda(self) -> Optional[float]:
        """
        EBITDA computed from financial statements (scaled), not info["ebitda"].

        CRITICAL FIX: info["ebitda"] has the same unit-mismatch issue as
        info["freeCashflow"] for NSE-listed stocks. Computing from statements
        (after scale correction) is the reliable path.
        EBITDA = Operating Income (EBIT) + Depreciation & Amortization.
        """
        # ── Try direct EBITDA row from income statement ───────────────────────
        v = self._stmt_row(self.income_stmt, "EBITDA", "Normalized EBITDA")
        if v and v > 0:
            return v

        # ── Compute: EBITDA = EBIT + D&A ─────────────────────────────────────
        ebit = self._stmt_row(
            self.income_stmt,
            "EBIT", "Operating Income", "Operating Income Or Loss",
            "Total Operating Income As Reported",
        )
        da = self._stmt_row(
            self.cashflow,
            "Depreciation And Amortization",
            "Depreciation Amortization Depletion",
            "Depreciation",
        )
        if ebit is not None and da is not None:
            return ebit + abs(da)

        # ── If only EBIT available, estimate D&A from revenue ────────────────
        if ebit is not None and ebit > 0:
            rev = self.revenue
            da_estimate = rev * 0.04 if rev else 0   # ~4% D&A/revenue fallback
            return ebit + da_estimate

        # ── Last resort: info field, validated against revenue margin ─────────
        v = self._get("ebitda")
        if v and float(v) > 0:
            rev = self.revenue
            if rev and float(rev) > 0:
                margin = float(v) / rev
                if 0.05 <= margin <= 0.80:   # EBITDA margin must be 5–80%
                    return float(v)
        return None

    @property
    def net_income(self) -> Optional[float]:
        v = self._get("netIncomeToCommon")
        if v: return float(v)
        return self._stmt_row(self.income_stmt,
                              "Net Income", "Net Income Common Stockholders")

    @property
    def eps(self) -> Optional[float]:
        for k in ("trailingEps", "epsTrailingTwelveMonths", "epsForward", "forwardEps"):
            v = self._get(k)
            if v is not None and float(v) != 0:
                return float(v)
        ni = self.net_income
        return ni / self.shares if ni and self.shares else None

    @property
    def fcf(self) -> Optional[float]:
        """
        Free Cash Flow = Operating CF − Capital Expenditure.

        CRITICAL FIX: info["freeCashflow"] is intentionally NOT used as the
        primary source. For NSE-listed stocks (e.g. INFY.NS, TCS.NS), yfinance
        sometimes returns this field in USD instead of INR, causing DCF values
        to be ~83× too small. The cashflow statement is always in local currency
        and is corrected by _stmt_scale, so it is the ground truth.
        """
        # ── Primary: compute from cashflow statement (always in local currency) ─
        ocf = self._stmt_row(
            self.cashflow,
            "Operating Cash Flow", "Cash From Operations",
            "Total Cash From Operating Activities",
            "Net Cash Provided By Operating Activities",
        )
        capex = self._stmt_row(
            self.cashflow,
            "Capital Expenditure", "Capital Expenditures",
            "Purchase Of Property Plant And Equipment",
            "Capital Expenditures Reported",
        )
        if ocf is not None and capex is not None:
            result = ocf + capex   # CapEx is stored negative in yfinance
            if result > 0:
                return result
            # If negative FCF, still return it — callers check for > 0
            if ocf > 0:
                return result

        # ── If only OCF available, estimate FCF conservatively ───────────────
        if ocf is not None and ocf > 0:
            # Use 85% of OCF as a conservative FCF estimate
            return ocf * 0.85

        # ── Last resort: info field, validated against revenue ────────────────
        # Only trusted if FCF margin is in a realistic 5–60% range
        v = self._get("freeCashflow")
        if v and float(v) > 0:
            rev = self._get("totalRevenue")
            if rev and float(rev) > 0:
                if 0.05 <= float(v) / float(rev) <= 0.60:
                    return float(v)
            else:
                return float(v)   # no revenue to validate against, use as-is
        return None

    @property
    def bvps(self) -> Optional[float]:
        v = self._get("bookValue")
        return float(v) if v else None

    @property
    def total_debt(self) -> float:
        return float(self._get("totalDebt") or 0.0)

    @property
    def cash(self) -> float:
        return float(self._get("totalCash") or 0.0)

    @property
    def dividends_per_share(self) -> float:
        return float(self._get("dividendRate") or
                     self._get("trailingAnnualDividendRate") or 0.0)

    @property
    def total_assets(self) -> Optional[float]:
        return self._stmt_row(self.balance_sheet, "Total Assets")

    @property
    def total_liabilities(self) -> Optional[float]:
        return self._stmt_row(self.balance_sheet,
                              "Total Liabilities Net Minority Interest",
                              "Total Liabilities")

    @property
    def growth_rate(self) -> float:
        for k in ("earningsGrowth", "revenueGrowth", "earningsQuarterlyGrowth"):
            v = self._get(k)
            if v is not None:
                val = float(v)
                if -1.0 < val < 5.0:
                    return val
        if not self.income_stmt.empty:
            try:
                for k in ("Total Revenue", "Revenue"):
                    if k in self.income_stmt.index:
                        rows = self.income_stmt.loc[k].dropna()
                        if len(rows) >= 2:
                            cagr = (float(rows.iloc[0]) / float(rows.iloc[-1])) \
                                   ** (1/(len(rows)-1)) - 1
                            if -0.5 < cagr < 3.0:
                                return cagr
            except Exception:
                pass
        return 0.08

    @property
    def beta(self) -> float:
        v = self._get("beta")
        return float(v) if v else 1.0

    @property
    def enterprise_value(self) -> float:
        ev = self._get("enterpriseValue")
        if ev: return float(ev)
        return self.market_cap + self.total_debt - self.cash

    @property
    def price_history(self) -> pd.DataFrame:
        try:
            return self._tk.history(period="1y")
        except Exception:
            return pd.DataFrame()

    def quality_report(self) -> dict:
        fields = {
            "price": self.price, "eps": self.eps, "fcf": self.fcf,
            "revenue": self.revenue, "ebitda": self.ebitda,
            "net_income": self.net_income, "bvps": self.bvps,
            "dividends": self.dividends_per_share, "growth_rate": self.growth_rate,
        }
        missing = [k for k, v in fields.items() if v is None or v == 0.0]
        present = [k for k, v in fields.items() if v is not None and v != 0.0]
        sf = self._stmt_scale

        # BUG 3 FIX: format scale factor properly for all magnitudes
        if sf == 1.0:
            scale_display = None          # no correction — don't show warning
        elif sf >= 1:
            scale_display = f"×{sf:,.0f}"
        else:
            scale_display = f"÷{1/sf:,.0f}"   # e.g. 0.1 → "÷10"

        return {
            "score_pct": round(len(present) / len(fields) * 100, 0),
            "present": present,
            "missing": missing,
            "scale_factor": sf,
            "scale_display": scale_display,   # human-readable, never shows "×0"
        }


# ─────────────────────────────────────────────────────────────────────────────
#  ALL VALUATION MODELS
# ─────────────────────────────────────────────────────────────────────────────

MODEL_WEIGHTS = {
    "DCF (Two-Stage)":     0.25,
    "DDM (Gordon Growth)": 0.08,
    "Graham Number":       0.10,
    "P/E Relative":        0.10,
    "P/B Relative":        0.07,
    "PEG":                 0.07,
    "EV/EBITDA":           0.10,
    "EV/Revenue":          0.05,
    "Price/Sales":         0.05,
    "Price/FCF":           0.08,
    "Residual Income (RI)":0.05,
    "Asset-Based NAV":     0.00,
}

def run_all_models(data: StockData, cfg: ValuationConfig) -> list:
    results = []

    # DCF
    fcf = data.fcf
    if fcf and fcf > 0:
        pv, cf = 0.0, fcf
        for yr in range(1, cfg.dcf_years + 1):
            g = cfg.near_growth if yr <= 5 else cfg.mid_growth
            cf *= (1 + g); pv += cf / (1 + cfg.wacc) ** yr
        tv = cf*(1+cfg.terminal_growth)/(cfg.wacc-cfg.terminal_growth)
        pv_tv = tv / (1+cfg.wacc)**cfg.dcf_years
        iv = (pv + pv_tv + data.cash - data.total_debt) / data.shares
        results.append({"method":"DCF (Two-Stage)","intrinsic_value":round(iv,2),
                         "description":"10-yr FCF forecast + Gordon Growth terminal value"})
    else:
        results.append({"method":"DCF (Two-Stage)","intrinsic_value":None,
                         "error":"Negative/missing FCF","description":"10-yr FCF forecast"})

    # DDM
    dps = data.dividends_per_share
    if dps > 0 and cfg.required_return > cfg.dividend_growth:
        d1 = dps*(1+cfg.dividend_growth)
        results.append({"method":"DDM (Gordon Growth)","intrinsic_value":round(d1/(cfg.required_return-cfg.dividend_growth),2),
                         "description":"D1 / (r − g) — for dividend-paying stocks"})
    else:
        results.append({"method":"DDM (Gordon Growth)","intrinsic_value":None,
                         "error":"No dividends or r≤g","description":"D1 / (r − g)"})

    # Graham Number
    eps = data.eps; bvps = data.bvps
    if eps and bvps and eps > 0 and bvps > 0:
        results.append({"method":"Graham Number","intrinsic_value":round(np.sqrt(22.5*eps*bvps),2),
                         "description":"√(22.5 × EPS × BVPS) — Graham's conservative floor"})
    else:
        results.append({"method":"Graham Number","intrinsic_value":None,
                         "error":"Needs positive EPS + BVPS","description":"Graham's formula"})

    # P/E
    if eps and eps > 0:
        pe_cur = data._get("trailingPE") or (data.price / eps)
        results.append({"method":"P/E Relative","intrinsic_value":round(eps*cfg.sector_pe,2),
                         "current_multiple":round(pe_cur,2),"benchmark":cfg.sector_pe,
                         "description":f"EPS × sector P/E benchmark ({cfg.sector_pe}x)"})
    else:
        results.append({"method":"P/E Relative","intrinsic_value":None,
                         "error":"Non-positive EPS","description":"EPS × sector P/E"})

    # P/B
    if bvps and bvps > 0:
        results.append({"method":"P/B Relative","intrinsic_value":round(bvps*cfg.sector_pb,2),
                         "current_multiple":round(data.price/bvps,2),"benchmark":cfg.sector_pb,
                         "description":f"BVPS × sector P/B benchmark ({cfg.sector_pb}x)"})
    else:
        results.append({"method":"P/B Relative","intrinsic_value":None,
                         "error":"Non-positive BVPS","description":"BVPS × sector P/B"})

    # PEG
    g_pct = data.growth_rate * 100
    if eps and eps > 0 and g_pct > 0:
        fair_pe = cfg.sector_peg * g_pct
        results.append({"method":"PEG","intrinsic_value":round(fair_pe*eps,2),
                         "current_multiple":round((data.price/eps)/g_pct,2),"benchmark":cfg.sector_peg,
                         "description":f"PEG-adjusted P/E (benchmark PEG {cfg.sector_peg})"})
    else:
        results.append({"method":"PEG","intrinsic_value":None,
                         "error":"Non-positive EPS or growth","description":"PEG-adjusted valuation"})

    # EV/EBITDA
    ebitda = data.ebitda
    if ebitda and ebitda > 0:
        ev_cur = data.enterprise_value / ebitda
        fair_ev = cfg.sector_evebitda * ebitda
        results.append({"method":"EV/EBITDA","intrinsic_value":round((fair_ev-data.total_debt+data.cash)/data.shares,2),
                         "current_multiple":round(ev_cur,2),"benchmark":cfg.sector_evebitda,
                         "description":f"Enterprise value relative (benchmark {cfg.sector_evebitda}x)"})
    else:
        results.append({"method":"EV/EBITDA","intrinsic_value":None,
                         "error":"Negative/missing EBITDA","description":"EV/EBITDA relative"})

    # EV/Revenue
    rev = data.revenue
    if rev and rev > 0:
        ev_rev = data.enterprise_value / rev
        fair_ev = cfg.sector_evrev * rev
        results.append({"method":"EV/Revenue","intrinsic_value":round((fair_ev-data.total_debt+data.cash)/data.shares,2),
                         "current_multiple":round(ev_rev,2),"benchmark":cfg.sector_evrev,
                         "description":f"EV/Revenue relative (benchmark {cfg.sector_evrev}x)"})
    else:
        results.append({"method":"EV/Revenue","intrinsic_value":None,
                         "error":"Missing revenue","description":"EV/Revenue relative"})

    # P/S
    if rev and rev > 0:
        rps = rev / data.shares
        results.append({"method":"Price/Sales","intrinsic_value":round(cfg.sector_ps*rps,2),
                         "current_multiple":round(data.price/rps,2),"benchmark":cfg.sector_ps,
                         "description":f"Revenue/share × sector P/S ({cfg.sector_ps}x)"})
    else:
        results.append({"method":"Price/Sales","intrinsic_value":None,
                         "error":"Missing revenue","description":"Price/Sales relative"})

    # P/FCF
    if fcf and fcf > 0:
        fcfps = fcf / data.shares
        results.append({"method":"Price/FCF","intrinsic_value":round(cfg.sector_pfcf*fcfps,2),
                         "current_multiple":round(data.price/fcfps,2),"benchmark":cfg.sector_pfcf,
                         "description":f"FCF/share × sector P/FCF ({cfg.sector_pfcf}x)"})
    else:
        results.append({"method":"Price/FCF","intrinsic_value":None,
                         "error":"Negative/missing FCF","description":"Price/FCF relative"})

    # Residual Income
    if eps and bvps and bvps > 0:
        pv_ri, cb, ce = 0.0, bvps, eps
        for i in range(cfg.dcf_years):
            ri = ce - cfg.required_return * cb
            pv_ri += ri / (1+cfg.required_return)**(i+1)
            cb += ce; ce *= (1+data.growth_rate)
        results.append({"method":"Residual Income (RI)","intrinsic_value":round(bvps+pv_ri,2),
                         "description":"BVPS + PV of future excess returns (EBO model)"})
    else:
        results.append({"method":"Residual Income (RI)","intrinsic_value":None,
                         "error":"Needs positive BVPS + EPS","description":"EBO residual income"})

    # NAV
    assets = data.total_assets; liabs = data.total_liabilities
    if assets and liabs:
        results.append({"method":"Asset-Based NAV","intrinsic_value":round((assets-liabs)/data.shares,2),
                         "description":"(Total Assets − Liabilities) / Shares — best for banks/REITs"})
    else:
        results.append({"method":"Asset-Based NAV","intrinsic_value":None,
                         "error":"Balance sheet unavailable","description":"Net asset value"})

    # Reverse DCF — special (no intrinsic_value)
    if fcf and fcf > 0:
        target_ev = data.market_cap + data.total_debt - data.cash
        lo, hi = -0.5, 2.0
        for _ in range(80):
            mid = (lo+hi)/2; pv, cf2 = 0.0, fcf
            for yr in range(1,11):
                cf2 *= (1+mid); pv += cf2/(1+cfg.wacc)**yr
            pv += (cf2*(1+cfg.terminal_growth)/(cfg.wacc-cfg.terminal_growth))/(1+cfg.wacc)**10
            lo, hi = (lo,mid) if pv > target_ev else (mid,hi)
        results.append({"method":"Reverse DCF","implied_growth":round(mid,4),
                         "description":f"Market prices in {mid*100:.1f}%/yr FCF growth for 10 yrs"})
    else:
        results.append({"method":"Reverse DCF","implied_growth":None,
                         "description":"Implied FCF growth from current price"})

    return results


def compute_composite(models: list, price: float, cfg: ValuationConfig):
    vals, wts = [], []
    for m in models:
        iv = m.get("intrinsic_value")
        if iv is not None and m.get("method") != "Reverse DCF":
            w = MODEL_WEIGHTS.get(m["method"], 0.05)
            vals.append(iv); wts.append(w)
    if not vals:
        return None, None, None
    total_w = sum(wts)
    composite = sum(v*w for v,w in zip(vals,wts)) / total_w if total_w > 0 else float(np.mean(vals))
    mos = composite * (1 - cfg.margin_of_safety)
    upside = (composite / price - 1) * 100
    return round(composite,2), round(mos,2), round(upside,2)


# ─────────────────────────────────────────────────────────────────────────────
#  CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG    = "#0d1117"
DARK_PAPER = "#161b22"
GRID_COLOR = "#21262d"
TEXT_COLOR = "#8b949e"
LINE_COLOR = "#e6edf3"

def chart_defaults():
    return dict(
        plot_bgcolor=DARK_BG, paper_bgcolor=DARK_PAPER,
        font=dict(family="Space Grotesk", color=TEXT_COLOR, size=12),
        xaxis=dict(gridcolor=GRID_COLOR, showline=False, color=TEXT_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, showline=False, color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)),
    )

def chart_valuation_waterfall(models: list, price: float, composite: float,
                               currency: str) -> go.Figure:
    s = sym(currency)
    methods, values, colors = [], [], []
    for m in models:
        iv = m.get("intrinsic_value")
        if iv is None or m.get("method") == "Reverse DCF":
            continue
        methods.append(m["method"])
        values.append(iv)
        pct = (iv/price - 1)*100
        colors.append("#3fb950" if pct > 0 else "#f85149")

    # Sort by value
    paired = sorted(zip(values, methods, colors), key=lambda x: x[0])
    values, methods, colors = zip(*paired) if paired else ([], [], [])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(values), y=list(methods), orientation="h",
        marker=dict(color=list(colors), opacity=0.85,
                    line=dict(color="rgba(0,0,0,0)")),
        text=[f"{s}{v:,.2f}" for v in values],
        textposition="outside", textfont=dict(color=LINE_COLOR, size=11),
        hovertemplate="<b>%{y}</b><br>Fair Value: %{x:,.2f}<extra></extra>",
    ))
    # Current price line
    fig.add_vline(x=price, line=dict(color="#58a6ff", dash="dash", width=2))
    fig.add_annotation(x=price, y=len(methods)-0.5,
                       text=f"  Current: {s}{price:,.2f}",
                       showarrow=False, font=dict(color="#58a6ff", size=11))
    # Composite line
    if composite:
        fig.add_vline(x=composite, line=dict(color="#d29922", dash="dot", width=2))
        fig.add_annotation(x=composite, y=-0.7,
                           text=f"  Composite: {s}{composite:,.2f}",
                           showarrow=False, font=dict(color="#d29922", size=11))

    fig.update_layout(**chart_defaults(),
                      title=dict(text="Fair Value by Model", font=dict(size=14, color=LINE_COLOR)),
                      height=max(350, len(methods)*42 + 80),
                      xaxis_title="Fair Value per Share",
                      bargap=0.3)
    return fig


def chart_price_history(data: StockData) -> go.Figure:
    hist = data.price_history
    if hist.empty:
        return go.Figure()
    s = sym(data.currency)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode="lines", name="Price",
        line=dict(color="#58a6ff", width=2),
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.07)",
        hovertemplate=f"{s}%{{y:,.2f}}<extra></extra>",
    ))
    fig.update_layout(**chart_defaults(),
                      title=dict(text="12-Month Price History", font=dict(size=14, color=LINE_COLOR)),
                      height=280, showlegend=False)
    return fig


def chart_multiples_radar(data: StockData, cfg: ValuationConfig) -> go.Figure:
    """Spider chart: current multiples vs sector benchmarks."""
    eps = data.eps or 1
    bvps = data.bvps or 1
    rev = data.revenue or 1
    ebitda = data.ebitda or 1

    metrics = ["P/E", "P/B", "P/S", "EV/EBITDA", "P/FCF"]
    current = [
        (data.price / eps) / cfg.sector_pe if eps > 0 else 0,
        (data.price / bvps) / cfg.sector_pb if bvps > 0 else 0,
        (data.price / (rev / data.shares)) / cfg.sector_ps if rev > 0 else 0,
        (data.enterprise_value / ebitda) / cfg.sector_evebitda if ebitda > 0 else 0,
        (data.price / (data.fcf / data.shares)) / cfg.sector_pfcf
            if data.fcf and data.fcf > 0 else 0,
    ]
    # current values are expressed as ratio to sector benchmark (1.0 = fair)
    fair = [1.0] * len(metrics)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=current + [current[0]], theta=metrics + [metrics[0]],
                                   fill="toself", name="Current",
                                   fillcolor="rgba(88,166,255,0.15)",
                                   line=dict(color="#58a6ff", width=2)))
    fig.add_trace(go.Scatterpolar(r=fair + [fair[0]], theta=metrics + [metrics[0]],
                                   fill="toself", name="Sector Fair",
                                   fillcolor="rgba(63,185,80,0.1)",
                                   line=dict(color="#3fb950", width=2, dash="dot")))
    fig.update_layout(
        polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(visible=True, color=TEXT_COLOR, gridcolor=GRID_COLOR),
            angularaxis=dict(color=LINE_COLOR),
        ),
        plot_bgcolor=DARK_BG, paper_bgcolor=DARK_PAPER,
        font=dict(family="Space Grotesk", color=TEXT_COLOR),
        title=dict(text="Multiples vs Sector (1.0 = fair value)", font=dict(size=14, color=LINE_COLOR)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)),
        margin=dict(l=40, r=40, t=50, b=20),
        height=320,
    )
    return fig


def chart_dcf_sensitivity(data: StockData, cfg: ValuationConfig) -> go.Figure:
    """WACC × terminal growth heatmap."""
    fcf = data.fcf
    if not fcf or fcf <= 0:
        return go.Figure()

    waccs = [0.08, 0.09, 0.10, 0.11, 0.12, 0.13]
    tgrs  = [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]
    z, hover = [], []

    for w in waccs:
        row, hr = [], []
        for tg in tgrs:
            if w <= tg:
                row.append(None); hr.append("Invalid"); continue
            pv, cf = 0.0, fcf
            for yr in range(1, 11):
                g = cfg.near_growth if yr<=5 else cfg.mid_growth
                cf *= (1+g); pv += cf/(1+w)**yr
            tv = cf*(1+tg)/(w-tg)
            pv_tv = tv/(1+w)**10
            iv = (pv + pv_tv + data.cash - data.total_debt) / data.shares
            row.append(round(iv,2))
            hr.append(f"WACC={w*100:.0f}%  TG={tg*100:.1f}%<br>Fair Value = {sym(data.currency)}{iv:,.2f}")
        z.append(row); hover.append(hr)

    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{t*100:.1f}%" for t in tgrs],
        y=[f"{w*100:.0f}%" for w in waccs],
        colorscale=[[0,"#f85149"],[0.5,"#d29922"],[1,"#3fb950"]],
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
        text=[[f"{sym(data.currency)}{v:,.0f}" if v else "" for v in row] for row in z],
        texttemplate="%{text}", textfont=dict(size=10, color="white"),
        colorbar=dict(tickfont=dict(color=TEXT_COLOR), title=dict(text="Fair Value", font=dict(color=TEXT_COLOR))),
    ))
    fig.update_layout(
        **chart_defaults(),
        title=dict(text="DCF Sensitivity: WACC × Terminal Growth Rate", font=dict(size=14, color=LINE_COLOR)),
        xaxis_title="Terminal Growth Rate",
        yaxis_title="WACC",
        height=320,
    )
    return fig


def chart_peer_comparison(peer_results: list, metric: str = "composite_fair_value") -> go.Figure:
    tickers = [r["ticker"] for r in peer_results if not r.get("error")]
    prices  = [r["current_price"] for r in peer_results if not r.get("error")]
    fvs     = [r.get("composite_fair_value") or r["current_price"] for r in peer_results if not r.get("error")]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current Price", x=tickers, y=prices,
                         marker=dict(color="#58a6ff", opacity=0.8), text=[f"{p:,.0f}" for p in prices],
                         textposition="outside", textfont=dict(color=LINE_COLOR, size=11)))
    fig.add_trace(go.Bar(name="Fair Value", x=tickers, y=fvs,
                         marker=dict(color="#3fb950", opacity=0.8), text=[f"{v:,.0f}" for v in fvs],
                         textposition="outside", textfont=dict(color=LINE_COLOR, size=11)))
    fig.update_layout(**chart_defaults(),
                      title=dict(text="Price vs Fair Value — Peer Comparison", font=dict(size=14, color=LINE_COLOR)),
                      barmode="group", height=350, bargap=0.15, bargroupgap=0.05)
    return fig


def chart_financials(data: StockData) -> go.Figure:
    """Revenue, Net Income, FCF trend."""
    if data.income_stmt.empty:
        return go.Figure()

    years, revs, nis, fcfs = [], [], [], []
    try:
        for col in data.income_stmt.columns:
            yr = str(col)[:4]
            r = data._stmt_row_raw(data.income_stmt, "Total Revenue", "Revenue")
            ni = data._stmt_row_raw(data.income_stmt, "Net Income",
                                     "Net Income Common Stockholders")
            years.append(yr)
            revs.append((r or 0) / data._stmt_scale / 1e9)
            nis.append((ni or 0) / data._stmt_scale / 1e9)
        # Use actual columns
        revs, nis = [], []
        for col in reversed(data.income_stmt.columns):
            yr = str(col)[:4]
            rv = None
            for k in ("Total Revenue", "Revenue"):
                if k in data.income_stmt.index:
                    rv = data.income_stmt.loc[k, col]
                    break
            ni = None
            for k in ("Net Income", "Net Income Common Stockholders"):
                if k in data.income_stmt.index:
                    ni = data.income_stmt.loc[k, col]
                    break
            revs.append((float(rv) / data._stmt_scale / 1e9) if rv is not None and not pd.isna(rv) else 0)
            nis.append((float(ni) / data._stmt_scale / 1e9) if ni is not None and not pd.isna(ni) else 0)
    except Exception:
        pass

    years_sorted = [str(c)[:4] for c in reversed(data.income_stmt.columns)]

    s_unit = "B" if data.currency != "INR" else "B (INR)"
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(name="Revenue", x=years_sorted, y=revs,
                         marker=dict(color="#58a6ff", opacity=0.7)), secondary_y=False)
    fig.add_trace(go.Bar(name="Net Income", x=years_sorted, y=nis,
                         marker=dict(color="#3fb950", opacity=0.7)), secondary_y=False)
    fig.update_layout(**chart_defaults(),
                      title=dict(text=f"Revenue & Net Income Trend ({s_unit})",
                                 font=dict(size=14, color=LINE_COLOR)),
                      barmode="group", height=280)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:1.5rem 0 0.5rem 0">
      <div style="font-size:0.7rem;letter-spacing:0.15em;color:#58a6ff;font-weight:600;
                  text-transform:uppercase;margin-bottom:0.3rem">QUANTITATIVE RESEARCH TOOL</div>
      <div style="font-size:2rem;font-weight:700;color:#e6edf3;line-height:1.1">
        Stock Valuation Engine
      </div>
      <div style="color:#8b949e;font-size:0.9rem;margin-top:0.3rem">
        DCF · DDM · Graham · P/E · P/B · PEG · EV/EBITDA · EV/Rev · P/S · P/FCF · RI · NAV · Reverse DCF
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Stock Input")
        ticker_input = st.text_input(
            "Ticker Symbol",
            value="INFY.NS",
            placeholder="e.g. AAPL, INFY.NS, RELIANCE.NS",
            help="Use .NS suffix for NSE (India), .BO for BSE"
        ).strip().upper()

        st.markdown("### ⚙️ Valuation Parameters")

        wacc = st.slider("WACC (%)", 6.0, 18.0, 10.0, 0.5) / 100
        tg   = st.slider("Terminal Growth (%)", 1.0, 6.0, 2.5, 0.25) / 100
        ng   = st.slider("Near-term Growth 1-5yr (%)", 2.0, 40.0, 10.0, 1.0) / 100
        mg   = st.slider("Mid-term Growth 6-10yr (%)", 2.0, 20.0, 6.0, 1.0) / 100
        rr   = st.slider("Required Return (%)", 6.0, 18.0, 9.0, 0.5) / 100
        dg   = st.slider("Dividend Growth (%)", 0.0, 12.0, 4.0, 0.5) / 100
        mos  = st.slider("Margin of Safety (%)", 5.0, 40.0, 20.0, 5.0) / 100

        st.markdown("### 📊 Sector Benchmarks")
        s_pe      = st.number_input("Sector P/E",    value=20.0, step=1.0)
        s_pb      = st.number_input("Sector P/B",    value=3.0,  step=0.5)
        s_ps      = st.number_input("Sector P/S",    value=2.0,  step=0.5)
        s_evebitda= st.number_input("Sector EV/EBITDA", value=12.0, step=1.0)
        s_evrev   = st.number_input("Sector EV/Revenue", value=2.5, step=0.5)
        s_pfcf    = st.number_input("Sector P/FCF",  value=20.0, step=1.0)
        s_peg     = st.number_input("Sector PEG",    value=1.5,  step=0.1)

        st.markdown("### 👥 Competitor Analysis")
        auto_peers = st.checkbox("Auto-detect competitors", value=True)
        max_peers  = st.slider("Max competitors", 2, 8, 4)

        run_btn = st.button("🚀  Run Valuation", use_container_width=True, type="primary")

    cfg = ValuationConfig(
        wacc=wacc, terminal_growth=tg, near_growth=ng, mid_growth=mg,
        required_return=rr, dividend_growth=dg, margin_of_safety=mos,
        sector_pe=s_pe, sector_pb=s_pb, sector_ps=s_ps,
        sector_evebitda=s_evebitda, sector_evrev=s_evrev,
        sector_pfcf=s_pfcf, sector_peg=s_peg,
    )

    if not run_btn and "last_ticker" not in st.session_state:
        st.markdown("""
        <div style="text-align:center;padding:4rem 0;color:#30363d">
          <div style="font-size:3rem">📈</div>
          <div style="font-size:1.1rem;margin-top:1rem;color:#8b949e">
            Enter a ticker symbol and click <strong style="color:#58a6ff">Run Valuation</strong>
          </div>
          <div style="font-size:0.85rem;margin-top:0.5rem;color:#30363d">
            Supports NSE (.NS), BSE (.BO), NYSE, NASDAQ, LSE (.L), and more
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Cache session state so page doesn't reset on slider change
    if run_btn:
        st.session_state["last_ticker"] = ticker_input
        st.session_state["last_cfg"] = cfg
    else:
        ticker_input = st.session_state.get("last_ticker", ticker_input)
        cfg = st.session_state.get("last_cfg", cfg)

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner(f"Fetching data for **{ticker_input}**..."):
        try:
            data = StockData(ticker_input)
        except ValueError as e:
            st.error(f"❌ {e}")
            return

    s = sym(data.currency)
    info = data.info
    qr   = data.quality_report()

    # ── Company header ────────────────────────────────────────────────────────
    col_logo, col_info = st.columns([1, 5])
    with col_info:
        company_name = info.get("longName") or info.get("shortName") or ticker_input
        sector   = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        exchange = info.get("exchange", "")
        website  = info.get("website", "")
        st.markdown(f"""
        <div style="margin-bottom:0.5rem">
          <span style="font-size:1.6rem;font-weight:700;color:#e6edf3">{company_name}</span>
          <span style="font-size:0.9rem;color:#58a6ff;margin-left:0.7rem;
                       background:#161b22;padding:2px 10px;border-radius:12px;
                       border:1px solid #30363d">{ticker_input}</span>
          <span style="font-size:0.8rem;color:#8b949e;margin-left:0.5rem">{exchange}</span>
        </div>
        <div style="color:#8b949e;font-size:0.85rem">
          {sector} &nbsp;·&nbsp; {industry}
          {"&nbsp;·&nbsp; <a href='" + website + "' style='color:#58a6ff'>" + website.replace("https://","") + "</a>" if website else ""}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ── Key metrics row ───────────────────────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    price_chg = info.get("regularMarketChangePercent", 0) or 0

    def metric_card(col, label, value, delta=""):
        delta_class = "metric-delta-up" if "▲" in delta else "metric-delta-down" if "▼" in delta else "metric-delta-flat"
        col.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          {"<div class='" + delta_class + "'>" + delta + "</div>" if delta else ""}
        </div>""", unsafe_allow_html=True)

    chg_pct = price_chg * 100 if abs(price_chg) < 1 else price_chg
    delta_str = f"{'▲' if chg_pct >= 0 else '▼'} {abs(chg_pct):.2f}% today"
    metric_card(m1, "Price", f"{s}{data.price:,.2f}", delta_str)
    metric_card(m2, "Market Cap", fmt_large(data.market_cap, data.currency))
    metric_card(m3, "EPS (TTM)", f"{s}{data.eps:,.2f}" if data.eps else "N/A")
    metric_card(m4, "P/E Ratio",
                f"{data.price/data.eps:.1f}x" if data.eps and data.eps > 0 else "N/A")
    metric_card(m5, "FCF", fmt_large(data.fcf, data.currency) if data.fcf else "N/A")
    metric_card(m6, "Beta", f"{data.beta:.2f}")

    # ── Data quality ──────────────────────────────────────────────────────────
    dq_score = qr["score_pct"]
    dq_class = "dq-high" if dq_score >= 75 else "dq-medium" if dq_score >= 50 else "dq-low"
    dq_icon  = "✅" if dq_score >= 75 else "⚠️" if dq_score >= 50 else "❌"
    missing_txt = ", ".join(qr["missing"]) if qr["missing"] else "none"
    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
                padding:0.7rem 1.2rem;margin-bottom:1rem;display:flex;
                align-items:center;gap:1rem;flex-wrap:wrap">
      <span style="color:#8b949e;font-size:0.8rem">DATA QUALITY</span>
      <span class="{dq_class}">{dq_icon} {dq_score:.0f}%</span>
      <span style="color:#8b949e;font-size:0.8rem">
        {len(qr['present'])}/{len(qr['present'])+len(qr['missing'])} fields available
      </span>
      {"<span style='color:#f85149;font-size:0.8rem'>Missing: " + missing_txt + "</span>" if qr["missing"] else ""}
      {"<span style='color:#d29922;font-size:0.8rem'>⚠ Statement unit correction: " + qr['scale_display'] + " applied to financials</span>" if qr.get("scale_display") else ""}
    </div>
    """, unsafe_allow_html=True)

    # ── Run models ────────────────────────────────────────────────────────────
    with st.spinner("Running valuation models..."):
        models   = run_all_models(data, cfg)
        composite, mos_price, upside = compute_composite(models, data.price, cfg)

    # ── Verdict banner ────────────────────────────────────────────────────────
    if composite:
        valid_count = sum(1 for m in models if m.get("intrinsic_value") is not None)
        if upside > mos * 100:
            v_class = "verdict-undervalued"
            v_text  = f"🟢 UNDERVALUED   |   Composite Fair Value: {s}{composite:,.2f}   |   Upside: +{upside:.1f}%   |   MoS Entry Price: {s}{mos_price:,.2f}   |   {valid_count} models ran"
        elif upside < -mos * 100:
            v_class = "verdict-overvalued"
            v_text  = f"🔴 OVERVALUED   |   Composite Fair Value: {s}{composite:,.2f}   |   Downside: {upside:.1f}%   |   {valid_count} models ran"
        else:
            v_class = "verdict-fair"
            v_text  = f"🟡 FAIRLY VALUED   |   Composite Fair Value: {s}{composite:,.2f}   |   {upside:+.1f}% from current   |   {valid_count} models ran"
        st.markdown(f'<div class="{v_class}">{v_text}</div>', unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📊 Valuation", "📈 Charts", "🔍 DCF Sensitivity",
                    "👥 Peer Analysis", "📋 Financials", "ℹ️ Company Info"])

    # ────────── TAB 1: VALUATION TABLE ──────────────────────────────────────
    with tabs[0]:
        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            st.plotly_chart(
                chart_valuation_waterfall(models, data.price, composite, data.currency),
                use_container_width=True
            )

        with col_table:
            st.markdown('<div class="section-header">Model Results</div>', unsafe_allow_html=True)
            rows = []
            for m in models:
                iv     = m.get("intrinsic_value")
                method = m["method"]
                if method == "Reverse DCF":
                    ig = m.get("implied_growth")
                    rows.append({
                        "Model": method,
                        "Fair Value": "—",
                        "Upside %": f"Implied FCF growth: {ig*100:.1f}%/yr" if ig else "N/A",
                        "Status": "ℹ️",
                    })
                    continue
                if iv is None:
                    rows.append({"Model": method, "Fair Value": "N/A",
                                 "Upside %": "—", "Status": f"⚠ {m.get('error','')[:30]}"})
                    continue
                upsid = (iv / data.price - 1) * 100
                rows.append({
                    "Model": method,
                    "Fair Value": f"{s}{iv:,.2f}",
                    "Upside %": f"{'▲' if upsid>=0 else '▼'} {abs(upsid):.1f}%",
                    "Weight": f"{MODEL_WEIGHTS.get(method,0)*100:.0f}%",
                    "Status": "✅",
                })
            df_table = pd.DataFrame(rows)
            st.dataframe(df_table, use_container_width=True, hide_index=True,
                         height=460)

        # Summary metrics
        if composite:
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            metric_card(c1, "Composite Fair Value", f"{s}{composite:,.2f}")
            metric_card(c2, "Margin of Safety Price", f"{s}{mos_price:,.2f}")
            metric_card(c3, "Current Price", f"{s}{data.price:,.2f}")
            upside_str = f"{'▲' if upside>=0 else '▼'} {abs(upside):.1f}%"
            upside_color = "▲" if upside >= 0 else "▼"
            metric_card(c4, "Upside / Downside", f"{upside:+.1f}%",
                         f"{upside_color} vs current")

    # ────────── TAB 2: CHARTS ────────────────────────────────────────────────
    with tabs[1]:
        st.plotly_chart(chart_price_history(data), use_container_width=True)
        st.plotly_chart(chart_multiples_radar(data, cfg), use_container_width=True)

    # ────────── TAB 3: DCF SENSITIVITY ──────────────────────────────────────
    with tabs[2]:
        st.markdown("""
        <div style="color:#8b949e;font-size:0.85rem;margin-bottom:1rem">
          This heatmap shows how the DCF fair value changes with different WACC and terminal 
          growth rate assumptions. <strong style="color:#3fb950">Green = above current price</strong>, 
          <strong style="color:#f85149">Red = below current price</strong>.
          Your current assumptions are highlighted.
        </div>
        """, unsafe_allow_html=True)
        fig_sens = chart_dcf_sensitivity(data, cfg)
        if fig_sens.data:
            st.plotly_chart(fig_sens, use_container_width=True)
        else:
            st.info("DCF sensitivity requires positive Free Cash Flow.")

        # Also show reverse DCF result prominently
        for m in models:
            if m["method"] == "Reverse DCF" and m.get("implied_growth") is not None:
                ig = m["implied_growth"]
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
                            padding:1rem 1.5rem;margin-top:1rem">
                  <div style="color:#8b949e;font-size:0.75rem;text-transform:uppercase;
                               letter-spacing:0.08em;margin-bottom:0.3rem">REVERSE DCF RESULT</div>
                  <div style="color:#e6edf3;font-size:1.1rem;font-weight:600">
                    At the current price of <span style="color:#58a6ff">{s}{data.price:,.2f}</span>,
                    the market is pricing in 
                    <span style="color:{'#f85149' if ig>0.3 else '#d29922' if ig>0.15 else '#3fb950'}">
                      {ig*100:.1f}% annual FCF growth
                    </span> for the next 10 years.
                  </div>
                  <div style="color:#8b949e;font-size:0.8rem;margin-top:0.3rem">
                    {"⚠️ This is extremely optimistic — implies near-perfect execution for a decade." if ig>0.3 else
                     "🔶 This is ambitious — achievable for fast-growing companies in strong sectors." if ig>0.15 else
                     "✅ This is a reasonable growth expectation." }
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ────────── TAB 4: PEER ANALYSIS ─────────────────────────────────────────
    with tabs[3]:
        if auto_peers:
            with st.spinner("🔍 Auto-detecting competitors..."):
                competitors = find_competitors(ticker_input, max_peers)

            if competitors:
                st.success(f"Found {len(competitors)} peer(s): **{', '.join(competitors)}**")
            else:
                st.warning("Could not auto-detect competitors. Enter them manually below.")

            extra = st.text_input(
                "Add / override competitors (comma-separated)",
                placeholder="e.g. TCS.NS, WIPRO.NS",
                key="manual_peers"
            )
            if extra:
                manual = [t.strip().upper() for t in extra.split(",") if t.strip()]
                competitors = list(dict.fromkeys(competitors + manual))[:max_peers+2]
        else:
            extra = st.text_input("Enter competitors (comma-separated)",
                                   placeholder="e.g. TCS.NS, WIPRO.NS", key="manual_peers2")
            competitors = [t.strip().upper() for t in extra.split(",") if t.strip()]

        all_tickers = [ticker_input] + competitors

        if len(all_tickers) > 1:
            peer_results = []
            prog = st.progress(0, text="Running valuations...")
            for i, t in enumerate(all_tickers):
                prog.progress((i+1)/len(all_tickers), text=f"Valuing {t}...")
                try:
                    d = StockData(t)
                    ms = run_all_models(d, cfg)
                    comp, mos_p, ups = compute_composite(ms, d.price, cfg)
                    peer_results.append({
                        "ticker": t,
                        "current_price": d.price,
                        "composite_fair_value": comp,
                        "margin_of_safety_price": mos_p,
                        "currency": d.currency,
                        "upside": ups,
                        "market_cap": d.market_cap,
                        "eps": d.eps,
                        "pe": (d.price/d.eps) if d.eps and d.eps>0 else None,
                        "pb": (d.price/d.bvps) if d.bvps and d.bvps>0 else None,
                        "rev_growth": d.growth_rate,
                        "beta": d.beta,
                        "fcf": d.fcf,
                        "data_quality": d.quality_report()["score_pct"],
                    })
                except Exception as e:
                    peer_results.append({"ticker": t, "error": str(e)})
            prog.empty()

            # Chart
            st.plotly_chart(chart_peer_comparison(peer_results), use_container_width=True)

            # Table
            st.markdown('<div class="section-header">Peer Comparison Table</div>',
                        unsafe_allow_html=True)
            peer_rows = []
            for r in peer_results:
                if r.get("error"):
                    peer_rows.append({"Ticker": r["ticker"], "Error": r["error"][:50]})
                    continue
                cs = sym(r["currency"])
                peer_rows.append({
                    "Ticker": r["ticker"],
                    "Price": f"{cs}{r['current_price']:,.2f}",
                    "Fair Value": f"{cs}{r['composite_fair_value']:,.2f}" if r["composite_fair_value"] else "N/A",
                    "MoS Price": f"{cs}{r['margin_of_safety_price']:,.2f}" if r["margin_of_safety_price"] else "N/A",
                    "Upside %": f"{r['upside']:+.1f}%" if r["upside"] is not None else "N/A",
                    "P/E": f"{r['pe']:.1f}x" if r["pe"] else "N/A",
                    "P/B": f"{r['pb']:.1f}x" if r["pb"] else "N/A",
                    "Rev Growth": f"{r['rev_growth']*100:.1f}%" if r["rev_growth"] else "N/A",
                    "Beta": f"{r['beta']:.2f}",
                    "Data Quality": f"{r['data_quality']:.0f}%",
                })
            st.dataframe(pd.DataFrame(peer_rows), use_container_width=True,
                         hide_index=True, height=300)
        else:
            st.info("Enable auto-detect or add competitors manually to see peer comparison.")

    # ────────── TAB 5: FINANCIALS ─────────────────────────────────────────────
    with tabs[4]:
        st.plotly_chart(chart_financials(data), use_container_width=True)

        col_is, col_bs, col_cf = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

        def df_style(df: pd.DataFrame):
            df2 = df.copy()
            df2.columns = [str(c)[:10] for c in df2.columns]
            df2 = df2.map(lambda x: f"{x/1e9:.2f}B" if isinstance(x,(int,float)) and not pd.isna(x) else x)
            return df2

        with col_is:
            if not data.income_stmt.empty:
                st.dataframe(df_style(data.income_stmt), use_container_width=True)
            else:
                st.info("Income statement not available.")
        with col_bs:
            if not data.balance_sheet.empty:
                st.dataframe(df_style(data.balance_sheet), use_container_width=True)
            else:
                st.info("Balance sheet not available.")
        with col_cf:
            if not data.cashflow.empty:
                st.dataframe(df_style(data.cashflow), use_container_width=True)
            else:
                st.info("Cash flow statement not available.")

    # ────────── TAB 6: COMPANY INFO ───────────────────────────────────────────
    with tabs[5]:
        col_desc, col_meta = st.columns([3, 2])
        with col_desc:
            st.markdown('<div class="section-header">Business Description</div>',
                        unsafe_allow_html=True)
            desc = info.get("longBusinessSummary", "No description available.")
            st.markdown(f'<div style="color:#c9d1d9;line-height:1.7;font-size:0.9rem">{desc}</div>',
                        unsafe_allow_html=True)

        with col_meta:
            st.markdown('<div class="section-header">Key Facts</div>',
                        unsafe_allow_html=True)
            facts = {
                "Employees":       info.get("fullTimeEmployees", "N/A"),
                "HQ Country":      info.get("country", "N/A"),
                "City":            info.get("city", "N/A"),
                "Exchange":        info.get("exchange", "N/A"),
                "52W High":        f"{s}{info['fiftyTwoWeekHigh']:,.2f}" if info.get("fiftyTwoWeekHigh") else "N/A",
                "52W Low":         f"{s}{info['fiftyTwoWeekLow']:,.2f}" if info.get("fiftyTwoWeekLow") else "N/A",
                "Div Yield":       f"{info.get('dividendYield',0)*100:.2f}%" if info.get("dividendYield") else "N/A",
                "Payout Ratio":    f"{info.get('payoutRatio',0)*100:.1f}%" if info.get("payoutRatio") else "N/A",
                "Debt/Equity":     f"{info.get('debtToEquity','N/A')}",
                "Current Ratio":   f"{info.get('currentRatio','N/A')}",
                "Profit Margin":   f"{info.get('profitMargins',0)*100:.1f}%" if info.get("profitMargins") else "N/A",
                "ROE":             f"{info.get('returnOnEquity',0)*100:.1f}%" if info.get("returnOnEquity") else "N/A",
                "ROIC":            f"{info.get('returnOnAssets',0)*100:.1f}%" if info.get("returnOnAssets") else "N/A",
            }
            for k, v in facts.items():
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:0.35rem 0;
                            border-bottom:1px solid #21262d">
                  <span style="color:#8b949e;font-size:0.85rem">{k}</span>
                  <span style="color:#e6edf3;font-size:0.85rem;font-weight:500">{v}</span>
                </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()