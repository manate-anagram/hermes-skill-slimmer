# Changelog

このリポジトリの変更履歴。バージョンは [Semantic Versioning](https://semver.org/lang/ja/) に従う。

## [0.1.1] - 2026-10-24

### Added
- `plugins/skill-slimmer-autoindex/` — **hydrate の実体を同梱**（`plugin.yaml` / `__init__.py` / `hydrate.py`）。
  `transform_tool_result`（hydrate）＋ `on_skill_lifecycle`（カタログ再生成）＋ `pre_llm_call`（思い出し注入）の3フック。
  `install.sh` が `$HERMES_HOME/plugins/` へ配置して `hermes plugins enable --no-allow-tool-override` する
- `install.sh` — 一発インストーラ（パッチ適用 + レシピ配置 + カタログ生成、環境変数でパス上書き可）
- `skills/skill-slimmer/SKILL.md` — 配布用レシピ（SKILL.md 形式）。install.sh が環境に応じて
  skill-management の references または独立スキルとして配置
- README に「動作確認済み環境」（Hermes Agent v0.19.1 / 2026-07-30）を追記
- `scripts/revert-skill-slimmer.sh` — 本体パッチの逆適用（stock の disabled-gate に戻す）。
  hydrate をプラグイン経路（`transform_tool_result` フック）へ移行する際の cutover 用。
  dry-run 既定 / `--apply` で書込 / バックアップ自動作成 / 構文検証付き。
  対象ブロックが patched でも stock でもない場合は上流変更とみなして停止する。

### Changed
- `skill-slimmer-autoindex` プラグイン（Hermes プラグイン）を追加:
  `on_skill_lifecycle` フックでスキル追加・再有効化時に `generate-skill-catalog.py` を
  自動呼び出し、`skill-catalog.md` を再生成する。本番（v0.20.3）で動作確認済み。
- `README.md` を英語化（構成ツリー・Note コメント）し、誤った `docs/skill-slimmer.md`
  参照を `skills/skill-slimmer/SKILL.md` に修正。Operational Notes / Pitfalls セクションを追加。
- 動作確認済み環境を v0.20.3 / Python 3.13.5 に更新（初回公開時は v0.19.1 / Python 3.11）。
- **hydrate は本体パッチ不要になった**: `skill-slimmer-autoindex` プラグインの
  `hydrate.py`（`transform_tool_result` フック）が `skill_view` の disabled 拒否だけを検知し、
  `tools.skills_tool._is_skill_disabled` を呼び出し中だけ False 固定にして本体実装を再実行、
  実コンテンツへ差し替える。通常フックなので `allow_tool_override` / capability consent は不要で、
  ツールの名前・toolset・schema は変わらない（= `hermes update` 後の再適用が不要）。
  旧パッチは第1ゲートしか緩めていなかったが、本方式は `skills_tool_plugin.py` 側の
  第2ゲート（plugin 名前空間スキル）も同じ関数経由でカバーする。
- `install-skill-slimmer.sh` / `generate-skill-catalog.py` を現行 Hermes（v0.21.x）の
  ブロック形状に追従（未コミットだった差分を取り込み）。旧パッチは緊急時の保険として残す。
- **`install.sh` の既定動作を「プラグイン配置」に変更**。旧コアパッチは `--legacy-patch` の opt-in になった
  （プラグインが有効な間はパッチを当ててもフックが発火しないため、既定で当てない）
- **`README.md` を全面改訂**（プラグイン方式・動作確認環境 v0.21.5 / 2026-09-25・リポジトリ構成・
  環境変数・Pitfalls）。`skills/skill-slimmer/SKILL.md` も同様に更新
- **レシピ配置先の判定を dev-workflow 優先に**（旧 skill-management も後方互換で対応）
- プラグインのパス・文言を環境変数化（`SKILL_SLIMMER_CATALOG_SCRIPT` / `SKILL_SLIMMER_CATALOG_PATH`）。
  `pre_llm_call` の案内文からスキル総数のハードコードを外した（カタログ再生成で古くなるため）

### Fixed
- **カタログ自動再生成が全滅していたのを修正**: Hermes 3.x の venv は PyYAML を同梱せず
  **ruamel.yaml のみ**のため、`generate-skill-catalog.py` の `import yaml` が
  `ModuleNotFoundError` で落ち、`on_skill_lifecycle` 経由の再生成が `rc=1` で失敗し続けていた
  （症状: `errors.log` の `catalog regen failed (rc=1)`／カタログが古い総数のまま固定）。
  PyYAML 不在時は ruamel.yaml へフォールバックする `safe_load` シムを追加（`YAMLError` も同梱）。
  別インタープリタに逃がす回避策は環境依存なので採らない。
- `discover_skills()` が深い階層（`mlops/models/audiocraft/SKILL.md` 等）のスキルを
  無言で取りこぼしていたのを修正。`.venv` / `site-packages` / `node_modules` 配下の
  依存パッケージ内 SKILL.md は除外し、深い階層は category を `"/"` 結合で保持する。

## [0.1.0] - 2026-08-10

### Added
- Skill Slimmer パッチ（`install-skill-slimmer.sh`）: `skill_view` の disabled 拒否を「警告ログ+継続」に緩和
  - 対象: `/opt/hermes/tools/skills_tool.py` L1278-1290
  - 効果: `skills.disabled` / `skills.platform_disabled` で一覧から消えたスキルも、名前指定で `skill_view` 可能（hydrate）
- `README.md` — 目的・パッチ内容・使い方（適用方法・スキルを隠す方法）を記載
