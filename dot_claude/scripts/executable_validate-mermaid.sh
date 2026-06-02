#!/usr/bin/env bash
# Validate every ```mermaid block in a Markdown file using the real Mermaid
# renderer (mmdc). Exits non-zero and prints the parse error if any block fails.
#
# Usage: validate-mermaid.sh <markdown-file>
#
# Requires @mermaid-js/mermaid-cli (`mmdc`). Install one of:
#   sudo snap install mermaid-cli         # provides /snap/bin/mmdc
#   npm install -g @mermaid-js/mermaid-cli
#
# NOTE: the snap build of mmdc is confined and CANNOT read /tmp or arbitrary
# paths; it can only read under $HOME, and the snap 'home' interface also blocks
# HIDDEN paths (dotfiles/dotdirs). The working dir is therefore a NON-hidden
# directory directly under $HOME.
set -euo pipefail

doc="${1:?usage: validate-mermaid.sh <markdown-file>}"
if ! command -v mmdc >/dev/null 2>&1; then
  echo "ERROR: mmdc not found. Install with 'sudo snap install mermaid-cli' or 'npm i -g @mermaid-js/mermaid-cli'." >&2
  exit 2
fi

work="$(mktemp -d "${HOME}/mmcheck.XXXXXX")"
trap 'rm -rf "$work"' EXIT

awk '/^```mermaid/{f=1;n++;fn=sprintf("%s/d%02d.mmd", dir, n);next}
     /^```[[:space:]]*$/{if(f)f=0;next}
     f{print > fn}' dir="$work" "$doc"

shopt -s nullglob
blocks=("$work"/d*.mmd)
if [ ${#blocks[@]} -eq 0 ]; then
  echo "No mermaid blocks found in $doc"
  exit 0
fi

rc=0
for f in "${blocks[@]}"; do
  if mmdc -i "$f" -o "$f.svg" >"$f.log" 2>&1; then
    echo "PASS  $(basename "$f")"
  else
    echo "FAIL  $(basename "$f")"
    grep -E "Parse error|Error:" -A3 "$f.log" | sed 's/^/      /' | head -8
    rc=1
  fi
done
exit $rc
