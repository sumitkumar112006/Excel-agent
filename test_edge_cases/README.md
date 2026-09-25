# PDF extraction edge-case suite

This folder is intentionally isolated from the application source, existing PDFs, and
the normal `output` folder.

It contains:

- `pdfs/`: 200 separate PDF fixtures (`case_001.pdf` through `case_200.pdf`).
- `case_manifest.json`: the case names, descriptions, categories, and expected behavior.
- `test_edge_cases.py`: a standard-library test runner for the real backend extractor.
- `generate_edge_case_pdfs.py`: reproducible fixture generator.

## Run the suite

From the project root:

```powershell
.\backend\venv\Scripts\python.exe -m unittest discover -s test_edge_cases -p "test_*.py" -v
```

The tests are intentionally strict. A failing case means the extractor behavior does
not match the expectation recorded in `case_manifest.json`; this is useful for finding
regressions and documenting current weaknesses.

To regenerate only this folder's fixtures:

```powershell
.\backend\venv\Scripts\python.exe test_edge_cases\generate_edge_case_pdfs.py
```

Some fixtures are intentionally malformed or incomplete. Those cases should not crash
the extractor; they should return a record marked `REVIEW` with the relevant field set
to `NA` or an open error recorded.
