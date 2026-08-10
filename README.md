# hermes-skill-slimmer

Hermes Agent のスキル一覧スリマー（Skill Slimmer）パッチ管理リポジトリ。

## 目的

Tool Slimmer（ツールスキーマ削減）のスキル版。システムプロンプトの `<available_skills>` ブロック
（毎ターン約2,677トークン）から、`skills.disabled` / `skills.platform_disabled` で指定した
スキルを**隠す**。隠したスキルは `skill_view` で名前指定すれば**いつでも読める**（hydrate相当）。

## パッチ内容

- 対象: `/opt/hermes/tools/skills_tool.py` L1278-1290
- 変更: `skill_view` の disabled 拒否（early return）を「警告ログ+継続」に変更
  - 変更前: disabled スキルは一覧から消える＋skill_view も拒否
  - 変更後: disabled スキルは一覧から消えるが、skill_view では読める（hydrate）

## 使い方

### 適用（コンテナ更新後・root で実行）

```bash
# コンテナ内 root で実行
TARGET=/opt/hermes/tools/skills_tool.py bash /opt/data/repos/hermes-skill-slimmer/scripts/install-skill-slimmer.sh
# または
bash /opt/data/repos/hermes-skill-slimmer/scripts/install-skill-slimmer.sh
```

冪等（2回実行しても安全）。適用後は Hermes gateway 再起動（docker restart hermes）。

### スキルを隠す

`/opt/data/config.yaml` の `skills.disabled`（全プラットフォーム）または
`skills.platform_disabled.<platform>`（特定プラットフォーム）にスキル名を追加。

## 関連

- Obsidian: `Agent/Procedures/2026-08-10_Skill_Slimmer_適用フロー.md`
