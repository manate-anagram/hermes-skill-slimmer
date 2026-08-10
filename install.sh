#!/usr/bin/env bash
# install.sh — One-shot installer for hermes-skill-slimmer.
#
# Applies the Skill Slimmer patch, installs the usage recipe, and regenerates
# the skill catalog. Safe to re-run (idempotent).
#
# Usage:
#   bash install.sh                          # defaults for this host
#   SKILLS_DIR=/custom/skills bash install.sh
#   HERMES_TOOLS=/custom/skills_tool.py bash install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-/opt/data/skills}"
HERMES_TOOLS="${HERMES_TOOLS:-/opt/hermes/tools/skills_tool.py}"

echo "==> [1/3] Skill Slimmer patch"
TARGET="$HERMES_TOOLS" bash "$REPO_DIR/scripts/install-skill-slimmer.sh"

echo "==> [2/3] Recipe: docs/skill-slimmer.md -> skills/.../skill-management/references/"
RECIPE_DEST="$SKILLS_DIR/software-development/skill-management/references/skill-slimmer.md"
if [[ -d "$SKILLS_DIR/software-development/skill-management" ]]; then
  mkdir -p "$(dirname "$RECIPE_DEST")"
  cp "$REPO_DIR/docs/skill-slimmer.md" "$RECIPE_DEST"
  echo "    installed -> $RECIPE_DEST"
else
  echo "    WARN: skill-management not found under $SKILLS_DIR — recipe skipped."
  echo "    (copy docs/skill-slimmer.md manually if you still want it)"
fi

echo "==> [3/3] Skill catalog"
python3 "$REPO_DIR/scripts/generate-skill-catalog.py" || {
  echo "    WARN: catalog generation failed — check paths (SKILLS_DIR / config.yaml)."
}

echo ""
echo "OK — restart the Hermes gateway to load the change (docker restart hermes)."
