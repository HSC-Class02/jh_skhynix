from pathlib import Path
import json

required = [
    Path('data/processed/metadata.json'),
    Path('data/processed/ratios.json'),
    Path('data/processed/quarterly_data.json'),
    Path('data/processed/filings.csv'),
]
for p in required:
    if not p.exists():
        raise SystemExit(f'Missing required generated file: {p}')

meta=json.loads(Path('data/processed/metadata.json').read_text(encoding='utf-8'))
assert meta['corp_code']=='00164779'
assert meta['api_financial_start_year']==2015
print('Validation passed:', meta)
