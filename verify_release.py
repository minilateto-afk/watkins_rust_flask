"""Verify source identity before the Docker tests; fail on stale project content."""
from pathlib import Path
root=Path(__file__).resolve().parent
release=(root/'RELEASE_ID.txt').read_text(encoding='utf-8').strip()
expected='watkins-rust-verified-20261121-b'
if release!=expected:
    raise SystemExit(f'Unexpected release marker: {release!r}; expected {expected!r}')
test=(root/'tests'/'test_flask_routes.py').read_text(encoding='utf-8')
if "['指定材料的病害進展比較'" in test or "['指定材料的病害進展曲線'" in test:
    raise SystemExit('Old fragile title-based Flask route test still present')
if "'1190048','1190527'" not in test:
    raise SystemExit('Expected robust screening route test not found')
if not (root/'data'/'raw'/'Watkins.xlsx').is_file():
    raise SystemExit('Required original source workbook is missing')
print(f'OK: verified project: {release}')
