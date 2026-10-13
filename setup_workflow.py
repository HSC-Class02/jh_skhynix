#!/usr/bin/env python3
"""Generate GitHub Actions workflows (the ZIP itself contains no hidden files)."""
from pathlib import Path

root = Path(__file__).resolve().parent
workflow_dir = root / ".github" / "workflows"
workflow_dir.mkdir(parents=True, exist_ok=True)

update = """name: Update DART Financial Data

on:
  schedule:
    - cron: '17 0 1 * *'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: dart-data-update
  cancel-in-progress: false

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip
          cache-dependency-path: requirements.txt
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Collect OpenDART financial data
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
        run: python src/collect_dart.py --start-year 2010
      - name: Commit updated CSV
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/financials.csv
          if git diff --cached --quiet; then
            echo "No financial-data changes."
          else
            git commit -m "chore: update DART financial data"
            git push
          fi
"""
pages = """name: Deploy GitHub Pages

on:
  push:
    branches: [main, master]
  workflow_dispatch:
  workflow_run:
    workflows: ["Update DART Financial Data"]
    types: [completed]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Configure Pages
        uses: actions/configure-pages@v5
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""
(workflow_dir / "update.yml").write_text(update, encoding="utf-8")
(workflow_dir / "pages.yml").write_text(pages, encoding="utf-8")
print("Created .github/workflows/update.yml and pages.yml")
print("Next: commit and push these files; add repository secret DART_API_KEY; set Settings > Pages > Source to GitHub Actions.")
