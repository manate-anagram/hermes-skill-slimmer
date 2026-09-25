#!/usr/bin/env bash
# install-skill-slimmer.sh — Apply/repair the Skill Slimmer patch to Hermes core.
#
# What it does: relaxes the `skill_view` disabled-gate in /opt/hermes/tools/skills_tool.py
# so skills hidden from the system-prompt index (skills.disabled / platform_disabled)
# remain viewable on demand — the Skill Slimmer equivalent of Tool Slimmer hydrate.
#
# Idempotent: safe to re-run after every container/image update.
# Usage:
#   bash scripts/install-skill-slimmer.sh
#   TARGET=/opt/hermes/tools/skills_tool.py bash scripts/install-skill-slimmer.sh
set -euo pipefail

TARGET="${TARGET:-/opt/hermes/tools/skills_tool.py}"
PYTHON="${HERMES_PYTHON:-/opt/hermes/.venv/bin/python3}"

if [[ ! -f "$TARGET" ]]; then
  echo "ERROR: target not found: $TARGET" >&2
  exit 1
fi

"$PYTHON" - "$TARGET" <<'PY'
import logging
import sys
from pathlib import Path

import py_compile

target = Path(sys.argv[1])
text = target.read_text(encoding="utf-8")

# v2026.9.7 (v0.21.1) 対応: json.dumps 直書き → _fail() ヘルパー、
# parsed_frontmatter → frontmatter にリネームされたため OLD ブロックを更新 (2026-09-08)
OLD = '''        resolved_name = frontmatter.get("name", skill_md.parent.name)
        if _is_skill_disabled(resolved_name):
            return _fail(f"Skill '{resolved_name}' is disabled. Enable it with `hermes skills` or inspect the files directly on disk.")'''

NEW = '''        resolved_name = frontmatter.get("name", skill_md.parent.name)
        if _is_skill_disabled(resolved_name):
            # Skill Slimmer hydrate: hidden from the system-prompt index but
            # still viewable on demand.
            logging.getLogger(__name__).warning(
                "Skill Slimmer hydrate: viewing disabled skill '%s' on demand", resolved_name
            )'''

if NEW in text:
    print(f"SKILL-SLIMMER: already patched (no-op) -> {target}")
    sys.exit(0)

if OLD not in text:
    raise SystemExit(
        "SKILL-SLIMMER: target block not found — upstream Hermes changed this code; "
        "manual review needed (see Obsidian Agent/Procedures skill-slimmer note)."
    )

text = text.replace(OLD, NEW, 1)
target.write_text(text, encoding="utf-8")
py_compile.compile(target, doraise=True)
print(f"SKILL-SLIMMER: patched -> {target}")
PY

echo "OK — restart Hermes gateway to load the change (or it loads on next session)."
