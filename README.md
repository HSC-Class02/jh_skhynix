# SK hynix DART Financial Dashboard

[![Dashboard](https://img.shields.io/badge/%F0%9F%94%97%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C-%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-2563eb?style=for-the-badge)](https://hsc-class02.github.io/jh_skhynix/)

SK hynix OpenDART financial-data collection and analysis project. It collects annual, half-year, and quarterly financial statements from 2010 onward, calculates key financial ratios, and publishes a static dashboard through GitHub Pages.

## Included
- OpenDART API collector (`src/collect_dart.py`)
- Normalized CSV output (`data/financials.csv`)
- Dashboard with summary figures, trend charts, and annual / half-year / quarterly tables (`index.html`)
- Korean semiconductor/technology peer-firm reference table
- Workflow generator (`setup_workflow.py`) to create GitHub Actions workflows after extraction

> ZIP delivery intentionally contains no dotfiles. Run `python setup_workflow.py` to generate `.github/workflows/update.yml` and `.github/workflows/pages.yml`.

## 1. Install and configure
1. Extract this ZIP into the root of `HSC-Class02/jh_skhynix`.
2. Install Python 3.11 or newer.
3. Run `pip install -r requirements.txt`.
4. Create an OpenDART API key at https://opendart.fss.or.kr/ .
5. In GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `DART_API_KEY`
   - Secret: your OpenDART API key
6. Run `python setup_workflow.py`.
7. Commit and push all files, including the generated `.github` directory.

## 2. Run a local collection
```bash
pip install -r requirements.txt
# Windows PowerShell:
$env:DART_API_KEY="YOUR_DART_API_KEY"
python src/collect_dart.py --start-year 2010
```
The collector writes `data/financials.csv`. Do not place the API key in source code or commit it.

## 3. GitHub Actions and monthly update
The generated update workflow runs on the first day of every month at 00:17 UTC (09:17 Korea time) and can also be started manually from **Actions → Update DART Financial Data → Run workflow**. It fetches reports from 2010 onward on each run and updates the CSV if values changed.

The Pages workflow publishes the repository root with GitHub Pages. In **Settings → Pages**, set **Build and deployment → Source: GitHub Actions**. The expected URL is:
https://hsc-class02.github.io/jh_skhynix/

GitHub Pages deployment and the repository About link cannot be changed from this ZIP alone; after pushing, verify the URL, then set the repository **About → Website** field to the dashboard URL. The README badge already points to that expected URL.

## 4. Data definitions and caveats
- OpenDART statement API: `fnlttSinglAcntAll.json`.
- Report codes: annual `11011`, half-year `11012`, Q1 `11013`, Q3 `11014`. Q4 is derived only when comparable annual and nine-month cumulative values exist; otherwise it is left blank.
- Income statement and cash-flow values from DART are often year-to-date cumulative in Q1/H1/Q3 filings. The dashboard labels them as reported cumulative figures rather than silently converting them to standalone quarter values.
- Ratio fields are calculated only when required inputs exist. EBITDA, interest-bearing debt, CAPEX, market price, and some working-capital inputs may not be consistently available in the standardized statement API. Unsupported ratios remain blank rather than fabricated.
- Market valuation ratios (PER, PBR, EV/EBITDA, FCF yield) require market-price/share-count/enterprise-value data and are not inferred from accounting statements alone.
- Consolidated (`CFS`) statements are preferred; separate (`OFS`) is used only when consolidated data is unavailable.
- Data availability depends on what OpenDART exposes for each company, filing, and year. Check filing-level originals before making investment decisions.

## 5. Main metrics
**Financial statements:** revenue, cost of sales, gross profit, SG&A, operating profit, profit before tax, net income, current/non-current assets and liabilities, total assets/liabilities/equity, cash and cash equivalents, inventories, receivables, interest-bearing debt where available, operating/investing/financing cash flows, CAPEX proxy.

**Ratios:** revenue growth, gross margin, operating margin, net margin, EBITDA margin where available, ROA, ROE, current ratio, debt-to-equity, equity ratio, debt-to-assets, interest coverage, net debt/EBITDA, total asset turnover, DSO, DIO, DPO, CCC, CFO/net income, and FCF proxy.

## 6. Peer firms (reference set)
The dashboard and README list these Korean listed semiconductor / semiconductor-equipment companies as a starting peer set:
- Samsung Electronics
- Hanmi Semiconductor
- Leeno Industrial
- Wonik IPS
- DB HiTek
- EO Technics

They differ in scale and business mix; use business-segment and accounting-policy context when comparing margins and valuation.
