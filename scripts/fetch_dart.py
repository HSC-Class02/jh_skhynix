#!/usr/bin/env python3
"""Fetch SK hynix statements from OpenDART; preserve old rows when API has no result."""
import csv, io, os, sys, time, zipfile
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; API="https://opendart.fss.or.kr/api"
KEY=os.getenv("DART_API_KEY","").strip(); START=int(os.getenv("START_YEAR","2010"))
END=int(os.getenv("END_YEAR",str(__import__("datetime").date.today().year)))
REPORTS=[("11011","annual"),("11012","half-year"),("11013","quarterly"),("11014","quarterly")]
S=requests.Session(); S.headers["User-Agent"]="skhynix-dart-dashboard/1.0"
def corp_code():
    r=S.get(API+"/corpCode.xml",params={"crtfc_key":KEY},timeout=90); r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name=next((n for n in z.namelist() if n.lower().endswith(".xml")),None)
        if not name: raise RuntimeError("corpCode.zip에서 XML을 찾지 못했습니다")
        import xml.etree.ElementTree as ET
        root=ET.fromstring(z.read(name))
    for item in root.findall(".//list"):
        if (item.findtext("stock_code") or "").strip()=="000660":
            return (item.findtext("corp_code") or "").strip()
    raise RuntimeError("SK하이닉스 종목코드 000660을 찾지 못했습니다")
def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def get_json(endpoint,params):
    r=S.get(API+"/"+endpoint,params=params,timeout=60); r.raise_for_status(); obj=r.json()
    if obj.get("status") not in ("000","013",None):
        raise RuntimeError(f"OpenDART {obj.get('status')}: {obj.get('message','')}")
    return obj
def main():
    if not KEY: sys.exit("ERROR: DART_API_KEY secret이 설정되지 않았습니다.")
    DATA.mkdir(exist_ok=True); corp=corp_code()
    af=["company","stock_code","corp_code","bsns_year","reprt_code","report_type","fs_div","sj_div","account_id","account_nm","thstrm_nm","thstrm_amount","frmtrm_nm","frmtrm_amount","bfefrmtrm_nm","bfefrmtrm_amount","currency","source"]
    keyf=("bsns_year","reprt_code","fs_div","account_id","account_nm")
    rows={tuple(r.get(k,"") for k in keyf):r for r in read_csv(DATA/"financials.csv")}
    rf=["bsns_year","reprt_code","report_type","record_count","status","message","retrieved_at"]
    reports={(r.get("bsns_year"),r.get("reprt_code"),r.get("report_type")):r for r in read_csv(DATA/"reports.csv")}
    errors=[]
    from datetime import datetime,timezone
    for year in range(START,END+1):
        for code,kind in REPORTS:
            try:
                obj=get_json("fnlttSinglAcntAll.json",{"crtfc_key":KEY,"corp_code":corp,"bsns_year":str(year),"reprt_code":code,"fs_div":"CFS"})
                items=obj.get("list") or []
                if not items: continue
                for x in items:
                    row={"company":"SK hynix","stock_code":"000660","corp_code":corp,"bsns_year":str(year),"reprt_code":code,"report_type":kind,"fs_div":x.get("fs_div","CFS"),"sj_div":x.get("sj_div",""),"account_id":x.get("account_id",""),"account_nm":x.get("account_nm",""),"thstrm_nm":x.get("thstrm_nm",""),"thstrm_amount":x.get("thstrm_amount",""),"frmtrm_nm":x.get("frmtrm_nm",""),"frmtrm_amount":x.get("frmtrm_amount",""),"bfefrmtrm_nm":x.get("bfefrmtrm_nm",""),"bfefrmtrm_amount":x.get("bfefrmtrm_amount",""),"currency":"KRW","source":"OpenDART fnlttSinglAcntAll"}
                    rows[tuple(row.get(k,"") for k in keyf)]=row
                reports[(str(year),code,kind)]={"bsns_year":str(year),"reprt_code":code,"report_type":kind,"record_count":str(len(items)),"status":obj.get("status","000"),"message":obj.get("message",""),"retrieved_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
                print(f"{year} {kind}: {len(items)} accounts"); time.sleep(.15)
            except Exception as e:
                errors.append(f"{year}/{code}: {e}"); print(f"WARN {year}/{code}: {e}",file=sys.stderr)
    allrows=sorted(rows.values(),key=lambda r:(r.get("bsns_year",""),r.get("reprt_code",""),r.get("fs_div",""),r.get("sj_div",""),r.get("account_nm","")))
    with (DATA/"financials.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=af); w.writeheader(); w.writerows(allrows)
    with (DATA/"reports.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rf); w.writeheader(); w.writerows(sorted(reports.values(),key=lambda r:(r["bsns_year"],r["reprt_code"])))
    print(f"Saved {len(allrows)} account rows; warnings={len(errors)}")
    if errors and not allrows: raise RuntimeError("모든 API 수집이 실패했습니다: "+"; ".join(errors[:5]))
if __name__=="__main__": main()
