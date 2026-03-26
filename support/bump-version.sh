#!/usr/bin/env bash
# Versionsnummer zentral aktualisieren.
# Nutzung: ./support/bump-version.sh 0.2.0

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${1:-}" ]; then
  # Aktuelle Version anzeigen
  current=$(python3 -c "import re; print(re.search(r'__version__\s*=\s*\"(.+?)\"', open('devradar/__init__.py').read()).group(1))")
  echo "Aktuelle Version: $current"
  echo "Nutzung: $0 <neue-version>"
  exit 0
fi

NEW="$1"
echo "Setze Version auf: $NEW"

# 1. Python-Paket (Quelle der Wahrheit)
sed -i '' "s/__version__ = \".*\"/__version__ = \"$NEW\"/" devradar/__init__.py

# 2. pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml

# 3. Frontend package.json
sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW\"/" frontend/package.json

# 4. README.md
sed -i '' "s/^# DevRadar v.*/# DevRadar v$NEW/" README.md

echo "Version aktualisiert:"
grep -n "__version__" devradar/__init__.py
grep -n "^version" pyproject.toml
grep -n '"version"' frontend/package.json
head -1 README.md
