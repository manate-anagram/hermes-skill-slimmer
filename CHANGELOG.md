# Changelog

このリポジトリの変更履歴。バージョンは [Semantic Versioning](https://semver.org/lang/ja/) に従う。

## [Unreleased]

### Added
- `scripts/generate-skill-catalog.py` — スキルカタログ（skill-catalog.md）自動生成スクリプトを追加
- `CHANGELOG.md` 新設

## [0.1.0] - 2026-08-10

### Added
- Skill Slimmer パッチ（`install-skill-slimmer.sh`）: `skill_view` の disabled 拒否を「警告ログ+継続」に緩和
  - 対象: `/opt/hermes/tools/skills_tool.py` L1278-1290
  - 効果: `skills.disabled` / `skills.platform_disabled` で一覧から消えたスキルも、名前指定で `skill_view` 可能（hydrate）
- `README.md` — 目的・パッチ内容・使い方（適用方法・スキルを隠す方法）を記載
