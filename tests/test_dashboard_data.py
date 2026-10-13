import json
from pathlib import Path

def test_dashboard_json_is_valid():
    path = Path(__file__).resolve().parents[1] / 'docs' / 'data' / 'financials.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['corp_code'] == '00164779'
    assert 'periods' in data and 'filings' in data
    assert len(data['peer_firms']) >= 3
