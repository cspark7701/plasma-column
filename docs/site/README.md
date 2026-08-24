# `plasma-column.github.io` — Project Documentation Site

This directory contains the standalone static website files for the **Plasma Column Neutralizer** project.

## Files
- `index.html` — Interactive ReadTheDocs-themed single-page documentation and simulator.
- `style.css` — Sphinx / ReadTheDocs styling rules.
- `app.js` — Client-side interactive model simulator and SVG chart engine.
- `plasma_column_consolidated_report.pdf` — Downloadable consolidated physics and simulation report.
- `.nojekyll` — Bypasses Jekyll processing on GitHub Pages.

## Deploying to `plasma-column.github.io`
To deploy or synchronize these files to the standalone repository `https://github.com/cspark7701/plasma-column.github.io`:

```bash
# 1. Clone the GitHub Pages repository (e.g. into ../plasma-column.github.io)
git clone https://github.com/cspark7701/plasma-column.github.io.git /path/to/plasma-column.github.io

# 2. Sync site files from docs/site/
rsync -av --delete /home/cspark/Work/projects/plasma_column/docs/site/ /path/to/plasma-column.github.io/

# 3. Commit and push from the plasma-column.github.io repository
cd /path/to/plasma-column.github.io
git add .
git commit -m "Deploy latest plasma_column documentation site"
git push origin main
```
