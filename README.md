# hermes-skill-slimmer

Hermes Agent の**スキル一覧スリマー**。システムプロンプトの `<available_skills>` ブロックから、
`skills.disabled` / `skills.platform_disabled` で指定したスキルを**隠して**毎ターンのトークンを削減する。
隠したスキルは**名前を知っていれば `skill_view` でいつでも読める**（hydrate）。

Tool Slimmer（ツールスキーマ削減）のスキル版。

## 動作確認済み環境

- **Hermes Agent v0.21.5**（v2026.9.24 / upstream `749220ef`）— 2026-09-25 検証
- Python 3.13.5（Hermes バンドル venv: `/opt/hermes/.venv/bin/python3`）
- Docker コンテナ構成（`/opt/hermes` = イメージ層 / `/opt/data` = 永続ボリューム）

> 初回公開（2026-08-10）は v0.19.1 / Python 3.11。プラグインのフック名・フック契約は v0.20 系以降で安定。

## 仕組み（2段構え）

1. **隠す**: `skills.disabled`（全プラットフォーム）/ `skills.platform_disabled.<platform>` に名前を入れると
   `<available_skills>` インデックスから消える（＝トークン削減）
2. **hydrate（読める状態を保つ）**: 標準の Hermes は「disabled スキルは `skill_view` でも拒否」なので、
   隠したまま読めるようにする仕組みが要る。本リポジトリはこれを
   **プラグインの `transform_tool_result` フック**で実現する（`plugins/skill-slimmer-autoindex/hydrate.py`）:
   - `skill_view` が返した `Skill '…' is disabled` 拒否**だけ**を検知（それ以外の結果は素通し）
   - `tools.skills_tool._is_skill_disabled` を**その呼び出し中だけ** False 固定にし、本体実装をそのまま再実行
   - 得られた実コンテンツをツール結果として差し替える（失敗時は元の結果をそのまま返す＝fail-open）
   - disabled 判定は `skills_tool.py`（通常スキル）と `skills_tool_plugin.py`（plugin 名前空間スキル）が
     **同じ1関数**を参照するため、この1箇所で**両ゲート**をカバーする

**なぜコアパッチをやめたか**: `/opt/hermes` はコンテナイメージ層なので、ファイルパッチは
イメージ更新・コンテナ再作成のたびに消える（＝毎回 root で再適用）。プラグインは `/opt/data/plugins`
（永続ボリューム）にあり、**更新後も何もしなくてよい**。

## インストール

```bash
git clone git@github.com:manate-anagram/hermes-skill-slimmer.git /opt/data/repos/hermes-skill-slimmer
bash /opt/data/repos/hermes-skill-slimmer/install.sh
# → プラグイン配置 + 有効化 + レシピ配置 + カタログ生成（冪等）
# → gateway を再起動してフックを読み込ませる（フックはプロセス起動時に読まれる）
```

パスが標準と違う環境は環境変数で上書き:

```bash
HERMES_HOME=/custom/data SKILLS_DIR=/custom/skills bash install.sh
```

### 旧方式（コアパッチ）— 緊急時のみ

```bash
bash install.sh --legacy-patch
# または単体で:
sudo bash scripts/install-skill-slimmer.sh      # root（/opt/hermes を書き換える）
sudo bash scripts/revert-skill-slimmer.sh --apply   # 外して stock に戻す
```

- ⚠️ **プラグインが有効な間は当てない**。コア側の拒否が消えると **hydrate フックが一度も発火しない**
  （差し替えるべき「拒否」が来なくなるため）→ live 検証ができなくなる
- 通常状態は「stock ブロックが 1 件」: `grep -c "is disabled. Enable it with" /opt/hermes/tools/skills_tool.py`

## 使い方

### スキルを隠す

`$HERMES_HOME/config.yaml`:

```yaml
skills:
  disabled: [skill-a, skill-b]          # 全プラットフォーム
  platform_disabled:
    discord: [skill-c]                  # 特定プラットフォームのみ
```

リスト編集は `hermes config set` だと文字列化されて壊れるので、YAML を直接編集する
（例: `file-operations` スキルの `config-yaml-update-list.py` のような全置換方式のスクリプトを使う）。

### 隠したスキルを読む

```python
skill_view(name='skill-a')   # disabled でも内容が返る（hydrate）
```

### どのスキルを隠すか（使用頻度分析）

- データ源1: `$HERMES_HOME/skills/.usage.json`（`view_count` / `last_viewed_at` / `last_used_at`）
- データ源2: `$HERMES_HOME/state.db` の **tool レスポンス `content`** から `name` を抽出
  （`tool_calls` カラムは NULL が多い＝検出漏れする）
- 判定は**2系統の突合**: 「直近30日に `.usage.json` の `last_viewed_at` も state.db の `skill_view` 呼び出しも無い」= 非表示候補

詳細な判定しきい値・手順は `skills/skill-slimmer/SKILL.md` を参照。

## リポジトリ構成

```text
hermes-skill-slimmer/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── install.sh                              # one-shot installer (plugin + recipe + catalog)
├── plugins/
│   └── skill-slimmer-autoindex/            # hydrate の実体（配布物）
│       ├── plugin.yaml                     # provides_hooks: on_skill_lifecycle / pre_llm_call / transform_tool_result
│       ├── __init__.py                     # フック登録（hydrate + カタログ再生成 + 思い出し注入）
│       └── hydrate.py                      # transform_tool_result フック本体（disabled 拒否を差し替える）
├── skills/
│   └── skill-slimmer/SKILL.md              # 配布用レシピ（使用頻度分析・隠し方の手順）
└── scripts/
    ├── install-skill-slimmer.sh            # 旧: コアパッチ適用（冪等・緊急時のみ）
    ├── revert-skill-slimmer.sh             # 旧: コアパッチ逆適用（stock に戻す）
    └── generate-skill-catalog.py           # カタログ生成（隠し含む全スキル一覧）
```

## プラグインが担う3つのフック

| フック | 用途 |
|---|---|
| `transform_tool_result` | **hydrate**: `skill_view` の disabled 拒否を実コンテンツに差し替える |
| `on_skill_lifecycle` | スキル追加・再有効化・削除時に `generate-skill-catalog.py` を走らせてカタログを再生成 |
| `pre_llm_call` | 「一覧に出ていないスキルも `skill_view` で読める／カタログで探せる」を毎ターン注入（Tool Slimmer の `FALLBACK_INSTRUCTION` と同型） |

環境変数で挙動を調整できる（`hydrate.py` / `__init__.py` が参照）:

- `HERMES_PYTHON` — カタログ生成に使う Python（既定: 実行中プロセスの python）
- `SKILL_SLIMMER_CATALOG_SCRIPT` — カタログ生成スクリプトのパス
- `SKILL_SLIMMER_CATALOG_PATH` — `pre_llm_call` が案内するカタログのパス

> Note: `/reload-skills` では `on_skill_lifecycle` は発火しない（Hermes コア仕様）。スキルは
> `skill_manage` 経由で追加・再有効化する。

## Operational Notes / Pitfalls

- **プラグインの変更もフックもプロセス起動時に読まれる** → 反映には gateway 再起動が必要
- **コアパッチを当てると hydrate フックは静かに無効化される**（本体が拒否を返さなくなるため）。
  併用はできるが、その状態でプラグインの検証はできない
- **上流が拒否メッセージを変えたら hydrate は止まる**（fail-open で素の拒否が返るだけ・壊れはしない）。
  その時直すのは `hydrate.py` の `_DISABLED_RE` **1行**で、コアパッチは要らない
- **`transform_tool_result` フックは結果の文字列を丸ごと置換できる**ため、誤爆すると無関係なツール出力を壊しうる。
  本実装は「JSON かつ `success != true` かつ `Skill '…' is disabled` を含む」場合**だけ**介入する
- カタログ生成は PyYAML を要求する実装に差し替える場合は、Hermes の venv Python（`/opt/hermes/.venv/bin/python3`）で走らせる
- 本番環境では **`SKILL_SLIMMER_CATALOG_SCRIPT` 等を `$HERMES_HOME/.env` に置く**と再起動後も効く

## ライセンス

MIT License。Copyright (c) 2026 manate
