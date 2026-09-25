---
name: skill-slimmer
description: "Use when スキル一覧をスリム化/未使用スキルを非表示にしたい。使用頻度分析（usage.json + state.db）→ config無効化 → hydrate復活の手順。"
trigger: manual
tags: [skill-management, token-saving, hydration]
---

# Skill Slimmer — 使用頻度分析→非表示 詳細レシピ（2026-08-10 実装 / 2026-09-25 プラグイン hydrate 化）

システムプロンプトの `<available_skills>` ブロック（毎ターン約2,677トークン/10,711 chars 実測）から
未使用スキルを隠してトークンを削減する手法。Tool Slimmer（ツール削減）のスキル版。

> **配置（2026-08-10 マナテ確定）**: このリポジトリでは配布用 SKILL.md 形式で保持。
> install.sh が環境に応じて配置先を変える:
> - dev-workflow（旧名 skill-management）がある環境 → `dev-workflow/references/skill-slimmer.md` に同期（独立スキルにしない）
> - 無い環境 → `skills/skill-slimmer/SKILL.md` として独立スキル配置
>
> **役割分担（2026-09-25 現在）**: 機構（hydrate の実装・死活確認・更新後の扱い）は本ファイル＋ `plugins/skill-slimmer-autoindex/`、
> 運用（何を隠すか・しきい値・config 更新手順）も本ファイル。**コアパッチは退役**（保険として残置）。

## 常時非表示＋オンデマンドロード（使用頻度に関わらない無効化）

使用頻度が低いからではなく「**普段は一覧に出したくない**」スキルも無効化対象にする。
- 実例: ponytail（コーディングスタイル）は 30日3回使用ありでも 2026-08-10 に無効化。
  通常応答・ERP に口調/ルールが漏れるのを防ぐ意図（Persona Isolation の一環）
- 仕組み: `platform_disabled.discord` に入れれば一覧から消えるが、**hydrate（プラグイン方式）**で
  必要時 `skill_view('名前')` で読める = オンデマンドロード
- **delegate_task で子エージェントに委譲する際は、context に1行書いて子に自分で読ませる（案A・2026-08-10 マナテ確定）**:
  ```
  コーディングタスクは ponytail ルールに従うこと。開始前に skill_view('ponytail') で全文を読むこと。
  ```
  子エージェントは `skill_view` を実行可能（delegate_task の制限リストに含まれない）＋ hydrate（プラグインの `transform_tool_result` フック）で disabled でも読める。
  旧方式（親が全文コピー）は context 肥大＋コピー漏れリスクのため廃止。保険として「YAGNI / stdlib 優先 / 最短 diff」の3語を添えるのも可
- 判断軸: 「普段読み込まれてほしくない」というユーザー意図があれば、使用回数が高くても無効化してよい

## 背景: なぜ「隠す＋hydrate」が要るのか

- `skills.disabled` / `skills.platform_disabled.<pf>`（config.yaml）にスキル名を入れると
  `<available_skills>` インデックスから消える（トークン削減）✅
- **ただし標準状態では disabled スキルは `skill_view` も拒否される**（`skills_tool.py` の
  `_is_skill_disabled` チェックが early return で `"is disabled"` エラーを返す）
  = 「隠すと読めない」→ これでは必要時に復活できない ❌
- 対策: **hydrate はプラグイン側に置く**（`plugins/skill-slimmer-autoindex/hydrate.py`、`transform_tool_result` フック）。
  本体を書き換えないので **`hermes update` / コンテナ再作成で消えない**（`$HERMES_HOME/plugins` は永続）
  = 一覧からは消えるが、名前を知ってれば `skill_view` でいつでも読める（hydrate相当）

## hydrate の実装（プラグイン・パッチではない）

`plugins/skill-slimmer-autoindex/hydrate.py` が `transform_tool_result` フック
（`model_tools.handle_function_call` の最終段＝戻り値の str がツール結果を置換）で:

1. `skill_view` の結果が `Skill '…' is disabled` 拒否なら検知（それ以外は `None` を返して素通し）
2. `tools.skills_tool._is_skill_disabled` を**その呼び出し中だけ** False 固定
3. 本体の実装を**そのまま再実行**して実コンテンツを返す（例外・API 変化時は元の結果をそのまま返す＝fail-open）

disabled 判定は `skills_tool.py`（通常スキル）と `skills_tool_plugin.py`（plugin 名前空間スキルの第2ゲート）が
**同じ1関数**を参照するので、この1箇所で**両ゲート**をカバーする（旧パッチは第1ゲートのみだった）。

**旧方式（保険・緊急時のみ）**: `/opt/hermes/tools/skills_tool.py` の disabled チェックを
「警告ログ＋継続」に緩めるファイルパッチ（`scripts/install-skill-slimmer.sh` / 戻すのは `revert-skill-slimmer.sh --apply`）。
⚠️ **パッチが残っている間は hydrate フックが一度も発火しない**（本体が拒否を返さないため）＝ live 検証はパッチ除去後に行う。

## 永続化（コンテナ更新で消える問題への対策）

`/opt/hermes` は Docker イメージ内ソース（git管理外・root所有・overlay）→ **コンテナ再作成で消える**。
`/opt/data` は NAS 永続ボリューム → ここに置いたものは残る。

| 場所 | 役割 | 所有 |
|---|---|---|
| `/opt/data/repos/hermes-skill-slimmer/` | リポジトリ（git管理） | hermes |
| `/opt/data/repos/hermes-skill-slimmer/scripts/install-skill-slimmer.sh` | 冪等なパッチ再適用 | hermes |
| `/opt/data/tool-slimmer/backups/skills_tool.py.bak-*` | バックアップ | hermes |
| `/opt/hermes/tools/skills_tool.py` | パッチ対象 | **root** |

コンテナ更新後（root 不要）:
- **何もしない**。hydrate は `$HERMES_HOME/plugins/skill-slimmer-autoindex/`（永続ボリューム）側で完結し、
  `hermes update` / コンテナ再作成でも消えない。フックはプロセス起動時に読まれるので、
  プラグインを更新した時だけ gateway を再起動する
- 確認（更新のたびに1回）: 隠しスキルを1つ `skill_view` する → 内容が返れば OK。
  起動ログに `registered transform_tool_result (hydrate) hook` があれば配線もOK
- 緊急時の旧パッチ: `bash scripts/install-skill-slimmer.sh`（冪等・OLD 不一致で安全に停止）／戻すのは `--apply` 付きの `revert-skill-slimmer.sh`

## 使用頻度分析（どのスキルを隠すか）

### データ源1: `.usage.json`
`/opt/data/skills/.usage.json` — skill_view/skill_manage で自動更新される
（view_count / use_count / last_viewed_at / last_used_at / created_by 等）。

### データ源2: state.db の tool_calls JSON（実実行履歴）
`/opt/data/state.db` の `messages` テーブル。列: `tool_calls`（JSON配列）, `timestamp`（epoch秒）。

```python
import sqlite3, json
from datetime import datetime, timezone, timedelta
from collections import Counter

db = sqlite3.connect('/opt/data/state.db')
db.row_factory = sqlite3.Row
cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
c_30d = Counter()
rows = db.execute("SELECT tool_calls, timestamp FROM messages WHERE tool_calls IS NOT NULL").fetchall()
for r in rows:
    try:
        calls = json.loads(r['tool_calls'])
    except Exception:
        continue
    ts = r['timestamp'] or 0
    for call in (calls if isinstance(calls, list) else []):
        fn = call.get('function', {}).get('name', '')
        if fn == 'skill_view' and ts >= cutoff:
            try:
                a = json.loads(call.get('function', {}).get('arguments', '{}'))
                c_30d[a.get('name', '')] += 1
            except Exception:
                pass
```

注意: messages テーブルの列名は `json` ではなく `tool_calls`（`json_extract(json,...)` は使えない）。

### データ源2b: state.db の tool レスポンス content から抽出（実践版・2026-08-10 実測）

**`tool_calls` カラムは NULL の行が多く、上記クエリでは検出漏れする**（アシスタント呼び出し側に記録が残らない）。
実績は **tool レスポンスの `content` JSON** に `name` フィールドとして残るので、こちらを使うのが確実:

```python
import sqlite3, json
from datetime import datetime, timezone, timedelta

db = sqlite3.connect('/opt/data/state.db')
cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
c_30d = {}
cur = db.execute(
    "SELECT tool_name, content, timestamp FROM messages "
    "WHERE tool_name IN ('skill_view','skill_manage','skills_list')")
for tool_name, content, ts in cur:
    try:
        d = json.loads(content)
    except Exception:
        continue
    name = d.get('name') if isinstance(d, dict) else None
    if not name or ts < cutoff:
        continue
    c_30d[name] = c_30d.get(name, 0) + 1
```

- tool response の content は `{"success": true, "name": "<skill名>", ...}` 形式
- 判定は state.db 実績 + usage.json の last_viewed_at/last_used_at の **2系統突合**（片方だけだと誤判定する）
- 表示中スキルだけに絞るには、システムプロンプトの `<available_skills>` 一覧（または直近の skills_list 結果）と突合する

### 判定ロジック（2系統を突合）
「直近30日に usage.json の last_viewed_at も state.db の skill_view 呼び出しも無い」= 非表示候補。

### 判定しきい値の例（2026-08-10 マナテ確定）
- **30日0回 かつ usage.json の last_viewed_at も30日外** = 即無効化候補
  （実績: ideation / dspy / financial-consultation / workplace-consultation を無効化）
- **30日0回 でも usage.json が30日以内** = 乖離あり。state.db の tool レスポンスに記録が
  残らないケースがあり「実は読まれてる」可能性 → 要確認（view_count が高いほど実質使用中）
- **30日1回** = 次回棚卸し（30日後）の最有力候補
  （実績: persistent-tooling / image-prompt-engineering / hermes-plugins / hermes-dashboard-auth / ugreen-nas など）
- **30日2〜10回** = 低頻度だが使われている → 基本残す
- **30日10回以下** = 参考基準。無効化判断は「30日0回＋usage.json も30日外」のみで行う
- 直近一括作成（例: 08-08 に3件）は「作っただけ」でも将来使う可能性があるため保留が安全

### 実績（2026-08-10）
- 表示中128スキルのうち60個が直近30日未使用 → 約40%削減見込み
- 旧版重複（aivis系旧版 / obsidian-sync系旧版 / x-twitter系旧版）は新しいスキルに統合済みの可能性大 → 優先非表示

## 無効化の実行手順（config.yaml 更新）

**⚠️ エージェントから config.yaml は直接編集不可**（patch/write_file 拒否）。`hermes config set` はリストを文字列化するため使えない。**専用スクリプト必須**:
`/opt/data/skills/software-development/file-operations/scripts/config-yaml-update-list.py`

### 手順

1. **現状把握**: `yaml.safe_load` で `skills.platform_disabled.discord` の既存リストを取得
2. **全置換方式なので「既存全件＋追加分」をカンマ区切りで渡す**（追加のみ渡すと既存が消える！）
   ```bash
   # dry-run（推奨・何も書かない）
   python3 /opt/data/skills/software-development/file-operations/scripts/config-yaml-update-list.py \
     skills.platform_disabled.discord "existing1,existing2,...,new1,new2"
   # 適用（バックアップ→置換→型検証を自動実行）
   python3 /opt/data/skills/software-development/file-operations/scripts/config-yaml-update-list.py \
     skills.platform_disabled.discord "existing1,existing2,...,new1,new2" --apply
   ```
3. **バックアップ自動生成**: `/opt/data/backups/config/config.yaml.bak-platform_disabled-discord-YYYYMMDD-HHMMSS`
4. **適用後検証**: yaml.safe_load で件数確認 + 追加分が含まれること
5. **ゲートウェイ再起動で反映**: `/command/s6-svc -r /run/service/gateway-default`（s6-svc は PATH に無いのでフルパス必須）

### 実績（2026-08-10 2回目）
- 表示中58スキルのうち30日未使用7件を特定 → うち4件（ideation / dspy / financial-consultation / workplace-consultation）を無効化
- 直近作成（08-08 一括）の huggingface-model-stocking / open-weights-video-models / geo-municipal-research は保留（「作っただけ」でも将来使う可能性）
- 全置換で既存89件＋4件=93件 → さらに ponytail（常時非表示）追加で94件に更新、バックアップ＋型検証OK

## 手順メモ（Obsidian）
`Agent/Procedures/2026-08-10_Skill_Slimmer_適用フロー.md`

## プラグイン `skill-slimmer-autoindex`（hydrate ＋ カタログ ＋ 思い出し注入）

1つのプラグインが3つの役割を持つ（`$HERMES_HOME/plugins/skill-slimmer-autoindex/`）:

| フック | 役割 |
|---|---|
| `transform_tool_result` | **hydrate**（`hydrate.py`）: `skill_view` の disabled 拒否を実コンテンツに差し替える |
| `on_skill_lifecycle` | スキル追加・再有効化・削除（`skill_manage` の create/install/restore/removed/enabled/disabled 等）で `scripts/generate-skill-catalog.py` を実行し `skill-catalog.md` を再生成 |
| `pre_llm_call` | 「一覧に出ていないスキルも `skill_view` で読める／カタログで探せる」を毎ターン注入（Tool Slimmer の `FALLBACK_INSTRUCTION` と同型） |

- **有効化**: `hermes plugins enable skill-slimmer-autoindex --no-allow-tool-override`（フックのみなので override 権限は不要）
  → gateway 再起動でロード
- **環境変数**: `HERMES_PYTHON`（カタログ生成に使う Python）/ `SKILL_SLIMMER_CATALOG_SCRIPT`（生成スクリプトのパス）/
  `SKILL_SLIMMER_CATALOG_PATH`（`pre_llm_call` が案内するカタログの位置）
- **注意**: `/reload-skills` 単体では `on_skill_lifecycle` は発火しない（Hermes コア仕様）。スキル追加は `skill_manage` 経由で行うこと

このプラグインにより、`skill-management` 配下の `references/skill-catalog.md` は
スキル変更のたびに手動実行なしで最新状態を保つ。
