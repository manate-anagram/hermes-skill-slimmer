# hermes-skill-slimmer

Hermes Agent のスキル一覧スリマー（Skill Slimmer）パッチ管理リポジトリ。

Tool Slimmer（ツールスキーマ削減）のスキル版。システムプロンプトの `<available_skills>` ブロック
（毎ターン約2,677トークン実測）から、`skills.disabled` / `skills.platform_disabled` で指定した
スキルを**隠す**。隠したスキルは `skill_view` で名前指定すれば**いつでも読める**（hydrate相当）。

## 動作確認済み環境

- **Hermes Agent v0.20.3**（2026-08-16 リリース）— パッチ・プラグイン検証済み
- Python 3.13.5（Hermes バンドル venv: `/opt/hermes/.venv/bin/python3`）
- 動作確認: 2026-08-18（Docker コンテナ構成・/opt/data 永続ボリューム）

> 初回公開時（2026-08-10）は v0.19.1 / Python 3.11 で検証。本リポジトリの
> `skill-slimmer-autoindex` プラグインは v0.20.3 の `on_skill_lifecycle` フックで
> 動作確認済み。

パッチ対象コード（`skills_tool.py`）は Hermes のバージョン更新で変わる可能性があるため、
適用時に「target block not found」が出た場合は `skills/skill-slimmer/SKILL.md` の手順に従って手動確認する。

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

### 一発インストール（推奨）

```bash
# リポジトリを取得して install.sh を実行
git clone git@github.com:manate-anagram/hermes-skill-slimmer.git /opt/data/repos/hermes-skill-slimmer
bash /opt/data/repos/hermes-skill-slimmer/install.sh
# → パッチ適用 + レシピ配置 + スキルカタログ生成を一括実行（冪等）
```

パスが標準と違う環境は環境変数で上書き:

```bash
SKILLS_DIR=/custom/skills HERMES_TOOLS=/custom/skills_tool.py bash install.sh
```

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

```text
hermes-skill-slimmer/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── install.sh                      # one-shot installer (patch + recipe + catalog)
├── skills/
│   └── skill-slimmer/SKILL.md      # distributed recipe (single SKILL.md source)
└── scripts/
    ├── install-skill-slimmer.sh    # idempotent patch applier
    └── generate-skill-catalog.py   # skill catalog generator
```

## スキルカタログの自動更新（skill-slimmer-autoindex プラグイン）

スキル追加・再有効化時にカタログを自動再生成する Hermes プラグイン。
`on_skill_lifecycle` フックで `generate-skill-catalog.py` を呼び出す。

- 配置: `/opt/data/plugins/skill-slimmer-autoindex/`
- 詳細: `skills/skill-slimmer/SKILL.md` の「スキルカタログの自動更新」セクション
- カタログ出力先: `skill-management` スキル配下の `references/skill-catalog.md`

> Note: `/reload-skills` alone does NOT trigger the hook (Hermes core behavior).
> Add skills via `skill_manage` so the lifecycle event fires.

## 関連

- `skill-management` スキル: `references/skill-slimmer.md`（install.sh が `skills/skill-slimmer/SKILL.md` から同期配置する）
- 自動更新プラグイン: `skill-slimmer-autoindex`（本リポジトリ外の `/opt/data/plugins/` に配置）

## Operational Notes / Pitfalls

- **Editing the repo alone does NOT affect the live Hermes.** The patch target
  is `/opt/hermes/tools/skills_tool.py` (root-owned). You must run
  `scripts/install-skill-slimmer.sh` as root inside the container, then restart
  the gateway for changes to take effect.
- **Container recreation (image update) always wipes the patch.** Re-run steps
  1–2 after every Hermes upgrade.
- The patch script is idempotent: if the OLD block is not found it stops with an
  error instead of corrupting the file.
- If a Hermes upgrade changes `skills_tool.py`, the script's OLD block may no
  longer match and fail. Inspect the target lines and update the script.
- `skill-slimmer-autoindex` does NOT fire on `/reload-skills` (Hermes core
  behavior). Add or re-enable skills via `skill_manage` so the
  `on_skill_lifecycle` event fires and the catalog regenerates.

## ライセンス

MIT License。Copyright (c) 2026 manate
