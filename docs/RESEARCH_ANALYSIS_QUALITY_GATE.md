# Research & Analysis Quality Gate v2

## 正本と優先順位

本書が調査・分析・公開判定の正本である。古い「9ゲート全PASSでなければサイト全体を停止」という規定は廃止し、公開単位ごとの判定へ統合する。品質基準は下げず、問題のある部分だけを除外して再検証する。

優先順位は、(1)本書、(2)`docs/QUALITY_GATE_RULES.md`、(3)`docs/daily-publish-flow-v1.md`、(4)その他の旧メモとする。実装は`publication_policy.py`、`research_quality.py`、`validate_data.py`、`prepare_publish.py`を正とする。

## 公開単位

| 公開単位 | 主なファイル | 他単位がBLOCKでも更新できる条件 |
|---|---|---|
| AIレポート | report / japan-stocks / research-evidence | 3ファイルの整合と分析ゲートが成立 |
| 市場データ | market / status / japan-market | 確認済み観測が安全に表示可能 |
| 確認済みニュース | news | 記事単位の一次資料検証が成立 |

古いAIレポートを、新しい市場データやニュースと同じ時点の分析として表示しない。各単位の更新日時、対象市場日、公開判定を別々に表示する。

## PASS / QUALIFIED / BLOCK

- **PASS**：掲載内容に必要な調査、出典、日付、数値、分析、反証が完了。
- **QUALIFIED**：調査は実施したが一部取得不能・未確定。実際の試行、確認時刻、不足、影響、除外した断定、次の調査を記録し、残りの内容を再検証済み。未確認事項に依存する方向判断は掲載しない。
- **BLOCK**：未調査、誤情報、重大な数値・日付矛盾、未確認政策の事実化、根拠不足、必須分析経路・反証の欠落。該当部分は公開不可。除外後に残余を再検証できれば、その公開単位はPASSまたはQUALIFIEDにできる。

QUALIFIEDは未調査の抜け道ではない。`publication_decision.unresolved_items`に不足、試行、影響範囲、除外した主張、確認時刻、次の行動を残す。

## Research Coverage Matrix

固定Universe、ニュース横断、市場異常値からの逆引き、前日認識との差分の4方向を毎日確認する。状態は`取得済 / 十分調査したが取得不能 / 該当材料なし / 未調査`。

| Tier | 取得不能時 |
|---|---|
| Critical | その情報に依存する内容はBLOCK。該当材料を完全に除外し、残りが独立して成立すれば全体はQUALIFIED可 |
| Required | 2経路以上の試行、影響評価、断定除外、再調査予定があればQUALIFIED可 |
| Supplemental | 1件以上の試行と不使用明示があれば他の内容を止めない |

Copper価格・在庫は任意掲載。使わない日はMatrixから除外できる。使う場合は取引所、限月、値種別、基準時刻、在庫単位、公表日、頻度、一次出典を検証する。

アナリスト変更はRequired。無料公開情報で網羅できない日は、確認済み変更だけを掲載し「変更なし」と断定しない。

## 9ゲート

9ゲートは廃止しない。公開単位ごとに次を判定する。

- Research Coverage：PASS / QUALIFIED可
- Data Integrity：PASS / QUALIFIED可（誤値は不可。欠測を除外・注記した場合のみ）
- Cross-Asset Consistency：PASS / QUALIFIED可（取得不能カテゴリの確認記録と影響限定が必要）
- Source Quality：PASS必須
- Analysis Logic：PASS必須
- Japan Transmission：PASS必須
- Counter-Evidence Audit：PASS必須
- Previous-Day Change：PASS必須
- Final Content Audit：PASS必須

重要材料ごとに、事実、実際の市場反応、市場内部、織り込み、解釈、日本株への途中経路、反証、変更条件、時系列を記録する。未確認政策・交渉結果を事実として扱う分析、SOXだけで日本半導体全面追い風とする分析はBLOCK。

## 未解決項目

`data/unresolved-items.json`へ引き継ぐ。次の日のワークシート作成時に読み込み、解消するまで残す。解消時は`resolved_item_ids`へ明記する。単に翌日になったことを理由に消さない。

## 完了条件

Schemaだけで完了としない。回帰テスト、Actions、main、Vercel、本番画面で、各単位の日付・判定・注釈が一致して初めて完了（検証済み）とする。


## Workへの指示・ユーザー操作の明示（全Work共通）

ユーザーの次の操作が必要だと判明した時点で、依頼を待たずに以下を先に伝える。

1. **どのWorkに**：既存の正式な部屋名を明示する（例：WEB｜サイト開発｜Work、REPORT｜YYYY-MM-DD モーニングレポート｜Work）。
2. **何を渡すか**：そのまま貼り付けられる具体的な指示文、対象PR・ファイル・完成条件を提示する。
3. **ユーザーが何を操作するか**：必要な操作を順番に示す。不要なら「ユーザー操作不要」と明記する。

追加で必要な承認・認証・課金・不可逆操作があれば、その理由、止まる工程、他に継続可能な作業を明示する。完了報告では、実施済み・未完了・次の担当と必要操作を区別する。ルール保存やPR作成のみを本番更新完了と表現しない。不要な新規Workは作らず既存Workを優先する。
