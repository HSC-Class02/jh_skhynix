# SK hynix DART Financial Agent + GitHub Dashboard

> OpenDART → GitHub Actions → 재무수치 정규화/재무비율 계산 → GitHub Pages Dashboard

<p align="left">
  <a href="https://hsc-class02.github.io/jh_skhynix/">
    <img src="https://img.shields.io/badge/%F0%9F%94%97%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-63B9E8?style=for-the-badge&labelColor=173B5B" alt="대시보드 바로가기">
  </a>
</p>

## 1. 프로젝트 목적

SK hynix(고유번호 `00164779`)의 DART 정기보고서를 자동 수집하고, 주요 재무수치와 재무비율을 계산해 GitHub에 저장합니다. 대시보드는 GitHub Pages로 배포되며, 매월 1일 자동 실행됩니다.

### 수집 대상

- 사업보고서: `11011`
- 반기보고서: `11012`
- 1분기보고서: `11013`
- 3분기보고서: `11014`
- 연결재무제표(`CFS`) 우선, 데이터가 없으면 별도재무제표(`OFS`) fallback
- 보고서 원문 링크와 접수번호를 `data/processed/filings.csv`에 보관
- API 원응답은 `data/raw/`에 연도별로 보관

## 2. 중요: 2010년 데이터에 대한 OpenDART API 범위

사용자가 요청한 시작연도는 2010년으로 설정되어 있습니다. 다만 OpenDART의 `fnlttSinglAcntAll` 공식 개발가이드는 **재무정보를 2015년 이후부터 제공**한다고 명시합니다. 따라서 이 프로젝트는 2015년 이후의 재무수치를 OpenDART 재무 API로 자동 수집하고, 2010~2014 구간은 임의의 값을 생성하지 않습니다.

2010~2014까지 동일한 구조로 채우려면 DART의 과거 원문 보고서(HTML/XML/XBRL)의 재무제표 표를 별도 legacy parser로 일회성 backfill한 뒤 `data/processed/legacy_2010_2014.csv`로 합치는 방식이 안전합니다. 이 저장소는 그 구간을 명시적으로 표시하도록 설계했습니다.

## 3. 재무분석 지표

첨부된 `재무제표 및 재무비율 실무 가이드`의 핵심 수치와 분석 흐름을 기준으로 구현했습니다.

### 주요 재무수치

- 재무상태표: 총자산, 현금및현금성자산, 매출채권, 재고자산, 유형자산, 유동자산, 유동부채, 총부채, 이자부차입금, 자본총계
- 손익계산서: 매출액, 매출총이익, 매출원가, 판매비와관리비, 영업이익, 세전이익, 당기순이익, 지배주주순이익, 이자비용, EBITDA(공시 계정이 있는 경우)
- 현금흐름표: 영업활동현금흐름, 투자활동현금흐름, 재무활동현금흐름, CAPEX 관련 유형·무형자산 취득
- 파생지표: 순차입금, FCF

### 재무비율

- 수익성: 매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE
- 유동성/안정성: 유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도 성격의 지표, 이자보상배율, 순차입금/EBITDA
- 활동성: 총자산회전율, DSO, DIO, DPO, CCC
- 성장성/현금전환: 매출증가율, CFO/순이익

분모가 0이거나 필요한 계정이 없으면 해당 지표는 `null`로 남깁니다. 연결/별도 기준을 섞지 않도록 CFS를 우선합니다.

## 4. 분기 데이터 처리

OpenDART의 정기보고서 API는 분·반기 손익계산서에 `당기금액`과 `당기누적금액`을 제공합니다. 따라서 저장된 Q1/H1/Q3/Annual 누적 데이터를 이용해 다음과 같이 실제 분기 금액을 구성합니다.

- Q1 = Q1 누적
- Q2 = H1 누적 − Q1 누적
- Q3 = Q3 누적 − H1 누적
- Q4 = Annual − Q3 누적

재무상태표 계정은 보고시점의 기말잔액을 사용합니다.

## 5. GitHub Actions 자동화

워크플로우 파일은 다음 경로에 있습니다.

`\.github/workflows/update_and_deploy.yml`

스케줄:

```text
매월 1일 00:00 UTC = 매월 1일 09:00 KST
```

또한 `workflow_dispatch`를 제공하므로 첫 배포나 수동 재실행이 가능합니다.

워크플로우는 한 번의 실행에서 다음을 모두 수행합니다.

1. repository checkout
2. Python 3.12 설정
3. dependencies 설치
4. OpenDART 데이터 수집
5. 재무비율 계산
6. `data/` 변경사항 commit/push
7. GitHub Pages artifact 생성
8. GitHub Pages 배포

데이터 commit은 `data/**` 변경만 포함하므로 해당 commit이 다시 수집 workflow를 무한 실행시키지 않도록 `paths-ignore`를 적용했습니다.

## 6. OpenDART API Key 입력 방법

### ① OpenDART에서 인증키 발급

[OpenDART](https://opendart.fss.or.kr/)에서 인증키를 발급합니다.

### ② GitHub Repository Secret 등록

Repository → **Settings → Secrets and variables → Actions → New repository secret**

다음처럼 입력합니다.

| Name | Value |
|---|---|
| `DART_API_KEY` | 발급받은 40자리 OpenDART 인증키 |

**API 키를 Python 파일, README, CSV, Git commit에 직접 입력하지 마세요.**

기업코드는 이미 workflow에 다음과 같이 고정되어 있습니다.

```yaml
DART_CORP_CODE: '00164779'
```

## 7. GitHub Pages 배포 설정

Repository → **Settings → Pages** → Build and deployment → Source에서 **GitHub Actions**를 선택합니다.

그 다음 Actions → `DART update + GitHub Pages dashboard` → **Run workflow**를 한 번 실행합니다.

예상 dashboard 주소:

`https://hsc-class02.github.io/jh_skhynix/`

GitHub Pages가 처음 활성화된 뒤에는 workflow가 생성한 artifact를 이용해 자동 배포됩니다.

## 8. Repository About 영역에 Dashboard 링크 넣기

Repository → **About** 영역의 연필 아이콘 → Website에 다음 주소를 넣습니다.

`https://hsc-class02.github.io/jh_skhynix/`

README 최상단에는 이미 Dashboard badge를 넣어두었습니다. 현재 패키지에는 별도 숨김 이미지 파일 대신 Shields-style 배지를 사용했습니다.

## 9. Dashboard 구성

### 상단

- 매출액 / 영업이익 추세
- 주요 수익성 추세
- CFO / FCF 시각화
- 최신 매출증가율, 영업이익률, ROE, 순차입금/EBITDA KPI

### 하단

요청한 세 가지 표를 각각 제공합니다.

1. **Annual** — 사업보고서
2. **Half-year** — 반기보고서
3. **Quarterly** — Q1~Q4

그리고 최하단에 **국내 Peer Firms** 표를 제공합니다.

## 10. 국내 Peer Firms

Peer는 동일한 회사라고 가정하지 않고 사업의 겹침 정도에 따라 분류했습니다.

| 기업 | 코드 | 분류 | 주요 영역 |
|---|---:|---|---|
| Samsung Electronics | 005930 | 직접 메모리 peer | DRAM / NAND / 시스템LSI / 파운드리 |
| Hanmi Semiconductor | 042700 | HBM 생태계 peer | HBM TC bonder 등 후공정 장비 |
| DB HiTek | 000990 | 반도체 제조 peer | 특화 파운드리 |
| Wonik IPS | 240810 | 반도체 장비 peer | 증착 및 반도체 공정장비 |

이 표는 투자 판단을 위한 순위가 아니라, SK hynix의 사업 및 공급망을 비교할 때 사용할 국내 비교군을 구분해 놓은 것입니다.

## 11. 폴더 구조

```text
jh_skhynix/
├─ .github/
│  └─ workflows/
│     └─ update_and_deploy.yml
├─ assets/
│  ├─ app.js
│  └─ style.css
├─ data/
│  ├─ raw/
│  └─ processed/
│     ├─ filings.csv
│     ├─ financial_raw.csv       # 첫 실행 후 생성
│     ├─ ratios.csv              # 첫 실행 후 생성
│     ├─ ratios.json
│     ├─ quarterly_data.json
│     └─ metadata.json
├─ scripts/
│  └─ validate_data.py
├─ src/
│  └─ dart_agent.py
├─ index.html
├─ requirements.txt
└─ README.md
```

## 12. 로컬 테스트

Windows PowerShell 기준:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DART_API_KEY="여기에_키"
$env:DART_CORP_CODE="00164779"
$env:DART_START_YEAR="2010"
python src/dart_agent.py
python scripts/validate_data.py
```

## 13. 공식 참고자료

- OpenDART: https://opendart.fss.or.kr/
- OpenDART `fnlttSinglAcntAll`: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020
- GitHub Pages: https://docs.github.com/en/pages

## 14. 주의사항

- OpenDART API의 요청 제한에 따라 workflow가 실패할 경우 Actions 로그를 확인합니다.
- DART 계정/인증키는 공개 repository에 노출하지 않습니다.
- 재무비율은 보고서 표시 방식 및 계정명 변경에 영향을 받을 수 있으므로 `account_nm` 원문을 함께 저장합니다.
- CAPEX, EBITDA, 이자부차입금처럼 여러 계정의 합산 또는 기업별 공시 방식 차이가 있는 항목은 원천 계정을 함께 보관합니다.
- 재무비율 정의는 기업·기관별로 다를 수 있으므로 대시보드의 계산 정의를 고정해 추세 비교에 사용합니다.
