# Market Morning JSONスキーマ v1

## 1. 目的

本書は、Market Morning Webサイトで使用する最新JSONの正式なv1契約を定める。機械可読な正本は`schemas/*.schema.json`とし、本書は運用上の解釈を定める。

## 2. 対象ファイル

| データ | スキーマ | 役割 |
|---|---|---|
| `data/report.json` | `schemas/report.schema.json` | 最新のメインレポート |
| `data/market.json` | `schemas/market.schema.json` | 最新の自動取得市場データ |
| `data/japan-stocks.json` | `schemas/japan-stocks.schema.json` | 最新の日本株詳細ニュース |
| `data/japan-market.json` | `schemas/japan-market.schema.json` | 日本株のランキング・市場内部・朝シナリオ答え合わせ |
| `data/status.json` | `schemas/status.schema.json` | 更新処理の稼働結果を示す任意の運用ステータス |
| `data/market-context.json` | `schemas/market-context.schema.json` | 週次中心で更新する現在の市場環境・日本株・暮らしへの波及 |
| `data/glossary.json` | `schemas/glossary.schema.json` | 表示時に外部APIを使わない固定用語辞書 |

履歴JSONは、同名の最新JSONと同じスキーマに従う。

## 3. 共通ルール

- 文字コードはUTF-8、最上位はJSONオブジェクトとする。
- `NaN`、`Infinity`、`-Infinity`は使用しない。
- 日付専用項目は`YYYY-MM-DD`とする。
- 取得できない値を推測で補完しない。
- 分析文など文字列表示を前提とする項目は、未取得時に`「確認できず」`等を使用できる。
- 数値演算に使う項目は、未取得時に`null`を使用する。数値項目へ説明文字列を混在させない。
- 一覧に該当項目がない場合は空配列`[]`を使用する。配列そのものを任意とした項目は省略も許容する。
- 任意項目は省略可能。値が存在する場合はスキーマで定めた型に従う。
- v1では将来拡張と旧履歴互換のため未知キーを許容する。既存キーの意味変更や型変更は行わず、新しいキーを追加する。

## 4. 必須項目

### `report.json`

`report_date`、`target_market_date`、`updated_at`、`report_type`、`quick_view`、`executive_summary`、`news`、`scenarios`、`market_overview`、`data_quality`、`final_conclusion`。

`week_period`は週間レポートで使用する任意項目とする。その他のセクションは、データがある場合のみ掲載できる任意項目とする。

### `market.json`

`updated_at`、`timezone`、`markets`、`data_quality`。

`markets`の個別市場キーは、取得対象の追加・廃止に備えて固定しない。各市場オブジェクトは、現行の`name`、`ticker`、`price`、`previous`、`change`、`change_pct`、`status`、`market_date`、`previous_market_date`の型に従う。

### `japan-stocks.json`

`report_date`、`target_market_date`、`updated_at`、`report_type`、`japan_quick_view`、`top_stories`、`important_stories`、`other_stories`、`data_quality`。

3分類のニュースがない場合も、対応するキーを空配列で保持する。

### `japan-market.json`

`updated_at`、`market_date`、`data_phase`、`source`、`scope`、`sector_ranking`、`sector_stock_ranking`、`trading_value_ranking`、`volume_surge_ranking`、`market_internals`、`market_regime`、`key_drivers`、`rotation_read`、`sector_quality`、`scenario_review`、`monitoring_points`、`methodology`、`data_quality`。

`data_quality.date_alignment`には、朝レポート、セクターETF、主要監視銘柄、指数連動ETFの市場日と整合判定を保持する。朝レポート、セクターETF、主要監視銘柄の日付が一致しない場合、`scenario_review.status`を`判定可能`にしてはならない。

`market_regime`は実測・推定・判定対象外を`status`で区別する。`rotation_read`は投資主体別売買ではなく、値動きから見た推定であることを名称と注記の両方に保持する。`key_drivers`の基準日が日本株現物の`market_date`より新しい場合、`pricing_status`を`日本株現物に未反映`とする。詳細は`docs/JAPAN_INVESTOR_VIEW_SPEC.md`を参照する。

### `status.json`

`status`、`updated_at`、`message`。

`status.json`は画面本文の正本ではなく、更新処理の稼働結果を外部から確認するための任意ファイルとする。`status`は現状文字列とし、値の列挙は更新主体が確定していないためv1では固定しない。

### `market-context.json`

`updated_at`、`period_start`、`period_end`、`headline`、`summary`、`timeline`、`current_drivers`、`japan_connection`、`daily_life_impacts`、`scenario_change_conditions`、`sources`。

日次レポートから分離し、原則週1回または市場環境の重大変化時に更新する。`timeline`は対象期間内の日付順で3〜6件とする。`daily_life_impacts.evidence_type`は`直接影響`、`間接影響`、`可能性`のいずれかとし、制度・税制変更は市場要因と分離して公式根拠を確認する。

### `glossary.json`

`updated_at`、`terms`。各用語は`term`、`short`、`why_it_matters`、`aliases`を持つ。表示時にAIまたは外部APIを呼ばず、用語の重複と空値を公開前に検証する。

## 5. 互換性

- QUICK VIEWの`top_news`は正式入力を`{"title":"見出し"}`形式のオブジェクト配列とする。
- 表示側は既存履歴のため文字列配列も読み込めるが、新規データでは使用しない。
- `null`、空配列、欠損キーは同一ではない。`null`は値を取得できない場合、空配列は該当件数ゼロ、欠損は任意セクション自体を生成しない場合に使用する。
- 必須項目の欠損、不正JSON、日付形式違反、規定外の型は公開前エラーとする。
- 未知キーは警告対象にせず読み飛ばす。将来v2で禁止へ変更する場合は移行期間を設ける。

## 6. 生成と更新

現行データからスキーマを再生成する場合は、リポジトリ最上階層で次を実行する。

```bash
python scripts/generate_json_schemas.py
```

生成後は7つの現行JSONが対応するスキーマに適合することを確認する。項目の意味、必須区分、互換性ルールを変更する場合は、本書とWebサイト仕様書も同時に更新する。
