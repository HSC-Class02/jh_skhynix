from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

BASE_URL = "https://opendart.fss.or.kr/api"
CORP_CODE = os.getenv("DART_CORP_CODE", "00164779")
API_KEY = os.getenv("DART_API_KEY", "")
START_YEAR = int(os.getenv("DART_START_YEAR", "2010"))
END_YEAR = int(os.getenv("DART_END_YEAR", str(datetime.now().year)))
RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "data/processed"))
REQUEST_SLEEP = float(os.getenv("DART_REQUEST_SLEEP", "0.12"))

REPORT_CODES = {
    "annual": "11011",
    "half_year": "11012",
    "q1": "11013",
    "q3": "11014",
}
REPORT_NAMES = {
    "annual": "사업보고서",
    "half_year": "반기보고서",
    "q1": "1분기보고서",
    "q3": "3분기보고서",
}

# The guide supplied by the user is the source for this metric set.
METRIC_ALIASES: Dict[str, List[str]] = {
    "total_assets": ["자산총계", "총자산"],
    "cash": ["현금및현금성자산", "현금및현금성 자산", "현금 및 현금성자산"],
    "receivables": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권"],
    "inventory": ["재고자산"],
    "ppe": ["유형자산"],
    "current_assets": ["유동자산"],
    "current_liabilities": ["유동부채"],
    "payables": ["매입채무", "매입채무및기타채무", "매입채무 및 기타채무"],
    "total_liabilities": ["부채총계", "총부채"],
    "interest_bearing_debt": [
        "단기차입금", "유동성장기부채", "장기차입금", "사채",
        "유동성사채", "장기성차입금", "리스부채", "유동리스부채", "비유동리스부채",
    ],
    "equity": ["자본총계", "총자본"],
    "revenue": ["매출액", "수익(매출액)", "영업수익"],
    "gross_profit": ["매출총이익"],
    "sga": ["판매비와관리비", "판매비및관리비", "판매비와 일반관리비"],
    "operating_profit": ["영업이익", "영업이익(손실)"],
    "pretax_income": ["법인세비용차감전순이익", "법인세비용차감전순이익(손실)", "세전이익"],
    "net_income": ["당기순이익", "당기순이익(손실)"],
    "controlling_net_income": ["지배기업의 소유주에게 귀속되는 당기순이익", "지배기업 소유주지분 순이익", "지배주주순이익"],
    "ebitda": ["EBITDA", "상각전영업이익"],
    "interest_expense": ["이자비용", "금융비용"],
    "cost_of_sales": ["매출원가"],
    "capex": ["유형자산의 취득", "유형자산취득", "유형자산 취득", "무형자산의 취득", "무형자산취득", "무형자산 취득"],
    "cfo": ["영업활동현금흐름", "영업활동으로 인한 현금흐름"],
    "cfi": ["투자활동현금흐름", "투자활동으로 인한 현금흐름"],
    "cff": ["재무활동현금흐름", "재무활동으로 인한 현금흐름"],
}

BALANCE_SHEET_METRICS = {
    "total_assets", "cash", "receivables", "inventory", "ppe", "current_assets", "current_liabilities", "payables",
    "total_liabilities", "interest_bearing_debt", "equity"
}
INCOME_METRICS = {
    "revenue", "gross_profit", "sga", "operating_profit", "pretax_income",
    "net_income", "controlling_net_income", "ebitda", "interest_expense", "cost_of_sales"
}
CASHFLOW_METRICS = {"cfo", "cfi", "cff", "capex"}


def require_key() -> None:
    if not API_KEY:
        raise RuntimeError(
            "DART_API_KEY is missing. Add it as a GitHub Actions secret named DART_API_KEY."
        )


def get_json(endpoint: str, params: Dict[str, Any], retries: int = 4) -> Dict[str, Any]:
    require_key()
    params = {**params, "crtfc_key": API_KEY}
    url = f"{BASE_URL}/{endpoint}.json"
    last_error = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=40)
            r.raise_for_status()
            payload = r.json()
            if payload.get("status") == "000":
                return payload
            if payload.get("status") == "013":
                return payload
            if payload.get("status") == "020":
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"DART API {endpoint}: {payload.get('status')} {payload.get('message')}")
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"DART API request failed: {endpoint}: {last_error}")


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def filing_list(start: str, end: str, page_no: int = 1) -> Dict[str, Any]:
    return get_json(
        "list",
        {
            "corp_code": CORP_CODE,
            "bgn_de": start,
            "end_de": end,
            "page_no": page_no,
            "page_count": 100,
            "last_reprt_at": "Y",
        },
    )


def daterange_chunks(start_year: int, end_year: int) -> Iterable[Tuple[str, str]]:
    for year in range(start_year, end_year + 1):
        yield f"{year}0101", f"{year}1231"


def collect_filing_metadata() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for start, end in daterange_chunks(START_YEAR, END_YEAR):
        page = 1
        while True:
            payload = filing_list(start, end, page)
            save_json(RAW_DIR / "filings" / f"{start[:4]}_page{page}.json", payload)
            items = payload.get("list", []) or []
            for item in items:
                ptype = item.get("pblntf_detail_ty")
                report_type = {
                    "A001": "annual",
                    "A002": "half_year",
                    "A003": "q1_or_q3",
                }.get(ptype)
                title = item.get("report_nm", "")
                if "사업보고서" in title:
                    report_type = "annual"
                elif "반기보고서" in title:
                    report_type = "half_year"
                elif "1분기보고서" in title:
                    report_type = "q1"
                elif "3분기보고서" in title:
                    report_type = "q3"
                if report_type:
                    item["normalized_report_type"] = report_type
                    rows.append(item)
            total = int(payload.get("total_page", 1) or 1)
            if page >= total:
                break
            page += 1
            time.sleep(REQUEST_SLEEP)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates(subset=["rcept_no"]).sort_values("rcept_dt")
    df["report_url"] = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + df["rcept_no"].astype(str)
    out = PROCESSED_DIR / "filings.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    return df


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name)).replace("·", "")


def parse_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s in {"-", "–", "nan", "None"}:
        return None
    s = s.replace("(", "-").replace(")", "")
    try:
        return float(s)
    except ValueError:
        return None


def match_metric(account_name: str) -> Optional[str]:
    n = normalize_name(account_name)
    exact: List[str] = []
    for metric, aliases in METRIC_ALIASES.items():
        for alias in aliases:
            if n == normalize_name(alias):
                exact.append(metric)
    if len(exact) == 1:
        return exact[0]
    return None


def fetch_financials(year: int, report_key: str, fs_div: str = "CFS") -> pd.DataFrame:
    # OpenDART's financial API explicitly documents coverage from 2015 onward.
    if year < 2015:
        return pd.DataFrame()
    reprt_code = REPORT_CODES[report_key]
    payload = get_json(
        "fnlttSinglAcntAll",
        {
            "corp_code": CORP_CODE,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
    )
    save_json(RAW_DIR / "financials" / str(year) / f"{report_key}_{fs_div}.json", payload)
    items = payload.get("list", []) or []
    if not items:
        return pd.DataFrame()
    rows: List[Dict[str, Any]] = []
    for item in items:
        metric = match_metric(item.get("account_nm", ""))
        if not metric:
            continue
        amount = parse_amount(item.get("thstrm_amount"))
        cumulative = parse_amount(item.get("thstrm_add_amount"))
        # Balance sheet values use thstrm_amount; P&L/CF uses current-period and cumulative fields.
        rows.append({
            "year": year,
            "report_type": report_key,
            "fs_div": fs_div,
            "sj_div": item.get("sj_div"),
            "account_id": item.get("account_id"),
            "account_nm": item.get("account_nm"),
            "metric": metric,
            "amount": amount,
            "cumulative_amount": cumulative,
            "currency": item.get("currency"),
            "rcept_no": item.get("rcept_no"),
        })
    return pd.DataFrame(rows)


def collect_financial_data() -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    end_year = min(END_YEAR, datetime.now().year)
    for year in range(max(2015, START_YEAR), end_year + 1):
        for report_key in REPORT_CODES:
            # CFS is the primary source for consolidated analysis. Fall back to OFS only if CFS is empty.
            df = fetch_financials(year, report_key, "CFS")
            if df.empty:
                df = fetch_financials(year, report_key, "OFS")
            if not df.empty:
                frames.append(df)
            time.sleep(REQUEST_SLEEP)
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.drop_duplicates(subset=["year", "report_type", "fs_div", "metric", "account_nm"])
    out = PROCESSED_DIR / "financial_raw.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(out, index=False, encoding="utf-8-sig")
    return all_df


def choose_values(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df.copy()
    # Some DART presentations split interest-bearing debt and CAPEX across several accounts.
    # Sum those components instead of dropping them as duplicates.
    additive_metrics = {"interest_bearing_debt", "capex"}
    additive = d[d["metric"].isin(additive_metrics)].copy()
    additive_rows = []
    if not additive.empty:
        for (year, report_type, metric), g in additive.groupby(["year", "report_type", "metric"]):
            additive_rows.append({
                "year": year, "report_type": report_type, "metric": metric,
                "amount": pd.to_numeric(g["amount"], errors="coerce").sum(min_count=1),
                "cumulative_amount": pd.to_numeric(g["cumulative_amount"], errors="coerce").sum(min_count=1),
                "currency": g["currency"].dropna().iloc[0] if g["currency"].notna().any() else None,
                "account_nm": "; ".join(g["account_nm"].astype(str).tolist()),
                "rcept_no": g["rcept_no"].dropna().iloc[0] if g["rcept_no"].notna().any() else None,
            })
    other = d[~d["metric"].isin(additive_metrics)].sort_values(["year", "report_type", "metric", "account_nm"]).drop_duplicates(
        subset=["year", "report_type", "metric"], keep="first"
    )
    return pd.concat([other, pd.DataFrame(additive_rows)], ignore_index=True)

def build_period_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = choose_values(df)
    rows: List[Dict[str, Any]] = []
    for _, r in d.iterrows():
        # For income/cashflow statements, cumulative is used for half-year and Q3; annual uses amount.
        use_cumulative = r["report_type"] in {"half_year", "q1", "q3"} and r["metric"] in INCOME_METRICS | CASHFLOW_METRICS
        value = r["cumulative_amount"] if use_cumulative and pd.notna(r["cumulative_amount"]) else r["amount"]
        rows.append({
            "period": f"{int(r['year'])}-{r['report_type']}",
            "year": int(r["year"]),
            "report_type": r["report_type"],
            "metric": r["metric"],
            "value": value,
            "currency": r["currency"],
            "account_nm": r["account_nm"],
            "rcept_no": r["rcept_no"],
        })
    return pd.DataFrame(rows)


def pivot_metrics(period_df: pd.DataFrame) -> pd.DataFrame:
    if period_df.empty:
        return pd.DataFrame()
    p = period_df.pivot_table(index=["year", "report_type"], columns="metric", values="value", aggfunc="first").reset_index()
    return p.sort_values(["year", "report_type"])


def safe_div(a: Any, b: Any) -> Optional[float]:
    try:
        if pd.isna(a) or pd.isna(b) or float(b) == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def calc_ratios(p: pd.DataFrame) -> pd.DataFrame:
    if p.empty:
        return p
    p = p.copy().sort_values(["year", "report_type"])
    ratio_cols = ["gross_margin", "operating_margin", "net_margin", "ebitda_margin", "roa", "roe",
                  "current_ratio", "quick_ratio", "debt_ratio", "equity_ratio", "debt_to_assets",
                  "interest_coverage", "net_debt_ebitda", "asset_turnover", "dso", "dio", "dpo",
                  "ccc", "revenue_growth", "cfo_to_net_income"]
    for col in ratio_cols:
        p[col] = None
    if "interest_bearing_debt" in p and "cash" in p:
        p["net_debt"] = p["interest_bearing_debt"] - p["cash"]
    if "cfo" in p and "capex" in p:
        p["fcf"] = p["cfo"] - p["capex"].abs()
    if "revenue" in p:
        p["gross_margin"] = p.apply(lambda r: safe_div(r.get("gross_profit"), r.get("revenue")) * 100 if safe_div(r.get("gross_profit"), r.get("revenue")) is not None else None, axis=1)
        p["operating_margin"] = p.apply(lambda r: safe_div(r.get("operating_profit"), r.get("revenue")) * 100 if safe_div(r.get("operating_profit"), r.get("revenue")) is not None else None, axis=1)
        p["net_margin"] = p.apply(lambda r: safe_div(r.get("net_income"), r.get("revenue")) * 100 if safe_div(r.get("net_income"), r.get("revenue")) is not None else None, axis=1)
        if "ebitda" in p:
            p["ebitda_margin"] = p.apply(lambda r: safe_div(r.get("ebitda"), r.get("revenue")) * 100 if safe_div(r.get("ebitda"), r.get("revenue")) is not None else None, axis=1)
        p["revenue_growth"] = p["revenue"].pct_change() * 100
    if "total_assets" in p and "net_income" in p:
        avg_assets = (p["total_assets"] + p["total_assets"].shift(1)) / 2
        p["roa"] = p["net_income"] / avg_assets * 100
        if "revenue" in p:
            p["asset_turnover"] = p["revenue"] / avg_assets
    if "equity" in p and "net_income" in p:
        avg_equity = (p["equity"] + p["equity"].shift(1)) / 2
        p["roe"] = p["net_income"] / avg_equity * 100
    if "current_assets" in p and "current_liabilities" in p:
        p["current_ratio"] = p["current_assets"] / p["current_liabilities"] * 100
        if "inventory" in p:
            p["quick_ratio"] = (p["current_assets"] - p["inventory"]) / p["current_liabilities"] * 100
    if "total_liabilities" in p and "equity" in p:
        p["debt_ratio"] = p["total_liabilities"] / p["equity"] * 100
    if "equity" in p and "total_assets" in p:
        p["equity_ratio"] = p["equity"] / p["total_assets"] * 100
    if "interest_bearing_debt" in p and "total_assets" in p:
        p["debt_to_assets"] = p["interest_bearing_debt"] / p["total_assets"] * 100
    if "operating_profit" in p and "interest_expense" in p:
        p["interest_coverage"] = p["operating_profit"] / p["interest_expense"].abs()
    if "net_debt" in p and "ebitda" in p:
        p["net_debt_ebitda"] = p.apply(lambda r: safe_div(r.get("net_debt"), r.get("ebitda")), axis=1)
    if "cfo" in p and "net_income" in p:
        p["cfo_to_net_income"] = p.apply(lambda r: safe_div(r.get("cfo"), r.get("net_income")), axis=1)
    # Working-capital days use average balances when prior-period balances are available.
    if "receivables" in p and "revenue" in p:
        avg_ar = (p["receivables"] + p["receivables"].shift(1)) / 2
        p["dso"] = avg_ar / p["revenue"] * 365
    if "inventory" in p and "cost_of_sales" in p:
        avg_inv = (p["inventory"] + p["inventory"].shift(1)) / 2
        p["dio"] = avg_inv / p["cost_of_sales"].abs() * 365
    if "payables" in p and "cost_of_sales" in p:
        avg_ap = (p["payables"] + p["payables"].shift(1)) / 2
        p["dpo"] = avg_ap / p["cost_of_sales"].abs() * 365
    if all(x in p for x in ["dso", "dio", "dpo"]):
        p["ccc"] = p["dso"] + p["dio"] - p["dpo"]
    return p


def derive_quarterly(period_df: pd.DataFrame) -> pd.DataFrame:
    """Convert DART cumulative Q1/H1/Q3 values into discrete Q1-Q4 values."""
    if period_df.empty:
        return period_df
    flow_metrics = INCOME_METRICS | CASHFLOW_METRICS
    p = period_df.copy()
    p["quarter"] = None
    p["value_type"] = "reported"
    rows = []
    for year, g in p.groupby("year"):
        by_type = {k: v for k, v in g.groupby("report_type")}
        for metric in g["metric"].dropna().unique():
            mg = g[g["metric"] == metric]
            # Balance-sheet items are point-in-time; map report dates to quarter ends.
            if metric not in flow_metrics:
                for rk, q in [("q1", "Q1"), ("half_year", "Q2"), ("q3", "Q3"), ("annual", "Q4")]:
                    if rk in by_type:
                        x = by_type[rk][by_type[rk]["metric"] == metric]
                        if not x.empty:
                            row = x.iloc[0].to_dict(); row["quarter"] = q; row["value_type"] = "reported"; rows.append(row)
                continue
            vals = {}
            for rk in ["q1", "half_year", "q3", "annual"]:
                x = mg[mg["report_type"] == rk]
                if not x.empty:
                    vals[rk] = x.iloc[0]["value"]
            if "q1" in vals: rows.append({**mg.iloc[0].to_dict(), "quarter":"Q1", "value":vals["q1"], "period":f"{year}-Q1", "report_type":"quarterly", "value_type":"derived_from_reported"})
            if "half_year" in vals and "q1" in vals: rows.append({**mg.iloc[0].to_dict(), "quarter":"Q2", "value":vals["half_year"]-vals["q1"], "period":f"{year}-Q2", "report_type":"quarterly", "value_type":"derived_from_reported"})
            if "q3" in vals and "half_year" in vals: rows.append({**mg.iloc[0].to_dict(), "quarter":"Q3", "value":vals["q3"]-vals["half_year"], "period":f"{year}-Q3", "report_type":"quarterly", "value_type":"derived_from_reported"})
            if "annual" in vals and "q3" in vals: rows.append({**mg.iloc[0].to_dict(), "quarter":"Q4", "value":vals["annual"]-vals["q3"], "period":f"{year}-Q4", "report_type":"quarterly", "value_type":"derived_from_reported"})
    return pd.DataFrame(rows)

def write_dashboard_data(period_df: pd.DataFrame, ratios: pd.DataFrame, quarterly_df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if not period_df.empty:
        period_df.to_json(PROCESSED_DIR / "period_data.json", orient="records", force_ascii=False, indent=2)
    else:
        (PROCESSED_DIR / "period_data.json").write_text("[]", encoding="utf-8")
    if not quarterly_df.empty:
        quarterly_df.to_json(PROCESSED_DIR / "quarterly_data.json", orient="records", force_ascii=False, indent=2)
    else:
        (PROCESSED_DIR / "quarterly_data.json").write_text("[]", encoding="utf-8")
    if not ratios.empty:
        ratios.to_json(PROCESSED_DIR / "ratios.json", orient="records", force_ascii=False, indent=2)
        ratios.to_csv(PROCESSED_DIR / "ratios.csv", index=False, encoding="utf-8-sig")
    else:
        (PROCESSED_DIR / "ratios.json").write_text("[]", encoding="utf-8")
    metadata = {
        "company": "SK hynix Inc.",
        "corp_code": CORP_CODE,
        "start_year_requested": START_YEAR,
        "api_financial_start_year": 2015,
        "end_year": END_YEAR,
        "updated_at_utc": datetime.utcnow().isoformat() + "Z",
        "note": "OpenDART fnlttSinglAcntAll documents financial API coverage from 2015 onward; 2010-2014 requires a legacy filing-table parser or manual archive backfill.",
    }
    (PROCESSED_DIR / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    require_key()
    filings = collect_filing_metadata()
    financials = collect_financial_data()
    periods = build_period_table(financials)
    ratios = calc_ratios(pivot_metrics(periods))
    quarterly = derive_quarterly(periods)
    write_dashboard_data(periods, ratios, quarterly)
    print(f"Collected filings: {len(filings)}")
    print(f"Collected financial rows: {len(financials)}")
    print(f"Periods: {len(periods)}")


if __name__ == "__main__":
    main()
