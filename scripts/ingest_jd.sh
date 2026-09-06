#!/usr/bin/env bash
# Normalise a job description file into plain text on stdout.
#
# Handles .txt, .md, .pdf and .docx. URLs are deliberately NOT fetched here:
# the calling skill uses WebFetch so the request goes through the harness's
# permission layer rather than a shell escaping it.
#
# Usage: ingest_jd.sh <file> [--min CHARS]
# Exits non-zero when the file is missing, unreadable, an unsupported type,
# or yields less text than --min (default 200).

set -euo pipefail

MIN_CHARS=200
FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --min) MIN_CHARS="${2:?--min needs a value}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "error: unknown option $1" >&2; exit 2 ;;
    *)  FILE="$1"; shift ;;
  esac
done

if [[ -z "$FILE" ]]; then
  echo "error: no file given" >&2
  exit 2
fi
if [[ ! -f "$FILE" ]]; then
  echo "error: not a file: $FILE" >&2
  exit 2
fi

# macOS ships bash 3.2, which has no ${var,,} lowercase expansion.
LOWER="$(printf '%s' "$FILE" | tr '[:upper:]' '[:lower:]')"

extract() {
  case "$LOWER" in
    *.txt|*.md|*.markdown|*.text)
      cat -- "$FILE"
      ;;
    *.pdf)
      command -v pdftotext >/dev/null 2>&1 || {
        echo "error: pdftotext not installed (brew install poppler)" >&2
        exit 3
      }
      pdftotext -layout -- "$FILE" -
      ;;
    *.docx)
      command -v unzip >/dev/null 2>&1 || {
        echo "error: unzip not available" >&2; exit 3
      }
      unzip -p -- "$FILE" word/document.xml | python3 -c '
import html, re, sys
xml = sys.stdin.read()
xml = re.sub(r"</w:p>", "\n", xml)
xml = re.sub(r"<w:tab/>", "\t", xml)
text = html.unescape(re.sub(r"<[^>]+>", "", xml))
print("\n".join(line.strip() for line in text.split("\n") if line.strip()))
'
      ;;
    *)
      echo "error: unsupported file type: $FILE" >&2
      echo "       supported: .txt .md .pdf .docx" >&2
      exit 3
      ;;
  esac
}

TEXT="$(extract)"
CHARS=${#TEXT}

if (( CHARS < MIN_CHARS )); then
  echo "error: extracted only ${CHARS} characters (need ${MIN_CHARS})." >&2
  echo "       The file may be a scanned image, empty, or paywalled." >&2
  echo "       Ask the user to paste the job description instead." >&2
  exit 4
fi

printf '%s\n' "$TEXT"
