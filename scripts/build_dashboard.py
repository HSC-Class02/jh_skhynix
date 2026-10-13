#!/usr/bin/env python3
"""Normalize OpenDART account data and compute available ratios."""
import csv,json,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DOCS=ROOT/"docs"
ALIASES={
"revenue":["매출액","수익(매출액)","영업수익"],"gross_profit":["매출총이익","매출총이익(손실)"],
"operating_profit":["영업이익","영업이익(손실)"],"net_income":["당기순이익","당기순이익(손실)","분기순이익","반기순이익"],
"assets":["자산총계"],"current_assets":["유동자산"],"liabilities":["부채총계"],"current_liabilities":["유동부채"],"equity":["자본총계"],
"cash":["현금및현금성자산","현금 및 현금성자산"],"receivables":["매출채권","매출채권및기타채권","매출채권 및 기타채권"],
"inventory":["재고자산"],"ppe":["유형자산"],"short_borrowings":["단기차입금"],"long_borrowings":["장기차입금"],
"cost_of_sales":["매출원가"],"sga":["판매비와관리비"],"cfo":["영업활동현금흐름"],"cfi":["투자활동현금흐름"],
"cff":["재무활동현금흐름"],"capex":["유형자산의 취득","유형자산 취득","유형자산의취득"]}
PEERS=[
{"name":"삼성전자","ticker":"005930","reason":"메모리 반도체·종합 전자"},
{"name":"한미반도체","ticker":"042700","reason":"반도체 후공정 장비"},
{"name":"리노공업","ticker":"058470","reason":"반도체 테스트 부품·소켓"},
{"name":"원익IPS","ticker":"240810","reason":"반도체 제조 장비"},
{"name":"DB하이텍","ticker":"000990","reason":"파운드리·반도체 제조"},
{"name":"이오테크닉스","ticker":"039030","reason":"반도체 레이저 장비"}]
def norm(x): return re.sub(r"[\s()（）]","",str(x or "")).lower()
def number(x):
 s=str(x or "").strip().replace(",","").replace("△","-")
 try:return float(s) if s and s not in ("-","—") else None
 except:return None
def pct(a,b): return a/b*100 if a is not None and b not in (None,0) else None
def main():
 rows=[]
 with (DATA/"financials.csv").open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
 cfs=[r for r in rows if r.get("fs_div")=="CFS"]; chosen=cfs or [r for r in rows if r.get("fs_div")=="OFS"]
 groups={}
 for r in chosen:
  key=(r.get("bsns_year",""),r.get("reprt_code",""),r.get("report_type",""))
  g=groups.setdefault(key,{"year":int(r["bsns_year"]),"report_code":r["reprt_code"],"type":r["report_type"],"accounts":{},"account_labels":{}})
  name=norm(r.get("account_nm")); val=number(r.get("thstrm_amount"))
  if val is None: continue
  for k,aliases in ALIASES.items():
   if name in [norm(a) for a in aliases]:
    g["accounts"].setdefault(k,val); g["account_labels"].setdefault(k,r.get("account_nm",""))
 periods=sorted(groups.values(),key=lambda p:(p["year"],p["report_code"]))
 lookup={(p["year"],p["report_code"]):p for p in periods}
 for p in periods:
  a=p["accounts"]; old=lookup.get((p["year"]-1,p["report_code"]),{}).get("accounts",{})
  avg_assets=(a["assets"]+old["assets"])/2 if a.get("assets") is not None and old.get("assets") is not None else None
  avg_equity=(a["equity"]+old["equity"])/2 if a.get("equity") is not None and old.get("equity") is not None else None
  rev=a.get("revenue"); ni=a.get("net_income"); cfo=a.get("cfo"); capex=a.get("capex")
  p["revenue_growth_pct"]=pct(rev,old.get("revenue"))-100 if rev is not None and old.get("revenue") not in (None,0) else None
  p["gross_margin_pct"]=pct(a.get("gross_profit"),rev); p["operating_margin_pct"]=pct(a.get("operating_profit"),rev); p["net_margin_pct"]=pct(ni,rev)
  p["current_ratio_pct"]=pct(a.get("current_assets"),a.get("current_liabilities")); p["debt_ratio_pct"]=pct(a.get("liabilities"),a.get("equity")); p["equity_ratio_pct"]=pct(a.get("equity"),a.get("assets"))
  p["roa_pct"]=pct(ni,avg_assets); p["roe_pct"]=pct(ni,avg_equity); p["asset_turnover"]=rev/avg_assets if rev is not None and avg_assets not in (None,0) else None
  p["cfo_to_net_income_pct"]=pct(cfo,ni); p["fcf"]=cfo-abs(capex) if cfo is not None and capex is not None else None
  p["net_debt"]=(a.get("short_borrowings") or 0)+(a.get("long_borrowings") or 0)-(a.get("cash") or 0) if any(a.get(k) is not None for k in ("short_borrowings","long_borrowings","cash")) else None
 result={"company":"SK hynix","stock_code":"000660","accounting_basis":"CFS" if cfs else "OFS","periods":periods,"peers":PEERS,"generated_at":datetime.now().astimezone().isoformat(timespec="seconds")}
 (DATA/"financials.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 (DOCS/"data").mkdir(exist_ok=True)
 (DOCS/"data"/"financials.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
