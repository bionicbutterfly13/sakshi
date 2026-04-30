#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() {
  echo "hygiene failed: $*" >&2
  exit 1
}

grep_code() {
  rg "$@" sakshi tests
}

if grep_code '^(from|import) api\.' >/tmp/sakshi_hygiene_hits.txt; then
  cat /tmp/sakshi_hygiene_hits.txt >&2
  fail "package/test code imports host api.* modules"
fi

if grep_code 'FastAPI|Graphiti|Neo4j|smolagents|get_[a-zA-Z0-9_]+_service\(' >/tmp/sakshi_hygiene_hits.txt; then
  cat /tmp/sakshi_hygiene_hits.txt >&2
  fail "package/test code references forbidden host runtime dependencies"
fi

if grep_code '(class|def) MIDCA|from .*midca|import .*midca' >/tmp/sakshi_hygiene_hits.txt; then
  cat /tmp/sakshi_hygiene_hits.txt >&2
  fail "public identifiers or imports contain forbidden external reference names"
fi

if rg -n '^# .*MIDCA|^## .*MIDCA|^### .*MIDCA' README.md docs sakshi tests >/tmp/sakshi_hygiene_hits.txt; then
  cat /tmp/sakshi_hygiene_hits.txt >&2
  fail "primary headings contain forbidden external reference names"
fi

if rg -n -i '\b(Mani|Saint-Victor|Hexis|IAS|HBD|DGAF|Bergerac|Vigilant Sentinel|Analytical Empath|MEMORY_MANIFESTO|Ralph|Archon|Conductor|DrMani)\b' \
  sakshi tests README.md INSPIRATION.md CONTRIBUTING.md CHANGELOG.md pyproject.toml docs AGENTS.md >/tmp/sakshi_hygiene_hits.txt; then
  cat /tmp/sakshi_hygiene_hits.txt >&2
  fail "published package surface contains personal attribution or private-project terms"
fi

rm -f /tmp/sakshi_hygiene_hits.txt
echo "hygiene ok"
