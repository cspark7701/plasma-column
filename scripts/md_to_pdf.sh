#!/usr/bin/env bash
# ==============================================================================
# scripts/md_to_pdf.sh — Convert a Markdown document to PDF (pandoc + xelatex)
#
# Inline code is set with xurl (\nolinkurl, spaces kept) so long case names and
# paths can break; long code-block lines wrap (fvextra); table column widths
# follow the relative lengths of the dashes in each table's separator row.
# The build fails if LaTeX reports any overfull box.
#
# Usage:
#   bash scripts/md_to_pdf.sh docs/production_matrix.md            # -> docs/production_matrix.pdf
#   bash scripts/md_to_pdf.sh docs/production_matrix.md -o out.pdf
#   bash scripts/md_to_pdf.sh docs/production_matrix.md --dry_run  # check tools and input only
#
# PDFs are git-ignored (.gitignore: *.pdf); regenerate them with this script.
# ==============================================================================
set -euo pipefail

INPUT=""
OUTPUT=""
DRY_RUN=false

while [ $# -gt 0 ]; do
    case "$1" in
        -o|--output) OUTPUT="$2"; shift 2 ;;
        --dry_run|--dry-run) DRY_RUN=true; shift ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; exit 2 ;;
        *) INPUT="$1"; shift ;;
    esac
done

[ -n "$INPUT" ] || { echo "Usage: $0 <file.md> [-o out.pdf] [--dry_run]" >&2; exit 2; }
[ -f "$INPUT" ] || { echo "Input not found: $INPUT" >&2; exit 1; }
OUTPUT="${OUTPUT:-${INPUT%.md}.pdf}"

for tool in pandoc xelatex; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
kpsewhich xurl.sty >/dev/null || { echo "Missing LaTeX package: xurl" >&2; exit 1; }

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN SUCCESS] $INPUT -> $OUTPUT (pandoc $(pandoc --version | head -1 | cut -d' ' -f2), xelatex found)"
    exit 0
fi

WORK=$(mktemp -d)
trap 'rm -rf -- "${WORK:?}"' EXIT

cat > "$WORK/breakable_code.lua" <<'LUA'
-- Inline code -> \nolinkurl{...} (xurl allows a line break after any character).
function Code(el)
  if FORMAT:match("latex") then
    return pandoc.RawInline("latex", "\\nolinkurl{" .. el.text .. "}")
  end
end
LUA

cat > "$WORK/header.tex" <<'TEX'
\usepackage{etoolbox}
\PassOptionsToPackage{obeyspaces,spaces}{url}
\usepackage{xurl}
\AtBeginDocument{\urlstyle{tt}}  % pandoc sets \urlstyle{same} after header-includes
% Wrap long lines in code blocks (verbatim overflow is not reported as an overfull box)
\usepackage{fvextra}
\fvset{breaklines=true,breakanywhere=true}
\makeatletter
\@ifundefined{Highlighting}{}{\RecustomVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},breaklines,breakanywhere}}
\makeatother
\renewcommand{\arraystretch}{1.15}
\AtBeginEnvironment{longtable}{\small}
\usepackage[nobottomtitles*]{titlesec}  % no section heading alone at a page bottom
TEX

TEX_FILE="$WORK/doc.tex"
pandoc "$INPUT" -s -o "$TEX_FILE" \
    --lua-filter "$WORK/breakable_code.lua" \
    --include-in-header "$WORK/header.tex" \
    --resource-path "$(dirname "$INPUT")" \
    -V geometry:margin=2cm \
    -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" \
    -V fontsize=10pt -V colorlinks=true

(cd "$WORK" && for _ in 1 2; do xelatex -interaction=nonstopmode -halt-on-error doc.tex >/dev/null; done)

if grep -q "Overfull" "$WORK/doc.log"; then
    echo "Overfull boxes reported by LaTeX:" >&2
    grep -A1 "Overfull" "$WORK/doc.log" >&2
    exit 1
fi

cp "$WORK/doc.pdf" "$OUTPUT"
echo "Wrote $OUTPUT ($(pdfinfo "$OUTPUT" 2>/dev/null | awk '/^Pages/{print $2}') pages, no overfull boxes)"
