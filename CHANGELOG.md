# Changelog

このリポジトリの変更履歴。バージョンは [Semantic Versioning](https://semver.org/lang/ja/) に従う。

## [Unreleased]

### Added
- `install.sh` — 一発インストーラ（パッチ適用 + レシピ配置 + カタログ生成、環境変数でパス上書き可）
- `skills/skill-slimmer/SKILL.md` — 配布用レシピ（SKILL.md 形式）。install.sh が環境に応じて
  skill-management の references または独立スキルとして配置
- README に「動作確認済み環境」（Hermes Agent v0.19.1 / 2026-07-30）を追記

### Changed
- `skill-slimmer-autoindex` プラグイン（Hermes プラグイン）を追加:
  `on_skill_lifecycle` フックでスキル追加・再有効化時に `generate-skill-catalog.py` を
  自動呼び出し、`skill-catalog.md` を再生成する。本番（v0.20.3）で動作確認済み。
- `README.md` を英語化（構成ツリー・Note コメント）し、誤った `docs/skill-slimmer.md`
  参照を `skills/skill-slimmer/SKILL.md` に修正。Operational Notes / Pitfalls セクションを追加。
- 動作確認済み環境を v0.20.3 / Python 3.13.5 に更新（初回公開時は v0.19.1 / Python 3.11）。

## [0.1.0] - 2026-08-10

### Added
- Skill Slimmer パッチ（`install-skill-slimmer.sh`）: `skill_view` の disabled 拒否を「警告ログ+継続」に緩和
  - 対象: `/opt/hermes/tools/skills_tool.py` L1278-1290
  - 効果: `skills.disabled` / `skills.platform_disabled` で一覧から消えたスキルも、名前指定で `skill_view` 可能（hydrate）
- `README.md` — 目的・パッチ内容・使い方（適用方法・スキルを隠す方法）を記載
