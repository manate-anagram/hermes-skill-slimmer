"""Skill Slimmer hydrate — 本体パッチ不要版（transform_tool_result フック）。

なぜフックなのか
----------------
Hermes 本体の disabled-gate は「索引から隠したスキルは skill_view でも読めない」仕様で、
`/opt/hermes/tools/skills_tool.py` に直書きされている。これを毎回ファイルパッチで
緩める代わりに、**呼び出し時に in-process で** disabled 判定だけを無効化して
本体の実装をそのまま再実行する。

経路は `transform_tool_result` フック（`model_tools.handle_function_call` の最終段、
戻り値の str がそのままツール結果を置き換える）。通常のフックなので
`allow_tool_override` / capability consent（register_tool の privileged override）は不要で、
ツールの同一性（名前・toolset・schema・check_fn）も一切変わらない。

カバー範囲
----------
disabled 判定は `tools.skills_tool._is_skill_disabled` の1関数で、
`tools/skills_tool_plugin.py::_serve_plugin_skill`（plugin 名前空間スキル用の第2ゲート）も
`_st._is_skill_disabled` として同じ関数を参照する → **1箇所の一時差し替えで両ゲートをカバー**。

Fail-open
---------
判定パターンに一致しない結果・例外・想定外の API 形状では None を返し、
本体の結果をそのまま通す（=素の Hermes 挙動に静かに劣化。壊れない）。
"""

from __future__ import annotations

import json
import logging
import re
from contextlib import contextmanager

LOG = logging.getLogger(__name__)

TOOL = "skill_view"

# 本体の拒否メッセージ形:
#   gate1 skills_tool.py:  "Skill 'x' is disabled. Enable it with `hermes skills` ..."
#   gate2 skills_tool_plugin.py: "Skill 'x' is disabled."
# どちらも「Skill '…' is disabled」を含む。プラグイン無効化の拒否文
# （"Plugin 'x' is disabled."）は hydrate 対象外なので、プレフィックスで区別する。
_DISABLED_RE = re.compile(r"Skill '[^']*' is disabled")


def _is_disabled_refusal(result: object) -> bool:
    """本体が「disabled だから読めない」で返した結果かどうか（厳しめに判定）。"""
    if not isinstance(result, str):
        return False
    text = result.strip()
    if not text.startswith("{"):
        return False
    try:
        payload = json.loads(text)
    except Exception:
        return False
    if not isinstance(payload, dict) or payload.get("success") is True:
        return False
    for key in ("error", "message", "hint"):
        value = payload.get(key)
        if isinstance(value, str) and _DISABLED_RE.search(value):
            return True
    return False


@contextmanager
def _relaxed_disabled_gate():
    """`_is_skill_disabled` を一時的に False 固定にする（呼び出し中だけ）。

    モジュール属性の差し替えなので `skills_tool` 内の呼び出しと
    `skills_tool_plugin` の `_st._is_skill_disabled` の両方に効く。
    緩める方向のレースは「他の同時呼び出しも hydrate できる」だけなので無害。
    """
    from tools import skills_tool as st

    saved = st._is_skill_disabled
    st._is_skill_disabled = lambda *args, **kwargs: False  # noqa: ARG005
    try:
        yield st
    finally:
        st._is_skill_disabled = saved


def _serve(st, args: dict, task_id: str | None, session_id: str | None) -> str | None:
    """本体の skill_view 実装をそのまま呼ぶ（dedup / view_count bump も本体側の経路で維持）。"""
    handler = getattr(st, "_skill_view_with_bump", None)
    if callable(handler):
        out = handler(dict(args), task_id=task_id, session_id=session_id)
    else:  # 上流がリネームした場合のフォールバック（bump は失われるが hydrate は成立する）
        out = st.skill_view(args.get("name", ""), file_path=args.get("file_path"), task_id=task_id)
    return out if isinstance(out, str) else None


def transform_tool_result_callback(
    tool_name: str = "",
    args: dict | None = None,
    result: object = None,
    task_id: str | None = None,
    session_id: str | None = None,
    **kwargs: object,
) -> str | None:
    """skill_view が disabled 拒否を返した時だけ hydrate して差し替える。"""
    if tool_name != TOOL:
        return None
    if not _is_disabled_refusal(result):
        return None
    try:
        with _relaxed_disabled_gate() as st:
            served = _serve(st, args or {}, task_id, session_id)
    except Exception as exc:  # noqa: BLE001 — fail-open: 素の拒否結果をそのまま通す
        LOG.debug("Skill Slimmer hydrate: skipped (%s: %s)", type(exc).__name__, exc)
        return None
    if served is None or _is_disabled_refusal(served):
        return None
    LOG.warning(
        "Skill Slimmer hydrate: served disabled skill %r on demand (plugin path)",
        (args or {}).get("name"),
    )
    return served
