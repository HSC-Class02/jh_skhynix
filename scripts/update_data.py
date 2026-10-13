#!/usr/bin/env python3
"""Fetch SK hynix filings and structured financial statements from OpenDART."""
from __future__ import annotations
import csv, io, json, os, re, sys, time, zipfile
from datetime import datetime
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
KEY = os.getenv('DART_API_KEY', '').strip()
BASE = 'https://opendart.fss.or.kr/api'
DOCS = ROOT / 'docs'
DATA = DOCS / 'data'
PROCESSED = ROOT / 'data' / 'processed'
RAW = ROOT / 'data' / 'raw_reports'
for p in (DATA, PROCESSED, RAW): p.mkdir(parents=True, exist_ok=True)

if not KEY:
    print('ERROR: DART_API_KEY environment variable is missing.', file=sys.stderr)
    sys.exit(2)

session = requests.Session()
session.headers.update({'User-Agent': 'SKHynix-DART-Research-Agent/1.0'})

def get_json(endpoint: str, params: dict) -> dict:
    params = dict(params, crtfc_key=KEY)
    r = session.get(f'{BASE}/{endpoint}', params=params, timeout=60)
    r.raise_for_status()
    obj = r.json()
    status = obj.get('status')
    if status not in ('000', '013'):
        raise RuntimeError(f'{endpoint}: {obj.get("status")} {obj.get("message")}')
    return obj

def get_bytes(endpoint: str, params: dict) -> bytes:
    r = session.get(f'{BASE}/{endpoint}', params=dict(params, crtfc_key=KEY), timeout=120)
    r.raise_for_status()
    # OpenDART document API returns a ZIP on success; errors may be ZIP/XML/JSON.
    payload = r.content
    if not payload.startswith(b'PK'):
        raise RuntimeError(f'{endpoint} returned a non-ZIP response: {payload[:200]!r}')
    return payload

def report_matches(row: dict, year: int, report_code: str) -> bool:
    # list.json does not return reprt_code, so infer the regular-report type from report_nm.
    name = str(row.get('report_nm', '')).replace(' ', '')
    match = re.search(r'\((\d{4})[.\-/](\d{1,2})\)', name)
    month = int(match.group(2)) if match else None
    if report_code == '11011': return '사업보고서' in name
    if report_code == '11012': return '반기보고서' in name
    if report_code == '11013': return '분기보고서' in name and month == 3
    if report_code == '11014': return '분기보고서' in name and month == 9
    return False

def list_reports(year: int, report_code: str) -> list[dict]:
    rows=[]; page=1
    while True:
        obj=get_json('list.json', {'corp_code': CFG['corp_code'], 'bgn_de': f'{year}0101', 'end_de': f'{year}1231', 'pblntf_ty':'A', 'page_no':page, 'page_count':100})
        batch=obj.get('list', []) or []
        for row in batch:
            if row.get('corp_code') == CFG['corp_code'] and report_matches(row, year, report_code):
                rows.append(row)
        total=int(obj.get('total_page', 1) or 1)
        if page >= total: break
        page += 1
        time.sleep(0.15)
    return rows

def to_num(value):
    if value is None: return None
    s=str(value).replace(',', '').replace(' ', '').strip()
    if s in ('', '-', '—', 'N/A'): return None
    try: return float(s)
    except ValueError: return None

def fetch_statement(year: int, report_code: str) -> list[dict]:
    try:
        obj=get_json('fnlttSinglAcntAll.json', {'corp_code': CFG['corp_code'], 'bsns_year':str(year), 'reprt_code':report_code, 'fs_div':'CFS'})
        if obj.get('status') == '013': return []
        rows=[]
        for x in obj.get('list', []) or []:
            rows.append({
                'account_id': x.get('account_id',''), 'account_nm': x.get('account_nm',''),
                'sj_div': x.get('sj_div',''), 'sj_nm': x.get('sj_nm',''),
                'thstrm_nm': x.get('thstrm_nm',''), 'thstrm_amount': to_num(x.get('thstrm_amount')),
                'frmtrm_nm': x.get('frmtrm_nm',''), 'frmtrm_amount': to_num(x.get('frmtrm_amount')),
                'bfefrmtrm_nm': x.get('bfefrmtrm_nm',''), 'bfefrmtrm_amount': to_num(x.get('bfefrmtrm_amount')),
                'currency': x.get('currency','KRW'), 'year':year, 'report_code':report_code,
            })
        return rows
    except RuntimeError as e:
        # API may have no structured statements for older years or some filing types.
        print(f'NOTICE: no structured statement for {year}/{report_code}: {e}')
        return []

def first_value(rows, *names):
    targets={n.replace(' ','').lower() for n in names}
    for row in rows:
        nm=row.get('account_nm','').replace(' ','').lower()
        if nm in targets and row.get('thstrm_amount') is not None:
            return row['thstrm_amount']
    return None

def safe_div(a,b): return (a/b) if a is not None and b not in (None,0) else None

def extract_metrics(rows):
    # OpenDART labels vary by statement/accounting presentation; preserve source rows as well.
    revenue=first_value(rows,'매출액','수익(매출액)','영업수익')
    gross=first_value(rows,'매출총이익')
    sga=first_value(rows,'판매비와관리비','판매비와 관리비')
    op=first_value(rows,'영업이익','영업이익(손실)')
    pretax=first_value(rows,'법인세비용차감전순이익','법인세비용차감전순이익(손실)')
    net=first_value(rows,'당기순이익','당기순이익(손실)')
    owner_net=first_value(rows,'지배기업의 소유주에게 귀속되는 당기순이익','지배기업 소유주지분 순이익')
    assets=first_value(rows,'자산총계'); cash=first_value(rows,'현금및현금성자산','현금 및 현금성자산')
    receivables=first_value(rows,'매출채권','매출채권및기타채권','매출채권 및 기타채권')
    inventory=first_value(rows,'재고자산'); current_assets=first_value(rows,'유동자산')
    liabilities=first_value(rows,'부채총계'); current_liabilities=first_value(rows,'유동부채'); equity=first_value(rows,'자본총계')
    debt_st=first_value(rows,'단기차입금','유동성장기부채','유동성장기차입금') or 0
    debt_lt=first_value(rows,'장기차입금','사채','비유동성사채') or 0
    cfo=first_value(rows,'영업활동현금흐름','영업활동으로 인한 현금흐름')
    cfi=first_value(rows,'투자활동현금흐름','투자활동으로 인한 현금흐름')
    cff=first_value(rows,'재무활동현금흐름','재무활동으로 인한 현금흐름')
    interest=first_value(rows,'이자비용','금융원가')
    depreciation=first_value(rows,'감가상각비','감가상각비 및 무형자산상각비')
    amortization=first_value(rows,'무형자산상각비') or 0
    capex_ppe=first_value(rows,'유형자산의 취득','유형자산 취득')
    capex_int=first_value(rows,'무형자산의 취득','무형자산 취득') or 0
    capex=abs(capex_ppe or 0)+abs(capex_int)
    debt=(debt_st or 0)+(debt_lt or 0)
    ebitda=(op + (depreciation or 0) + amortization) if op is not None else None
    fcf=(cfo-capex) if cfo is not None else None
    return {
      'revenue':revenue,'gross_profit':gross,'sga':sga,'operating_income':op,'pretax_income':pretax,'net_income':net,'controlling_net_income':owner_net,
      'total_assets':assets,'cash_and_equivalents':cash,'accounts_receivable':receivables,'inventory':inventory,'current_assets':current_assets,
      'total_liabilities':liabilities,'interest_bearing_debt_estimate':debt,'current_liabilities':current_liabilities,'total_equity':equity,
      'operating_cash_flow':cfo,'investing_cash_flow':cfi,'financing_cash_flow':cff,'capex_estimate':capex,'free_cash_flow_estimate':fcf,'ebitda_estimate':ebitda,'interest_expense':interest,
      'gross_margin':safe_div(gross,revenue),'operating_margin':safe_div(op,revenue),'net_margin':safe_div(net,revenue),'ebitda_margin':safe_div(ebitda,revenue),
      'current_ratio':safe_div(current_assets,current_liabilities),'debt_to_equity':safe_div(liabilities,equity),'equity_ratio':safe_div(equity,assets),'debt_to_assets':safe_div(debt,assets),
      'interest_coverage':safe_div(op,interest),'net_debt_estimate':(debt-cash) if cash is not None else None,'cfo_to_net_income':safe_div(cfo,net),
      'revenue_growth':None,'roa':None,'roe':None,'total_asset_turnover':None,'net_debt_to_ebitda':safe_div((debt-cash) if cash is not None else None,ebitda)
    }

def write_json(path: Path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def main():
    index=[]; statement_rows=[]; periods=[]
    for year in range(int(CFG['start_year']), datetime.now().year+1):
        for period, code in [('annual','11011'),('half_year','11012'),('q1','11013'),('q3','11014')]:
            reports=list_reports(year,code)
            for rep in reports:
                rec={k:rep.get(k,'') for k in ['corp_name','report_nm','rcept_no','rcept_dt','flr_nm','rm']}
                rec.update({'year':year,'period':period,'report_code':code,'corp_code':CFG['corp_code'], 'report_url':f'https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rep.get("rcept_no","")}'})
                index.append(rec)
                if CFG.get('download_raw_reports'):
                    raw_path=RAW / str(year) / f'{rep.get("rcept_no")}.zip'; raw_path.parent.mkdir(parents=True,exist_ok=True)
                    if not raw_path.exists():
                        try:
                            payload=get_bytes('document.xml', {'rcept_no':rep['rcept_no']})
                            if len(payload) <= int(CFG.get('raw_report_max_mb',20))*1024*1024:
                                raw_path.write_bytes(payload)
                            else: print(f'SKIP large raw report {rep["rcept_no"]}: {len(payload)} bytes')
                        except Exception as e: print(f'NOTICE: raw report download failed {rep.get("rcept_no")}: {e}')
                time.sleep(0.1)
            # structured financial API starts in 2015; pre-2015 filings remain indexed for source traceability.
            if year >= 2015:
                rows=fetch_statement(year,code)
                if rows:
                    statement_rows.extend(rows)
                    metrics=extract_metrics(rows)
                    periods.append({'year':year,'period':period,'report_code':code,'report_date':next((r.get('rcept_dt') for r in reports),''),**metrics})
            time.sleep(0.1)
    # Add comparable-period growth and annual-only average-balance ratios.
    periods.sort(key=lambda p: (p['year'], {'q1':1,'half_year':2,'q3':3,'annual':4}.get(p['period'],0)))
    for p in periods:
        prev = next((x for x in periods if x['year'] == p['year']-1 and x['period'] == p['period']), None)
        if prev and prev.get('revenue') not in (None, 0) and p.get('revenue') is not None:
            p['revenue_growth'] = p['revenue'] / prev['revenue'] - 1
        if p['period'] == 'annual':
            prior_annual = next((x for x in periods if x['year'] == p['year']-1 and x['period'] == 'annual'), None)
            if prior_annual:
                avg_assets = ((p.get('total_assets') or 0) + (prior_annual.get('total_assets') or 0)) / 2
                avg_equity = ((p.get('total_equity') or 0) + (prior_annual.get('total_equity') or 0)) / 2
                p['roa'] = (p['net_income'] / avg_assets) if p.get('net_income') is not None and avg_assets else None
                p['roe'] = (p['net_income'] / avg_equity) if p.get('net_income') is not None and avg_equity else None
                p['total_asset_turnover'] = (p['revenue'] / avg_assets) if p.get('revenue') is not None and avg_assets else None
    # Preserve all source-level account lines and filing index.
    with (ROOT/'data'/'report_index.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['corp_name','report_nm','rcept_no','rcept_dt','flr_nm','rm','year','period','report_code','corp_code','report_url']
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(index)
    with (PROCESSED/'financial_statement_lines.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=list(statement_rows[0].keys()) if statement_rows else ['account_id','account_nm','sj_div','sj_nm','thstrm_nm','thstrm_amount','frmtrm_nm','frmtrm_amount','bfefrmtrm_nm','bfefrmtrm_amount','currency','year','report_code']
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(statement_rows)
    payload={'company':CFG['corp_name'],'corp_code':CFG['corp_code'],'updated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
             'data_note':'OpenDART structured financial statements are available from 2015 onward. Filings from 2010–2014 are indexed; they are not falsely populated with missing structured API values.',
             'filings':index,'periods':periods,'peer_firms':CFG['peer_firms'],'source':'OpenDART API','start_year':CFG['start_year']}
    write_json(DATA/'financials.json',payload)
    write_json(PROCESSED/'financials.json',payload)
    print(f'Completed: {len(index)} filing records, {len(statement_rows)} account rows, {len(periods)} period metric records.')

if __name__ == '__main__': main()
