# hermes-skill-slimmer

Hermes Agent のスキル一覧スリマー（Skill Slimmer）パッチ管理リポジトリ。

Tool Slimmer（ツールスキーマ削減）のスキル版。システムプロンプトの `<available_skills>` ブロック
（毎ターン約2,677トークン実測）から、`skills.disabled` / `skills.platform_disabled` で指定した
スキルを**隠す**。隠したスキルは `skill_view` で名前指定すれば**いつでも読める**（hydrate相当）。

## 目的

- システムプロンプトの `<available_skills>` インデックスを削減して毎ターンのトークン消費を抑える
- ただし「隠す＝読めなくなる」にしない。名前を知っていれば `skill_view('名前')` で復活できる
- 未使用スキルの棚卸し・無効化の運用は `skill-management` スキルの `references/skill-slimmer.md` に詳細

## パッチ内容

- 対象: `/opt/hermes/tools/skills_tool.py` L1278-1290 付近
- 変更: `skill_view` の disabled 拒否（early return）を「警告ログ+継続」に変更
  - 変更前: disabled スキルは一覧から消える + `skill_view` も拒否
  - 変更後: disabled スキルは一覧から消えるが、`skill_view` では読める（hydrate）

## 使い方

### 前提条件

- Hermes Agent が Docker コンテナで稼働している
- `/opt/hermes` はコンテナイメージ内ソース（root 所有・overlay レイヤー）のため、**コンテナ再作成で消える**
- 再適用が必要になるたびに本リポジトリのスクリプトを使う

### 適用（コンテナ更新後・root で実行）

```bash
# コンテナ内 root で実行
bash /opt/data/repos/hermes-skill-slimmer/scripts/install-skill-slimmer.sh
# 期待出力: "SKILL-SLIMMER: patched" or "already patched (no-op)"

# 反映には Hermes gateway 再起動が必要
docker restart hermes
```

冪等（2回実行しても no-op）。パッチ対象の OLD ブロックが一致しない場合はエラーで停止する。

### スキルを隠す

`/opt/data/config.yaml` の以下にスキル名を追加する:

```yaml
skills:
  disabled: [skill-a, skill-b]              # 全プラットフォーム
  platform_disabled:
    discord: [skill-c]                       # 特定プラットフォームのみ
```

config.yaml のリスト更新は `file-operations` スキルの
`scripts/config-yaml-update-list.py` を使うこと（`hermes config set` はリストを文字列化してしまうため）。

### 隠したスキルを読む

```python
skill_view(name='skill-a')  # disabled でも読める（hydrate）
```

### 使用頻度分析（何を隠すか）

- データ源1: `/opt/data/skills/.usage.json`（view_count / last_viewed_at 等）
- データ源2: `/opt/data/state.db` の tool レスポンス `content` JSON から `name` を抽出（`tool_calls` カラムは NULL が多い）
- 判定しきい値の例や詳細手順は `skill-management` スキルの `references/skill-slimmer.md` を参照

## リポジトリ構成

```
hermes-skill-slimmer/
├── README.md
├── CHANGELOG.md
├── LICENSE
└── scripts/
    ├── install-skill-slimmer.sh      # パッチ適用（冪等）
    └── generate-skill-catalog.py     # スキルカタログ自動生成
```

## 関連

- Obsidian: `Agent/Procedures/2026-08-10_Skill_Slimmer_適用フロー.md`
- `skill-management` スキル: `references/skill-slimmer.md`（詳細レシピ・判定しきい値）

## ライセンス

MIT License。Copyright (c) 2026 manate
