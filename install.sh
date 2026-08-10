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

echo "==> [2/3] Recipe: skills/skill-slimmer/SKILL.md"
RECIPE_SRC="$REPO_DIR/skills/skill-slimmer/SKILL.md"
if [[ -d "$SKILLS_DIR/software-development/skill-management" ]]; then
  # skill-management がある環境 → references に同期（独立スキルにしない・一覧非表示維持）
  RECIPE_DEST="$SKILLS_DIR/software-development/skill-management/references/skill-slimmer.md"
  mkdir -p "$(dirname "$RECIPE_DEST")"
  cp "$RECIPE_SRC" "$RECIPE_DEST"
  echo "    installed -> $RECIPE_DEST (as skill-management reference)"
else
  # skill-management が無い環境 → 独立スキルとして配置
  SKILL_DEST="$SKILLS_DIR/skill-slimmer/SKILL.md"
  mkdir -p "$(dirname "$SKILL_DEST")"
  cp "$RECIPE_SRC" "$SKILL_DEST"
  echo "    installed -> $SKILL_DEST (as standalone skill)"
fi

echo "==> [3/3] Skill catalog"
python3 "$REPO_DIR/scripts/generate-skill-catalog.py" || {
  echo "    WARN: catalog generation failed — check paths (SKILLS_DIR / config.yaml)."
}

echo ""
echo "OK — restart the Hermes gateway to load the change (docker restart hermes)."
