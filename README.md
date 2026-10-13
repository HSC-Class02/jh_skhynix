# SK hynix DART Financial Dashboard

[![🔗 대시보드 바로가기](https://img.shields.io/badge/🔗-대시보드%20바로가기-2563eb?style=for-the-badge)](https://hsc-class02.github.io/jh_skhynix/)

OpenDART로 SK하이닉스(000660)의 2010년 이후 사업보고서·반기보고서·1분기·3분기 보고서 재무수치를 수집하고 재무비율을 분석합니다. 제공된 「재무제표 및 재무비율 실무 가이드」의 분석 흐름인 매출 성장 → 이익률 → 현금흐름 → 차입 부담 → 투자수익률을 반영했습니다.

## 설치 및 배포
1. 이 ZIP의 **모든 파일과 폴더**를 `https://github.com/HSC-Class02/jh_skhynix` 저장소 루트에 업로드/커밋합니다.
2. https://opendart.fss.or.kr/ 에서 API 인증키를 발급합니다.
3. 저장소 **Settings → Secrets and variables → Actions → New repository secret** 에 `DART_API_KEY`라는 이름으로 인증키를 저장합니다. API 키를 코드에 직접 입력하거나 공개하지 마세요.
4. `workflow-template/update.yml`을 `.github/workflows/update.yml`로 복사해 커밋합니다. ZIP에서 숨김 파일을 제외했기 때문에 workflow 템플릿은 일반 폴더에 제공됩니다. 최종 저장소 경로는 반드시 `.github/workflows/update.yml`이어야 합니다.
5. **Settings → Pages → Build and deployment**에서 `Deploy from a branch`, Branch `main`, Folder `/docs`를 선택하고 저장합니다.
6. **Actions → Update DART financial data → Run workflow**로 최초 수집을 실행합니다. 2010년 이후 전체 백필은 API 처리량에 따라 시간이 걸릴 수 있습니다.
7. 배포 URL은 보통 `https://hsc-class02.github.io/jh_skhynix/`입니다. 실제 URL은 Settings → Pages에서 확인하세요.
8. 저장소 메인 화면 오른쪽 **About → Edit repository details**에서 Website에 Pages URL을 넣으면 오른쪽 About 링크가 추가됩니다.

## 월간 자동 업데이트
Workflow는 매월 1일 UTC 00:17에 실행됩니다(한국시간 09:17). GitHub Actions 예약 실행은 부하에 따라 지연될 수 있으나, 매월 1일에 실행되도록 설정되어 있습니다. 수동 실행도 지원합니다.

## 데이터와 지표
- `data/financials.csv`: 원 계정명과 공시 금액
- `data/financials.json`: 저장소 내 정규화 데이터
- `docs/data/financials.json`: GitHub Pages에서 읽는 대시보드 데이터
- `data/reports.csv`: 수집된 보고서 기록
- `docs/index.html`: GitHub Pages dashboard
- `scripts/fetch_dart.py`: OpenDART 수집
- `scripts/build_dashboard.py`: 지표 계산 및 대시보드 갱신

대시보드에는 매출, 매출총이익, 영업이익, 순이익, 총자산, 현금, 매출채권, 재고, 총부채, 자본, CFO/CFI/CFF, FCF 및 매출성장률·마진·유동비율·부채비율·자기자본비율·ROA·ROE·자산회전율·CFO/순이익·순차입금을 표시합니다. 공시 계정명이 과거 연도와 다르면 일부 값이 비어 있을 수 있습니다. 분기보고서 손익 금액은 누적 기준일 수 있으므로 분기 단독 실적과 혼동하지 마세요. ROA·ROE는 평균 자산·자본이 있을 때만 계산합니다. PER/PBR/EV/EBITDA, 주가 기반 지표, ROIC-WACC는 별도 시장 데이터/가정이 필요해 임의로 생성하지 않습니다.

## 국내 Peer Firms
| 기업 | 종목코드 | 비교 이유 |
|---|---:|---|
| 삼성전자 | 005930 | 메모리 반도체 및 종합 전자·반도체 |
| 한미반도체 | 042700 | 반도체 후공정 장비 |
| 리노공업 | 058470 | 반도체 테스트 부품·소켓 |
| 원익IPS | 240810 | 반도체 제조 장비 |
| DB하이텍 | 000990 | 파운드리·반도체 제조 |
| 이오테크닉스 | 039030 | 반도체 레이저 장비 |

Peer firms는 참고 비교군이며 사업 모델이 완전히 같지는 않습니다. 특히 삼성전자는 사업 범위가 넓고 장비·부품 기업은 수익구조가 다르므로 직접 순위 비교에 주의하세요.
