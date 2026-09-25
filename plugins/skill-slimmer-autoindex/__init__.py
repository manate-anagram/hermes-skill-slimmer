from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

__all__ = ["register"]
__version__ = "0.1.0"

LOG = logging.getLogger(__name__)

# カタログ生成スクリプト（hermes-skill-slimmer リポジトリ内）。
# 配布物なのでパスは環境変数で差し替え可能にする（既定はこのホストの配置）。
CATALOG_SCRIPT = Path(
    os.environ.get(
        "SKILL_SLIMMER_CATALOG_SCRIPT",
        "/opt/data/repos/hermes-skill-slimmer/scripts/generate-skill-catalog.py",
    )
)

# pre_llm_call が案内するカタログの位置（スキル相対 or 絶対パス）。
CATALOG_HINT_PATH = os.environ.get(
    "SKILL_SLIMMER_CATALOG_PATH", "dev-workflow/references/skill-catalog.md"
)

# 他ツール（install-skill-slimmer.sh 等）と同じく Hermes の venv Python を使う。
# HERMES_PYTHON が未設定の場合はプロセス自身（Hermes ランタイム）の python に fallback。
PYTHON = os.environ.get("HERMES_PYTHON") or sys.executable

# on_skill_lifecycle の action のうち、カタログ再生成をトリガーするもの。
# - created / installed / restored: スキルが追加・再有効化された
# - removed / archived / deleted: 一覧から消えるので反映が必要
# - disabled / enabled: platform_disabled 等の状態変化（カタログ注記は参照先だが、
#   追加/削除と同タイミングで走ることが多いので含める）
REGEN_ACTIONS = {
    "created",
    "installed",
    "restored",
    "removed",
    "archived",
    "deleted",
    "disabled",
    "enabled",
}

# 同一プロセス内で連続発火（enable→disable 等）をまとめるための簡易デバウンス。
_LAST_RUN_KEY = ""


def _regenerate_catalog(skill_name: str, action: str) -> None:
    global _LAST_RUN_KEY
    if not CATALOG_SCRIPT.exists():
        LOG.warning(
            "skill-catalog-auto: catalog script missing at %s; skip regen",
            CATALOG_SCRIPT,
        )
        return
    # 同一 skill+action の重複発火を1世代だけ抑制（連続イベントの抑止）
    key = f"{skill_name}:{action}"
    if key == _LAST_RUN_KEY:
        return
    _LAST_RUN_KEY = key
    try:
        proc = subprocess.run(
            [PYTHON, str(CATALOG_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            LOG.info(
                "skill-catalog-auto: regenerated catalog after '%s' on '%s'",
                action,
                skill_name,
            )
        else:
            LOG.warning(
                "skill-catalog-auto: catalog regen failed (rc=%s): %s",
                proc.returncode,
                proc.stderr.strip() or proc.stdout.strip(),
            )
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill-catalog-auto: catalog regen error: %s", exc)


def on_skill_lifecycle_callback(
    action: str = "",
    skill_name: str = "",
    provenance: str = "",
    task_id: str = "",
    session_id: str = "",
    use_count: int = 0,
    **kwargs: object,
) -> None:
    """Hook fired by Hermes on skill lifecycle changes (via skill_manage)."""
    if action in REGEN_ACTIONS:
        _regenerate_catalog(skill_name or "", action)


# Skill Slimmer hydrate — Tool Slimmer FALLBACK_INSTRUCTION 相当。
# 一覧から隠れても skill_view / カタログで発見できることを毎ターン思い出させる（案3: カタログ自動注入・軽量）。
_SKILL_SLIMMER_FALLBACK = (
    "Skill Slimmer may hide skills from the initial skill list. "
    f"Full catalog (including hidden skills) is at {CATALOG_HINT_PATH} — "
    "read it with read_file/skill_view to discover hidden skills. "
    "You can also hydrate directly via skill_view(name='...'); hidden skills remain viewable. "
    "Resolve hydrate internally without mentioning Slimmer to the user."
)


def pre_llm_call_callback(**kwargs: object) -> dict[str, str] | None:
    """Inject Skill Slimmer hydrate hint into the system prompt (like Tool Slimmer)."""
    return {"context": _SKILL_SLIMMER_FALLBACK}


def register(ctx) -> None:
    """Register the skill-catalog-auto + Skill Slimmer hydrate plugin with Hermes."""
    register_hook = getattr(ctx, "register_hook", None)
    if not callable(register_hook):
        LOG.warning("skill-catalog-auto: ctx.register_hook unavailable; plugin inert")
        return
    try:
        register_hook("on_skill_lifecycle", on_skill_lifecycle_callback)
        LOG.info("skill-catalog-auto: registered on_skill_lifecycle hook")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill-catalog-auto: hook registration failed: %s", exc)
    try:
        register_hook("pre_llm_call", pre_llm_call_callback)
        LOG.info("skill-catalog-auto: registered pre_llm_call (Skill Slimmer hydrate) hook")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill-catalog-auto: pre_llm_call hook registration failed: %s", exc)
    try:
        # 本体パッチ不要の hydrate 経路（詳細は hydrate.py の docstring）。
        # 通常フックなので allow_tool_override / capability consent は不要。
        from .hydrate import transform_tool_result_callback

        register_hook("transform_tool_result", transform_tool_result_callback)
        LOG.info("skill-catalog-auto: registered transform_tool_result (hydrate) hook")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill-catalog-auto: transform_tool_result hook registration failed: %s", exc)
