# 67 — Isolate Website Files to `docs/site/` for Standalone GitHub Pages Deployment

**Date:** 2026-08-24  
**Author:** Antigravity  

---

## 1. Summary

Isolated all static website files (`index.html`, `style.css`, `app.js`, `plasma_column_consolidated_report.pdf`, `.nojekyll`, and deployment `README.md`) into a clean standalone folder [`docs/site/`](file:///home/cspark/Work/projects/plasma-column/docs/site) to enable 1-to-1 synchronization with the dedicated [`plasma-column.github.io`](https://github.com/cspark7701/plasma-column.github.io) repository.

---

## 2. Changes Made

1. **Created `docs/site/` Directory**:
   - Moved `docs/index.html` $\rightarrow$ `docs/site/index.html`
   - Moved `docs/style.css` $\rightarrow$ `docs/site/style.css`
   - Moved `docs/app.js` $\rightarrow$ `docs/site/app.js`
   - Moved `docs/plasma_column_consolidated_report.pdf` $\rightarrow$ `docs/site/plasma_column_consolidated_report.pdf`
   - Created `docs/site/.nojekyll` to disable Jekyll processing in GitHub Pages.
   - Created `docs/site/README.md` with synchronization and deployment instructions.

2. **Updated Documentation & Guidelines**:
   - Updated template path rule in [`AGENTS.md`](file:///home/cspark/Work/projects/plasma-column/AGENTS.md) to reference `docs/site/index.html` and `docs/site/style.css`.

---

## 3. Verification

- Ran `python scripts/audit_repo.py --root .` to ensure repository integrity.
- Verified test suite with `pytest -q` (101 passed).
