# Market Morning JSONスキーマ v1

## 1. 目的

本書は、Market Morning Webサイトで使用する最新JSONの正式なv1契約を定める。機械可読な正本は`schemas/*.schema.json`とし、本書は運用上の解釈を定める。

## 2. 対象ファイル

| データ | スキーマ | 役割 |
|---|---|---|
| `data/report.json` | `schemas/report.schema.json` | 最新のメインレポート |
| `data/market.json` | `schemas/market.schema.json` | 最新の自動取得市場データ |
| `data/japan-stocks.json` | `schemas/japan-stocks.schema.json` | 最新の日本株詳細ニュース |
| `data/status.json` | `schemas/status.schema.json` | 更新処理の稼働結果を示す任意の運用ステータス |

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

### `status.json`

`status`、`updated_at`、`message`。

`status.json`は画面本文の正本ではなく、更新処理の稼働結果を外部から確認するための任意ファイルとする。`status`は現状文字列とし、値の列挙は更新主体が確定していないためv1では固定しない。

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

生成後は4つの現行JSONが対応するスキーマに適合することを確認する。項目の意味、必須区分、互換性ルールを変更する場合は、本書とWebサイト仕様書も同時に更新する。
