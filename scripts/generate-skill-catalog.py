#!/usr/bin/env python3
"""
generate-skill-catalog.py — スキルカタログ生成（Skill Slimmer 用）

全スキル（有効・無効化問わず）の一覧・説明・状態・使用回数を
Obsidian のスキルカタログ.md に書き出す。

使い方:
  python3 generate-skill-catalog.py                # 生成（既定: /opt/data/obsidian/Agent/Memo/スキルカタログ.md）
  python3 generate-skill-catalog.py --output X     # 出力先変更
  python3 generate-skill-catalog.py --dry-run      # 標準出力のみ

状態の見方:
  ✅ 有効   = システムプロンプトに表示される
  🔒 Discord無効 = platform_disabled.discord に登録（Discordでは非表示）
  🌐 グローバル無効 = skills.disabled に登録（全プラットフォームで非表示）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

DEFAULT_OUTPUT = Path("/opt/data/skills/software-development/skill-management/references/skill-catalog.md")
SKILLS_ROOT = Path("/opt/data/skills")
CONFIG = Path("/opt/data/config.yaml")
USAGE = Path("/opt/data/skills/.usage.json")

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_usage() -> dict:
    if not USAGE.exists():
        return {}
    with open(USAGE, encoding="utf-8") as f:
        return json.load(f)


def discover_skills() -> list[dict]:
    """ディスク上の全スキル（category/name/SKILL.mdパス）を収集。"""
    skills = []
    for p in SKILLS_ROOT.rglob("SKILL.md"):
        rel = p.relative_to(SKILLS_ROOT)
        parts = rel.parts
        if len(parts) == 3:
            skills.append({"category": parts[0], "name": parts[1], "path": p})
        elif len(parts) == 2:
            skills.append({"category": None, "name": parts[0], "path": p})
    return skills


def parse_frontmatter(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    m = FRONTMATTER_RE.match(txt)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def build_catalog() -> list[dict]:
    cfg = load_config()
    usage = load_usage()

    rows = []
    for sk in discover_skills():
        fm = parse_frontmatter(sk["path"])
        name = fm.get("name") or sk["name"]
        desc = fm.get("description", "")
        if isinstance(desc, str):
            desc = desc.replace("\n", " ").strip()
        cat = sk["category"] or fm.get("metadata", {}).get("hermes", {}).get("category")
        if isinstance(cat, dict) or isinstance(cat, list):
            cat = None

        rows.append({
            "name": name,
            "desc": desc[:100],
            "category": cat or "-",
        })

    rows.sort(key=lambda r: (r["category"], r["name"]))
    return rows


def render(rows: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# スキルカタログ",
        "",
        f"> 自動生成: {now}（generate-skill-catalog.py）",
        f"> 総数: **{len(rows)}** スキル",
        "> 状態（有効/無効化）は `skills_list` / `config.yaml`、使用回数は `.usage.json` を参照（Hermes 基本機能で取得可）。",
        "> 無効化スキルを呼び出すには `skill_view(name='...')` を使う（Skill Slimmer パッチ適用時）。",
        "",
        "## 一覧",
        "",
        "| カテゴリ | スキル名 | 説明 |",
        "|---|---|---|",
    ]
    for r in rows:
        desc = r["desc"].replace("|", "\\|").replace("`", "")
        lines.append(f"| {r['category']} | `{r['name']}` | {desc} |")

    lines += ["", "---", "", "再生成: `python3 /opt/data/repos/hermes-skill-slimmer/scripts/generate-skill-catalog.py`"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="スキルカタログ生成")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = build_catalog()
    md = render(rows)

    if args.dry_run:
        print(md)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    # Obsidian 共有環境用に権限を緩める（file-operations 規約）
    try:
        args.output.chmod(0o777)
    except PermissionError:
        pass
    print(f"✅ カタログ生成: {args.output}（{len(rows)}スキル）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
