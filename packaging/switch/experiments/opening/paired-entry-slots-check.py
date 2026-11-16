from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'compact-bridges-check.py').read_text().replace('opening-full-guest','opening-full-page').replace('compact-bridges.py','paired-entry-slots.py').replace('ngb_fast_page_bytes','opening_end4')
exec(compile(s,'paired-entry-check','exec'))
