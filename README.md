[![🔗 대시보드 바로가기](https://img.shields.io/badge/%F0%9F%94%97%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C-%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-315EFB?style=for-the-badge&logo=github&logoColor=white)](https://hsc-class02.github.io/jh_skhynix/)

# SK hynix DART Financial Agent

OpenDART 정기공시를 수집하고 재무제표 주요 계정과 재무비율을 계산해 GitHub Pages 대시보드에 게시하는 프로젝트입니다.

- **대시보드:** https://hsc-class02.github.io/jh_skhynix/
- **저장소:** https://github.com/HSC-Class02/jh_skhynix
- **기업 코드:** `00164779` (SK hynix)
- **수집 대상:** 사업보고서(11011), 반기보고서(11012), 1분기보고서(11013), 3분기보고서(11014)
- **수집 시작 연도:** 2010년
- **자동 업데이트:** 매월 1일 09:20 KST (GitHub Actions, 수동 실행 가능)

## API 키 설정

1. [OpenDART](https://opendart.fss.or.kr/)에서 이용 신청 후 인증키를 발급받습니다.
2. GitHub 저장소의 **Settings → Secrets and variables → Actions → New repository secret**으로 이동합니다.
3. Name에 `DART_API_KEY`, Secret에 발급받은 키를 입력하고 저장합니다. 키를 코드나 README에 직접 쓰지 마세요.
4. 이 ZIP은 업로드 편의를 위해 `.github` 같은 hidden 경로를 포함하지 않습니다. 저장소에서 **Add file → Create new file**을 선택해 `.github/workflows/update-and-deploy.yml` 경로를 만들고 `workflow_templates/update-and-deploy.yml`의 내용을 붙여넣어 커밋합니다. 같은 방식으로 `workflow_templates/validate.yml`도 `.github/workflows/validate.yml`에 추가합니다.
6. **Actions → Update DART data and deploy dashboard → Run workflow**로 첫 실행을 시작합니다.
7. 첫 실행이 성공하면 `docs/data/financials.json`, `data/processed/financial_statement_lines.csv`, `data/report_index.csv`가 갱신되고 Pages가 배포됩니다.

## GitHub Pages / About 설정

- **Settings → Pages → Build and deployment**에서 Source를 **GitHub Actions**로 선택합니다.
- 저장소 메인 페이지 오른쪽 **About → 톱니바퀴(Edit repository details)**에서 Website에 `https://hsc-class02.github.io/jh_skhynix/`를 입력하고 저장합니다.
- README 맨 위 배지는 Pages 주소로 연결됩니다. 저장소가 다른 소유자/이름으로 변경되면 URL도 함께 수정해야 합니다.

## 분석 지표

첨부된 「재무제표 및 재무비율 실무 가이드」의 지표 체계를 반영했습니다.

- **규모/손익:** 매출액, 매출총이익, 판매비와관리비, 영업이익, 세전이익, 당기순이익, 지배주주순이익
- **재무상태:** 총자산, 현금및현금성자산, 매출채권, 재고자산, 총부채, 이자부차입금 추정, 유동부채, 자본총계
- **현금흐름/투자:** 영업·투자·재무활동현금흐름, CAPEX 추정, FCF 추정, EBITDA 추정, 순차입금 추정
- **수익성:** 매출총이익률, 영업이익률, 순이익률, EBITDA 마진, 연간 ROA·ROE
- **유동성/안정성:** 유동비율, 부채비율, 자기자본비율, 차입금의존도 추정, 이자보상배율
- **현금전환/성장/효율:** CFO/순이익, 매출증가율, 총자산회전율, 순차입금/EBITDA 추정

일부 항목은 OpenDART 계정과목 명칭이 재무제표 표시 방식에 따라 달라질 수 있습니다. `data/processed/financial_statement_lines.csv`의 원 계정과 대조해 산출값을 확인하세요. 연간 ROA·ROE·총자산회전율은 전년도 연간 잔액과 당해 연간 잔액의 평균을 사용합니다. 분기·반기 ROA/ROE는 기간 길이 및 누적 손익의 차이로 왜곡될 수 있어 계산하지 않습니다. DSO/DIO/DPO/CCC는 평균 매출채권·재고·매입채무 및 매출원가/외상매입액의 계정 대응을 추가 검증해야 하므로 현재 자동 산출하지 않습니다. 주가 기반 PER/PBR/EV·EBITDA도 단일 공시 API만으로 계산할 수 없어 기본 산출 테이블에서 자동 계산하지 않습니다. 주가 기반 비율을 추가하려면 가격·주식수·기업가치의 별도 데이터 소스가 필요합니다.

## 2010년부터의 자료 범위 — 중요

- **2010~2014:** 공시 목록을 수집해 접수번호, 보고서명, 접수일, 원문 링크를 보존합니다. OpenDART의 구조화 재무제표 API가 제공하지 않는 기간의 수치를 API가 제공한 것처럼 만들지 않습니다.
- **2015년 이후:** OpenDART `fnlttSinglAcntAll.json`으로 연결재무제표(CFS)를 우선 수집합니다. 해당 API에서 자료가 없는 기간/항목은 빈 값으로 둡니다.
- 보고서 원문 ZIP 저장은 `config.json`에서 기본 활성화되어 있습니다. 각 원문 ZIP은 20MB 이하인 경우 `data/raw_reports/<연도>/` 아래 저장됩니다. 저장소 용량을 줄이려면 `download_raw_reports`를 `false`로 바꾸세요. 다운로드한 ZIP은 `data/raw_reports/<연도>/` 아래 저장됩니다. 원문 파일이 매우 커지면 GitHub 저장소 용량 제한을 고려해 별도 저장소/아티팩트 보관 방식을 사용하세요.

## 국내 Peer firms

| 기업 | 종목코드 | 비교 관계 | 주의사항 |
|---|---:|---|---|
| 삼성전자 | 005930 | 메모리 반도체 직접 경쟁사 | 종합 전자기업이라 사업 포트폴리오 차이 존재 |
| 한미반도체 | 042700 | 반도체 후공정 장비 인접 peer | 메모리 제조사가 아닌 장비업체 |
| DB하이텍 | 000990 | 파운드리 인접 peer | 사업모델/마진 구조가 다름 |
| HPSP | 403870 | 반도체 공정 장비 인접 peer | 장비기업이므로 밸류에이션 직접 비교 주의 |

국내 상장사 중 SK하이닉스와 동일하게 메모리 반도체를 핵심 사업으로 하는 기업은 제한적입니다. 따라서 삼성전자를 직접 경쟁사로, 나머지는 반도체 밸류체인 인접기업으로 표시합니다. 동일 업종 peer가 아닌 기업 간 PER/EV 배수는 기계적으로 비교하지 마세요.

## Workflow 템플릿 설치 및 문제 해결

ZIP에는 hidden 경로를 제외했기 때문에 GitHub Actions가 자동 인식하는 `.github/workflows/` 디렉터리는 포함되어 있지 않습니다. `workflow_templates/`의 두 YAML 파일을 README의 안내대로 `.github/workflows/` 경로에 각각 생성해야 자동 실행됩니다. 저장소에서 해당 경로를 만들 때 점(.)으로 시작하는 폴더명을 정확히 입력하세요.


- `DART_API_KEY` secret 이름/값 확인 (키를 로그에 출력하지 마세요).
- 저장소의 **Actions** 탭에서 실패한 job을 열어 실제 API 오류 메시지를 확인합니다.
- **Settings → Pages**에서 Source가 GitHub Actions인지 확인합니다.
- `contents: write`, `pages: write`, `id-token: write` 권한이 허용되어 있는지 확인합니다.
- 저장소 기본 브랜치가 `main`이 아니라면 `.github/workflows/update-and-deploy.yml`의 `branches: [main]`을 기본 브랜치명으로 변경합니다.

## 로컬 실행

```bash
python -m pip install -r requirements.txt
# macOS/Linux
export DART_API_KEY="발급받은_키"
python scripts/update_data.py
```

Windows PowerShell:

```powershell
$env:DART_API_KEY="발급받은_키"
python scripts/update_data.py
```

## 산출물

- `data/report_index.csv`: 2010년 이후 정기공시 목록과 DART 원문 링크
- `data/processed/financial_statement_lines.csv`: API에서 가져온 원 계정과목/금액
- `data/processed/financials.json`: 지표 산출 결과
- `docs/data/financials.json`: 대시보드 데이터
- `docs/index.html`: 반응형 대시보드

> 참고: 본 프로젝트는 교육·분석용 도구이며 투자 권유가 아닙니다. 재무비율 정의와 분모/분자 기준은 기업의 공시 방식 및 분석 목적에 따라 달라질 수 있습니다.
