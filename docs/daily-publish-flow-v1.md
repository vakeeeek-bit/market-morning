# Market Morning 日次公開フロー v2

## 原則

公開停止と作業停止を分ける。ある公開単位がBLOCKでも、市場再取得、調査、修正、確認済みニュース、独立して安全な市場データの更新を続ける。ユーザーへ同じ公開許可を取り直さない。

## 6:20 / 7:20 / 8:20 市場更新

1. `update_market.py`が各系列を通常取得で最大3回試す。
2. 失敗系列だけYahoo個別chart取得へ切り替える。
3. なお取得不能なら、過去の検証済み値を元の`market_date`付きで保持し、`取得不能・前回値維持`と表示する。最新値とは扱わない。
4. 主要指数の新規観測が安全な最低数を満たせば市場単位をQUALIFIED更新する。広範な障害ならBLOCKし、既存正本を保持して試行記録を保存する。
5. 市場単位の検証は古いAIレポートに依存させない。
6. `status.json`へ市場単位のPASS/QUALIFIED、更新時刻、対象コンポーネントを記録する。

## AIレポート

1. `create_research_evidence.py`で未完了状態のワークシートと前日からの未解決項目を読み込む。
2. 4方向調査、数値・時系列、分析経路、反証、前日との差分を埋める。
3. 取得不能項目は試行・確認時刻・不足・影響・除外した断定・次の調査を記録する。
4. BLOCK材料は本文から除外し、残りの結論を再検証する。主要結論が成立しなければ結論を保留する。
5. `report.json`、`japan-stocks.json`、`research-evidence.json`を同時に検証する。
6. PASSまたはQUALIFIEDならAIレポート単位を配置する。BLOCKなら旧レポートを上書きせず、他単位の更新を続ける。

```bash
python scripts/prepare_publish.py candidate --components report --check-only
python scripts/prepare_publish.py candidate --components report
```

## 確認済みニュース

記事ごとに一次資料、発表日、確認時刻、事実・解釈・制約を検証する。不合格記事は除外理由を残し、無関係な合格記事を止めない。総合レポートのPASSとはみなさない。

```bash
python scripts/prepare_publish.py candidate --components news
```

## 複数単位

`--components auto`またはカンマ区切りで処理する。各単位は別に検証され、BLOCK単位は配置されない。安全な単位が1つでもあれば、それを配置して処理を継続する。

## 履歴と表示

- report、market、japan-stocks、research-evidence、newsは実際の基準日へ保存する。
- 後日調査はretrospectiveと実際の確認時刻を残し、当時確認済みだったと偽装しない。
- 最新画面はAIレポート日、対象市場日、市場取得時刻、日本株実績日、ニュース確認時刻を分ける。
- AIレポートが古い場合は「更新待ち」を表示し、最新分析と誤認させない。

## 完了

ローカル検証、全テスト、PR、GitHub Actions、main、Vercel、本番画面の日時・判定・内容を確認して完了とする。
