import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from extractor import process_single_pdf

test_dir = 'test-pdfs'
for fname in sorted(os.listdir(test_dir)):
    if not fname.endswith('.pdf'):
        continue
    fpath = os.path.join(test_dir, fname)
    try:
        results = process_single_pdf(fpath)
        print(f'\n=== {fname} ({len(results)} items) ===')
        for i, r in enumerate(results):
            print(f'  Item {i+1}:')
            for k, v in r.items():
                if k not in ['validation_checks', 'file_name']:
                    print(f'    {k}: {repr(v)}')
    except Exception as e:
        print(f'ERROR {fname}: {e}')
        import traceback; traceback.print_exc()
