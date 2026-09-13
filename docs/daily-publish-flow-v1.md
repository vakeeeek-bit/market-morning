# Market Morning 日次公開フロー v1

## 目的

市場データの自動更新と、レポート・日本株詳細の公開を、不完全なJSONや日付の異なる組み合わせを公開しない形で運用する。

## 現行フロー

### 市場データ（自動）

1. GitHub Actionsが毎朝7:07 JSTに`update_market.py`を実行する。
2. `validate_data.py`で現行レポートとの組み合わせを検証する。日付差は警告、構造・整合性エラーは公開停止とする。
3. `data/history/YYYY-MM-DD/market.json`へ履歴を保存する。
4. `data/market.json`と履歴を1コミットで`main`へ反映する。
5. Vercelが`main`から本番公開する。

同じ更新処理は重複実行しない。`concurrency`により、先行処理の終了後に次の処理を開始する。

### レポートと日本株詳細（確認後に公開）

1. 公開候補用の同一ディレクトリに`report.json`と`japan-stocks.json`を置く。
2. 次のコマンドで、スキーマ、重要ニュースTOP3、日本株重要材料TOP5、詳細件数、日付をまとめて検証する。

   ```bash
   python scripts/prepare_publish.py /path/to/candidate --check-only
   ```

3. 内容確認後、`--check-only`を外して2ファイルを`data/`へ配置する。

   ```bash
   python scripts/prepare_publish.py /path/to/candidate
   ```

4. `report.json`と`japan-stocks.json`を必ず同じGitコミットで`main`へ反映する。
5. GitHub Actionsの`Validate Market Morning Data`が成功したことと、本番URLの表示を確認する。

候補ディレクトリに`market.json`または`status.json`がある場合は、それらも同じ検証・配置対象になる。検証失敗時は`data/`を変更しない。

## 履歴保存

`main`の対象データが更新されると`Archive Market Morning`が起動し、各JSONの基準日に対応する`data/history/YYYY-MM-DD/`へ保存する。履歴に差分がない場合はコミットしない。

## 現時点で手動の工程

- Web調査と出典確認
- レポート本文および日本株詳細JSONの生成・レビュー
- 本番画面の最終確認

調査・文章生成の完全自動化、外部通知、更新主体別の`status.json`運用は、責任範囲と失敗時の扱いが確定してから追加する。
