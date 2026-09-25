#!/usr/bin/env bash
# install.sh — One-shot installer for hermes-skill-slimmer.
#
# Two parts, both idempotent:
#   [1/3] hydrate plugin  : copies plugins/skill-slimmer-autoindex into $HERMES_HOME/plugins
#                           and enables it. Nothing under /opt/hermes is touched.
#   [2/3] usage recipe    : skills/skill-slimmer/SKILL.md -> reference/standalone skill
#   [3/3] skill catalog   : generates skill-catalog.md (list of hidden + visible skills)
#
# The legacy core patch (writes /opt/hermes/tools/skills_tool.py as root) is OPT-IN:
#   bash install.sh --legacy-patch
# Do NOT apply it while the plugin is active: the core gate would no longer refuse,
# so the hydrate hook could never fire (and live verification becomes impossible).
#
# Usage:
#   bash install.sh                          # plugin + recipe + catalog (recommended)
#   bash install.sh --legacy-patch           # also apply the legacy core patch (root needed)
#   HERMES_HOME=/x SKILLS_DIR=/x/skills bash install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME_DIR="${HERMES_HOME:-/opt/data}"
SKILLS_DIR="${SKILLS_DIR:-$HERMES_HOME_DIR/skills}"
PLUGINS_DIR="${PLUGINS_DIR:-$HERMES_HOME_DIR/plugins}"
HERMES_TOOLS="${HERMES_TOOLS:-/opt/hermes/tools/skills_tool.py}"
PLUGIN_NAME="skill-slimmer-autoindex"
LEGACY=0
[[ "${1:-}" == "--legacy-patch" ]] && LEGACY=1

echo "==> [1/3] hydrate plugin (patch-free)"
mkdir -p "$PLUGINS_DIR"
cp -a "$REPO_DIR/plugins/$PLUGIN_NAME" "$PLUGINS_DIR/"
echo "    installed -> $PLUGINS_DIR/$PLUGIN_NAME"
if command -v hermes >/dev/null 2>&1; then
  # --no-allow-tool-override: the plugin only registers hooks, so keep the privileged
  # built-in-tool override OFF (and skip the interactive consent prompt).
  hermes plugins enable "$PLUGIN_NAME" --no-allow-tool-override \
    || echo "    WARN: 'hermes plugins enable' failed — enable it from the dashboard"
else
  echo "    NOTE: hermes CLI not on PATH — add $PLUGIN_NAME to plugins.enabled in config.yaml"
fi
echo "    → restart the gateway to load the hooks (hooks are read at process start)"

echo "==> [2/3] Recipe: skills/skill-slimmer/SKILL.md"
RECIPE_SRC="$REPO_DIR/skills/skill-slimmer/SKILL.md"
if [[ -d "$SKILLS_DIR/software-development/dev-workflow" ]]; then
  # dev-workflow (older name: skill-management) → keep it as a reference, not a visible skill
  RECIPE_DEST="$SKILLS_DIR/software-development/dev-workflow/references/skill-slimmer.md"
elif [[ -d "$SKILLS_DIR/software-development/skill-management" ]]; then
  RECIPE_DEST="$SKILLS_DIR/software-development/skill-management/references/skill-slimmer.md"
else
  RECIPE_DEST="$SKILLS_DIR/skill-slimmer/SKILL.md"
fi
mkdir -p "$(dirname "$RECIPE_DEST")"
cp "$RECIPE_SRC" "$RECIPE_DEST"
echo "    installed -> $RECIPE_DEST"

echo "==> [3/3] Skill catalog"
CATALOG_SCRIPT="${SKILL_SLIMMER_CATALOG_SCRIPT:-$REPO_DIR/scripts/generate-skill-catalog.py}"
python3 "$CATALOG_SCRIPT" || {
  echo "    WARN: catalog generation failed — check paths (SKILLS_DIR / config.yaml)."
}

if [[ "$LEGACY" == "1" ]]; then
  echo "==> [legacy] core patch (root required)"
  TARGET="$HERMES_TOOLS" bash "$REPO_DIR/scripts/install-skill-slimmer.sh"
  echo "    NOTE: while this patch is applied the hydrate hook never fires."
else
  echo "==> [legacy] skipped (default). Use --legacy-patch only as an emergency fallback."
fi

echo ""
echo "OK — restart the Hermes gateway (or 'docker restart hermes') to load the hooks."
echo "Verify: skill_view a hidden skill (e.g. 'airtable') — content should come back."
