#!/usr/bin/env python3
"""Collect SK hynix financial statement data from OpenDART and calculate ratios."""
import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

BASE = "https://opendart.fss.or.kr/api"
CORP_CODE = "00164779"  # SK hynix
REPORTS = [("annual", "11011"), ("half_year", "11012"),
           ("quarterly_q1", "11013"), ("quarterly_q3", "11014")]
OUT = Path("data/financials.csv")
TIMEOUT = 45

# DART account names can vary by filing; first matching account name is used.
ACCOUNT_ALIASES = {
    "revenue": ["매출액", "수익(매출액)", "영업수익"],
    "cost_of_sales": ["매출원가", "영업비용"],
    "gross_profit": ["매출총이익", "매출총손익"],
    "sga": ["판매비와관리비", "판매비와 일반관리비"],
    "operating_profit": ["영업이익", "영업이익(손실)"],
    "profit_before_tax": ["법인세비용차감전순이익", "법인세비용차감전순이익(손실)"],
    "net_income": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
    "current_assets": ["유동자산"],
    "noncurrent_assets": ["비유동자산"],
    "total_assets": ["자산총계"],
    "current_liabilities": ["유동부채"],
    "noncurrent_liabilities": ["비유동부채"],
    "total_liabilities": ["부채총계"],
    "total_equity": ["자본총계"],
    "cash": ["현금및현금성자산", "현금 및 현금성자산"],
    "receivables": ["매출채권", "매출채권및기타채권", "매출채권 및 기타유동채권"],
    "inventory": ["재고자산"],
    "interest_expense": ["이자비용"],
    "operating_cash_flow": ["영업활동현금흐름"],
    "investing_cash_flow": ["투자활동현금흐름"],
    "financing_cash_flow": ["재무활동현금흐름"],
    "depreciation_amortization": ["감가상각비", "감가상각비와무형자산상각비"],
    "interest_bearing_debt": ["단기차입금", "장기차입금", "유동성장기부채"],
}

def api_get(endpoint, params, api_key):
    p = dict(params)
    p["crtfc_key"] = api_key
    response = requests.get(f"{BASE}/{endpoint}", params=p, timeout=TIMEOUT)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"OpenDART returned non-JSON for {endpoint}")
    status = payload.get("status")
    if status not in (None, "000", "013"):
        raise RuntimeError(f"OpenDART {endpoint}: {payload.get('status')} {payload.get('message')}")
    return payload

def as_number(value):
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s in ("-", "—", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def fetch_statement(year, reprt_code, api_key):
    payload = api_get("fnlttSinglAcntAll.json", {
        "corp_code": CORP_CODE, "bsns_year": str(year),
        "reprt_code": reprt_code, "fs_div": "CFS"
    }, api_key)
    rows = payload.get("list", [])
    if not rows and payload.get("status") == "013":
        payload = api_get("fnlttSinglAcntAll.json", {
            "corp_code": CORP_CODE, "bsns_year": str(year),
            "reprt_code": reprt_code, "fs_div": "OFS"
        }, api_key)
        rows = payload.get("list", [])
    return rows

def extract_values(rows):
    found = {}
    # Prefer the current-period value; preserve account IDs/names for fallback.
    for metric, aliases in ACCOUNT_ALIASES.items():
        candidates = []
        for row in rows:
            name = (row.get("account_nm") or "").strip()
            if name in aliases:
                candidates.append(row)
        if metric in ("interest_bearing_debt",):
            vals = [as_number(r.get("thstrm_amount")) for r in candidates]
            vals = [v for v in vals if v is not None]
            found[metric] = sum(vals) if vals else None
        else:
            chosen = candidates[0] if candidates else None
            found[metric] = as_number(chosen.get("thstrm_amount")) if chosen else None
    return found

def ratio(n, d, scale=1.0):
    if n is None or d in (None, 0):
        return None
    return n / d * scale

def collect(start_year, end_year, api_key):
    records = []
    for year in range(start_year, end_year + 1):
        for period, code in REPORTS:
            try:
                rows = fetch_statement(year, code, api_key)
                if not rows:
                    print(f"INFO: no statement rows for {year} {period}")
                    continue
                v = extract_values(rows)
                record = {"company": "SK hynix", "corp_code": CORP_CODE,
                          "fiscal_year": year, "period": period,
                          "report_code": code, "statement_scope": "CFS"}
                record.update(v)
                record["gross_profit"] = record.get("gross_profit")
                if record["gross_profit"] is None and record.get("revenue") is not None and record.get("cost_of_sales") is not None:
                    record["gross_profit"] = record["revenue"] - record["cost_of_sales"]
                record["revenue_growth_pct"] = None
                record["gross_margin_pct"] = ratio(record.get("gross_profit"), record.get("revenue"), 100)
                record["operating_margin_pct"] = ratio(record.get("operating_profit"), record.get("revenue"), 100)
                record["net_margin_pct"] = ratio(record.get("net_income"), record.get("revenue"), 100)
                record["current_ratio_pct"] = ratio(record.get("current_assets"), record.get("current_liabilities"), 100)
                record["debt_to_equity_pct"] = ratio(record.get("total_liabilities"), record.get("total_equity"), 100)
                record["equity_ratio_pct"] = ratio(record.get("total_equity"), record.get("total_assets"), 100)
                record["debt_to_assets_pct"] = ratio(record.get("total_liabilities"), record.get("total_assets"), 100)
                record["interest_coverage"] = ratio(record.get("operating_profit"), record.get("interest_expense"))
                record["total_asset_turnover"] = ratio(record.get("revenue"), record.get("total_assets"))
                record["cfo_to_net_income"] = ratio(record.get("operating_cash_flow"), record.get("net_income"))
                record["fcf_proxy"] = None
                # CAPEX is not consistently standardized in this endpoint; investing cash flow is not equivalent to CAPEX.
                record["roa_pct"] = None
                record["roe_pct"] = None
                record["ebitda_margin_pct"] = None
                record["net_debt_to_ebitda"] = None
                record["dso_days"] = None
                record["dio_days"] = None
                record["dpo_days"] = None
                record["ccc_days"] = None
                record["source"] = "OpenDART fnlttSinglAcntAll.json"
                records.append(record)
                print(f"OK: {year} {period}")
            except Exception as exc:
                print(f"WARN: {year} {period}: {exc}", file=sys.stderr)
    if not records:
        raise RuntimeError("No statements collected. Check DART_API_KEY, network, and API availability.")
    df = pd.DataFrame(records)
    df = df.sort_values(["fiscal_year", "period"])
    # Growth compares same period's revenue, and only when both values are available.
    for idx, row in df.iterrows():
        prior = df[(df["fiscal_year"] == row["fiscal_year"] - 1) &
                   (df["period"] == row["period"])]
        if not prior.empty:
            old = prior.iloc[-1].get("revenue")
            new = row.get("revenue")
            if pd.notna(old) and old != 0 and pd.notna(new):
                df.loc[idx, "revenue_growth_pct"] = (new / old - 1) * 100
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Merge prior normalized data so temporarily unavailable older filings are not deleted.
    # Older template CSVs may use raw OpenDART columns and are not compatible with this schema.
    if OUT.exists():
        try:
            old = pd.read_csv(OUT)
            required_keys = {"fiscal_year", "period"}
            if required_keys.issubset(old.columns) and not old.empty:
                df = pd.concat([old, df], ignore_index=True, sort=False)
                df = df.drop_duplicates(["fiscal_year", "period"], keep="last")
                df = df.sort_values(["fiscal_year", "period"])
            else:
                print("INFO: existing CSV uses a legacy/empty schema; replacing it with normalized records.")
        except Exception as exc:
            print(f"WARN: could not merge existing CSV ({exc}); replacing it with fresh normalized records.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(df)} normalized rows to {OUT}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=__import__("datetime").date.today().year)
    args = parser.parse_args()
    key = os.getenv("DART_API_KEY")
    if not key:
        raise SystemExit("Set DART_API_KEY as an environment variable or GitHub Actions secret.")
    collect(args.start_year, args.end_year, key)
