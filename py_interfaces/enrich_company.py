from __future__ import annotations

"""Remade enrich_company.py – *v2*

Changes from v1
---------------
1. **Console output** – switched from the standard ``logging`` module to
   plain ``print`` calls so progress is visible even if no logging handler is
   configured.
2. **Robust ``stage_numeric``** – we now fall back gracefully:
   * First choice: exact match on the *VC Round* cell (Seed, A, B …)
   * Second choice: map ``Deal Type 1/2/3`` containing *IPO* or *Public* → 8
   * Third choice: infer from *Deal Size* median bucket if the round text is
     blank **and** no IPO/Public tag.
     
     │ Deal Size (USD M) │ stage_numeric │ rationale │
     │-------------------│---------------│-----------│
     │      < 5          │       1       │ Seed / Pre‑seed
     │    5 – 15         │       2       │ Series A
     │   15 – 50         │       3       │ Series B
     │   50 – 150        │       4       │ Series C
     │   150 – 500       │       5       │ Series D‑E
     │   > 500           │       6       │ Growth / Late‑stage
3. Replaced deprecated ``id(c)`` with the stable ``elementId(c)`` Neo4j 5+
   function to silence deprecation warnings.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from dateutil.relativedelta import relativedelta

from neo4j_database import Neo4jDatabase  # local helper wrapper

try:
    import pycountry  # type: ignore
except ImportError:  # optional dependency only for ISO‑3 conversion
    pycountry = None  # type: ignore

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

STAGE_MAP: dict[str, int] = {
    "Seed": 1,
    "Series A": 2,
    "Series B": 3,
    "Series C": 4,
    "Series D": 5,
    "Series E": 5,
    "Series F": 6,
    "Series G": 6,
    "IPO": 8,
    "Public": 8,
}

# frozen snapshot date so months‑ago math is stable
TODAY = datetime(2025, 5, 13)

# ────────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ────────────────────────────────────────────────────────────────────────────────

def _months_between(older: datetime, newer: datetime) -> Optional[int]:
    if pd.isna(older) or pd.isna(newer):
        return None
    delta = relativedelta(newer, older)
    return delta.years * 12 + delta.months


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val) if pd.notna(val) else None
    except Exception:
        return None


def _safe_int(val: Any) -> Optional[int]:
    try:
        return int(float(val)) if pd.notna(val) else None
    except Exception:
        return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def _to_iso3(country: str) -> Optional[str]:
    if not country or pd.isna(country):
        return None
    if pycountry is None:
        return country
    try:
        return pycountry.countries.lookup(country).alpha_3  # type: ignore[attr-defined]
    except Exception:
        return None

# ────────────────────────────────────────────────────────────────────────────────
# PitchBook loader
# ────────────────────────────────────────────────────────────────────────────────

class _PitchBookFileLoader:
    """Locate header row heuristically because PitchBook dumps have pre‑ambles."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _header_row(self, probe: str) -> int:
        sniff = pd.read_excel(self.path, header=None, nrows=25)
        for idx, row in sniff.iterrows():
            if probe.lower() in " ".join(str(x).lower() for x in row.tolist()):
                return idx
        raise ValueError(f"Could not locate header row containing '{probe}' in {self.path.name}")

    def load(self, probe: str) -> pd.DataFrame:
        h = self._header_row(probe)
        df = pd.read_excel(self.path, skiprows=h)
        return df.dropna(how="all")


class PitchBookParser:
    """Loads the *General* row and full *Deals* table for one company."""

    def __init__(self, general_path: Path, deals_path: Path):
        loader_g = _PitchBookFileLoader(general_path)
        loader_d = _PitchBookFileLoader(deals_path)
        self.general_row = loader_g.load("Year Founded").iloc[0]
        self.deals_df = loader_d.load("Deal Date")
        self.deals_df["Deal Date"] = pd.to_datetime(self.deals_df["Deal Date"], errors="coerce")
        self.deals_df = (
            self.deals_df.dropna(subset=["Deal Date"]).sort_values("Deal Date").reset_index(drop=True)
        )
        if self.deals_df.empty:
            raise ValueError(f"Deals sheet {deals_path} has no valid rows with dates")

# ────────────────────────────────────────────────────────────────────────────────
# Feature engineering
# ────────────────────────────────────────────────────────────────────────────────

class PitchBookFeatures:
    """Compute ML‑ready features as a dict."""

    def __init__(self, general_path: Path, deals_path: Path):
        self._p = PitchBookParser(general_path, deals_path)
        self.g = self._p.general_row
        self.d = self._p.deals_df
        self.latest = self.d.iloc[-1]

    # ―――― helper for stage_numeric inference ――――

    def _infer_stage_numeric(self) -> Optional[int]:
        round_text = str(self.latest.get("VC Round", "")).strip()
        if round_text and round_text in STAGE_MAP:
            return STAGE_MAP[round_text]

        # Fallback 2: look at deal types for IPO/Public
        if self.latest[["Deal Type 1", "Deal Type 2", "Deal Type 3"]].astype(str).str.contains(
            "IPO|Public", case=False, na=False
        ).any():
            return STAGE_MAP["Public"]  # = 8

        # Fallback 3: bucket by deal size median
        size = _safe_float(self.latest.get("Deal Size (million, USD)"))
        if size is None:
            return None
        if size < 5:
            return 1
        if size < 15:
            return 2
        if size < 50:
            return 3
        if size < 150:
            return 4
        if size < 500:
            return 5
        return 6  # very large late‑stage / growth

    # ―――― public API ――――

    def to_dict(self) -> Dict[str, Any]:
        founded_year = _safe_int(self.g.get("Year Founded"))
        age_years = TODAY.year - founded_year if founded_year else None

        staff_count = _safe_int(self.g.get("# of Employees at Company"))
        round_count = len(self.d)
        last_round_months_ago = _months_between(self.d["Deal Date"].max(), TODAY)
        avg_round_usd_m = _safe_float(self.d["Deal Size (million, USD)"].mean())

        post_money_last = _safe_float(self.latest.get("Company Post Valuation (million, USD)"))
        rev_latest = _safe_float(self.latest.get("Revenue (million, USD)"))
        rev_growth_yoy = _safe_float(self.latest.get("Revenue Growth YoY (%)"))
        ebitda_latest = _safe_float(self.latest.get("EBITDA (million, USD)"))
        leverage_ratio = _safe_float(self.latest.get("Debt/EBITDA"))

        stage_numeric = self._infer_stage_numeric()

        sector_raw = str(self.g.get("Primary Industry Code"))
        sector_onehot = {f"sector_{_slug(sector_raw)}": 1} if sector_raw and sector_raw != "nan" else {}

        hq_country = _to_iso3(str(self.g.get("HQ Country/Territory")))

        total_funding_usd_m = _safe_float(self.d["Deal Size (million, USD)"].sum())
        largest_round_usd_m = _safe_float(self.d["Deal Size (million, USD)"].max())
        funding_velocity = _safe_float(round_count / age_years) if age_years else None

        valuation_to_revenue_last = (
            post_money_last / rev_latest if post_money_last and rev_latest else None
        )

        ipo_exit_flag = int(
            self.d[["Deal Type 1", "Deal Type 2", "Deal Type 3"]]
            .apply(lambda r: r.astype(str).str.contains("IPO|Public", case=False, na=False).any(), axis=1)
            .any()
        )

        median_round_interval_months = None
        if len(self.d) > 1:
            intervals = self.d["Deal Date"].diff().dropna().dt.days / 30.44
            median_round_interval_months = _safe_float(intervals.median())

        first_round_date = self.d["Deal Date"].min()
        time_to_first_round_months = (
            _months_between(datetime(founded_year, 1, 1), first_round_date)
            if founded_year else None
        )

        feats: Dict[str, Any] = {
            "company_name": self.g.get("Company Name"),
            "age_years": age_years,
            "staff_count": staff_count,
            "round_count": round_count,
            "last_round_months_ago": last_round_months_ago,
            "avg_round_usd_m": avg_round_usd_m,
            "post_money_last": post_money_last,
            "rev_latest": rev_latest,
            "rev_growth_yoy": rev_growth_yoy,
            "ebitda_latest": ebitda_latest,
            "leverage_ratio": leverage_ratio,
            "stage_numeric": stage_numeric,
            "hq_country": hq_country,
            "total_funding_usd_m": total_funding_usd_m,
            "largest_round_usd_m": largest_round_usd_m,
            "funding_velocity": funding_velocity,
            "valuation_to_revenue_last": valuation_to_revenue_last,
            "median_round_interval_months": median_round_interval_months,
            "ipo_exit_flag": ipo_exit_flag,
            "time_to_first_round_months": time_to_first_round_months,
            **sector_onehot,
        }
        return {k: v for k, v in feats.items() if v is not None}

# ────────────────────────────────────────────────────────────────────────────────
# Neo4j orchestration
# ────────────────────────────────────────────────────────────────────────────────

class PitchbookEnricher:
    """Walk a root directory of PitchBook exports, compute features, and add them
    to existing `:Company` nodes in Neo4j.
    """

    def __init__(self, root_dir: str | Path, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.root_dir = Path(root_dir)
        self.db = Neo4jDatabase(neo4j_uri, neo4j_user, neo4j_password)

    # ------------------------------------------------------------------
    # Public runner
    # ------------------------------------------------------------------

    def run(self) -> None:
        for company_dir in self.root_dir.iterdir():
            if not company_dir.is_dir():
                continue

            try:
                general_file = next(company_dir.glob("*General*.xlsx"))
                deals_file = next(company_dir.glob("*Deals*.xlsx"))
            except StopIteration:
                print(f"[SKIP] {company_dir.name}: missing General or Deals workbook(s)")
                continue

            print(f"[→] Processing {company_dir.name}")
            feats = PitchBookFeatures(general_file, deals_file).to_dict()
            self._write_to_neo4j(feats)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_to_neo4j(self, feats: Dict[str, Any]) -> None:
        # Locate the node by name, fetch its elementId (stable string id)
        match_q = "MATCH (c:Company {name:$name}) RETURN elementId(c) AS eid LIMIT 1"
        recs = self.db._run_query(match_q, {"name": feats["company_name"]})
        if not recs:
            print(f"   ↳ Node not found for {feats['company_name']}; skipping")
            return

        eid = recs[0]["eid"]
        props = {k: v for k, v in feats.items() if k != "company_name"}
        if not props:
            print(f"   ↳ No non‐null features for {feats['company_name']}")
            return

        set_clause = ", ".join(f"c.{k} = ${k}" for k in props)
        update_q = f"MATCH (c) WHERE elementId(c) = $eid SET {set_clause}"
        self.db._run_query(update_q, {"eid": eid, **props})
        print(f"   ↳ Updated {feats['company_name']} with {len(props)} properties")

# ────────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, os

    parser = argparse.ArgumentParser(
        description="Enrich Company nodes from PitchBook Excel exports",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("root", help="Root directory containing <Company>/ workbooks")
    parser.add_argument("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j-pass", default=os.getenv("NEO4J_PASSWORD", "neo4j"))
    args = parser.parse_args()

    enricher = PitchbookEnricher(
        root_dir=args.root,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_pass,
    )
    enricher.run()
