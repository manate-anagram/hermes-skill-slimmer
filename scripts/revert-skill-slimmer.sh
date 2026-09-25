#!/usr/bin/env bash
# revert-skill-slimmer.sh — Remove the Skill Slimmer core patch (patch-free cutover).
#
# Why: hydrate (reading a hidden skill on demand via `skill_view`) is now provided by the
# `skill-slimmer-autoindex` plugin's `transform_tool_result` hook —
# /opt/data/plugins/skill-slimmer-autoindex/hydrate.py. The core file patch is only needed
# to verify the plugin path (while the patch is applied, the hook never fires because the
# stock refusal never happens).
#
# Usage (root, inside the container):
#   bash scripts/revert-skill-slimmer.sh            # dry-run (prints what it would do)
#   bash scripts/revert-skill-slimmer.sh --apply    # reverse the patch (backup written)
#   TARGET=/path/to/skills_tool.py bash scripts/revert-skill-slimmer.sh --apply
set -euo pipefail

TARGET="${TARGET:-/opt/hermes/tools/skills_tool.py}"
PYTHON="${HERMES_PYTHON:-/opt/hermes/.venv/bin/python3}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

if [[ ! -f "$TARGET" ]]; then
  echo "ERROR: target not found: $TARGET" >&2
  exit 1
fi

"$PYTHON" - "$TARGET" "$APPLY" <<'PY'
import shutil
import sys
from datetime import datetime
from pathlib import Path

target = Path(sys.argv[1])
apply_ = sys.argv[2] == "1"
text = target.read_text(encoding="utf-8")

NEW = '''        if _is_skill_disabled(resolved_name):
            # Skill Slimmer hydrate: hidden from the system-prompt index but
            # still viewable on demand.
            logging.getLogger(__name__).warning(
                "Skill Slimmer hydrate: viewing disabled skill '%s' on demand", resolved_name
            )'''

OLD = '''        if _is_skill_disabled(resolved_name):
            return _fail(f"Skill '{resolved_name}' is disabled. Enable it with `hermes skills` or inspect the files directly on disk.")'''

if NEW not in text:
    if OLD in text:
        print(f"SKILL-SLIMMER-REVERT: already stock (no-op) -> {target}")
        sys.exit(0)
    raise SystemExit(
        "SKILL-SLIMMER-REVERT: neither patched nor stock block found — upstream changed this "
        "code; inspect manually before touching it."
    )

if not apply_:
    print(f"SKILL-SLIMMER-REVERT: dry-run — would restore the stock disabled-gate in {target}")
    print("  (re-run with --apply to write)")
    sys.exit(0)

backup = target.with_name(f"{target.name}.bak-slimmer-revert-{datetime.now():%Y%m%d%H%M%S}")
shutil.copy2(target, backup)
target.write_text(text.replace(NEW, OLD, 1), encoding="utf-8")

import py_compile
py_compile.compile(str(target), doraise=True)
print(f"SKILL-SLIMMER-REVERT: reverted -> {target} (backup: {backup})")
PY

echo "OK — restart the gateway to load stock behaviour."
