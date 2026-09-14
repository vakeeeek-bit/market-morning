# Market Morning 日次公開フロー v1

## 定時実行

- 市場データ取得はGitHub Actionsで日本時間の平日6:20に開始する。
- cronはUTC基準のため、`20 21 * * 0-4`（UTCの日曜〜木曜21:20）を使用する。
- ChatGPTのMarket Morningタスクは、市場データ更新の検証完了を待つため日本時間の平日6:45に開始する。
- ChatGPTは、公開済みの`data/status.json`が当日成功であることを確認し、`data/market.json`を数値の正本として使用する。
- ChatGPTからGitHubへレポート本文を自動反映する処理は、JSON適合と品質ゲートの検証後にのみ有効化する。

## 目的

市場データの自動更新と、レポート・日本株詳細の公開を、不完全なJSONや日付の異なる組み合わせを公開しない形で運用する。

## 現行フロー

### 市場データ（自動）

1. GitHub Actionsが平日6:20 JSTに`update_market.py`を実行する。
2. `validate_data.py`で現行レポートとの組み合わせを検証する。日付差は警告、構造・整合性エラーは公開停止とする。
3. 検証成功時だけ`status.json`へ市場データ更新成功時刻を記録し、公開候補を再検証する。
4. `data/history/YYYY-MM-DD/market.json`へ履歴を保存する。
5. `data/market.json`、`data/status.json`、履歴を1コミットで`main`へ反映する。
6. Vercelが`main`から本番公開する。

同じ更新処理は重複実行しない。`concurrency`により、先行処理の終了後に次の処理を開始する。

### レポートと日本株詳細（確認後に公開）

1. ChatGPTタスクを平日6:45 JSTに開始し、当日成功の`status.json`と検証済み`market.json`を読み込む。
2. `market.json`に存在する数値は同ファイルを正本とし、Web検索値で置換しない。
3. 公開候補用の同一ディレクトリに`report.json`と`japan-stocks.json`を置く。
4. 次のコマンドで、スキーマ、重要ニュースTOP3、日本株重要材料TOP5、詳細件数、日付をまとめて検証する。

   ```bash
   python scripts/prepare_publish.py /path/to/candidate --check-only
   ```

5. 内容確認後、`--check-only`を外して2ファイルを`data/`へ配置する。

   ```bash
   python scripts/prepare_publish.py /path/to/candidate
   ```

6. `report.json`と`japan-stocks.json`を必ず同じGitコミットで`main`へ反映する。
7. GitHub Actionsの`Validate Market Morning Data`が成功したことと、本番URLの表示を確認する。

候補ディレクトリに`market.json`または`status.json`がある場合は、それらも同じ検証・配置対象になる。検証失敗時は`data/`を変更しない。

### 自動公開の品質ゲート

次のいずれかに該当する場合は自動公開しない。

- 当日の`status.json`が成功状態でない。
- S&P500、NASDAQ総合、NASDAQ100、NYダウ、Russell2000、SOX、米2年・10年金利、DXY、USD/JPY、VIX、Gold、Copper、WTI、Brentのいずれかが欠測または基準日不明。
- 米11セクターのうち3系列以上が欠測。
- 終値、清算値、現在値、日中高安または先物限月が区別されていない。
- `report.json`と`japan-stocks.json`が正式スキーマに適合しない、または日付・TOP5が一致しない。
- 重要な経済指標、中央銀行、関税、制裁の確認結果または「該当なし」の記録がない。

品質ゲート不合格時は、理由を出力して既存の正常な公開データを維持する。

## 履歴保存

`main`の対象データが更新されると`Archive Market Morning`が起動し、各JSONの基準日に対応する`data/history/YYYY-MM-DD/`へ保存する。履歴に差分がない場合はコミットしない。

## 現時点で手動の工程

- Web調査と出典確認
- レポート本文および日本株詳細JSONの生成・レビュー
- 本番画面の最終確認

調査・文章生成の完全自動化、外部通知、更新主体別の`status.json`運用は、責任範囲と失敗時の扱いが確定してから追加する。
