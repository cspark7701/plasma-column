# Execution Plan Summary: Production Matrix PDF Without Overflow

**Task Index**: 101  
**Date**: 2026-10-22  
**Subject**: Build a PDF of `docs/production_matrix.md` in which no content runs past the margins.

---

## 1. Problems in the Default Pandoc Output

A plain `pandoc … --pdf-engine=xelatex` build gave 19 overfull boxes. Visual inspection showed
two more problems that the LaTeX log does not report:

| Problem | Cause |
|---|---|
| Table cells too wide | All columns got equal width (every separator `---` has the same length) |
| Case names and paths stick out of cells and the text block | `\texttt` inline code cannot line-break |
| Code-block lines run past the right margin (no log warning) | Verbatim text does not wrap |
| Spaces lost in inline code (`--mcc electron_impact` → `--mccelectron_impact`) | `url` package drops spaces by default |
| Inline code set in the serif body font | pandoc's template sets `\urlstyle{same}` after header-includes |

## 2. Changes

- **New** `scripts/md_to_pdf.sh` (`--dry_run`, `-o`): pandoc + xelatex with
  - a Lua filter that sets inline code as `\nolinkurl{}` (xurl: break after any character),
    `url` options `obeyspaces,spaces`, and monospace via `\AtBeginDocument{\urlstyle{tt}}`;
  - `fvextra` `breaklines,breakanywhere` for code blocks (pandoc `Highlighting` environment);
  - `\small` tables, `titlesec` `nobottomtitles*` so headings are not stranded at a page bottom;
  - DejaVu Serif / DejaVu Sans Mono for the non-ASCII characters (×, ∈, ±, —, η);
  - **exit 1 if the LaTeX log contains any overfull box**.
- `docs/production_matrix.md`: separator rows now use dash counts as relative column widths
  (pandoc reads them; GitHub rendering is unchanged).

## 3. Result

`bash scripts/md_to_pdf.sh docs/production_matrix.md` → `docs/production_matrix.pdf`
(2 pages, 0 overfull boxes). Rendered pages were checked at 110 dpi: all table cells and code
lines stay inside the margins, inline code is monospace with spaces kept, and the settings
heading starts page 2 with its table. The PDF is git-ignored (`*.pdf`); regenerate it after
editing the Status column.

## 4. Limitation

The script's overfull check cannot detect verbatim overflow. That case is prevented by the
`fvextra` line wrapping rather than detected, so check the pages visually for new kinds of content.
