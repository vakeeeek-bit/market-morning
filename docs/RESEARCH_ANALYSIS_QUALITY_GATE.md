# Research & Analysis Quality Gate v1

## 目的

情報量ではなく、調査の網羅性、因果分析の連続性、反証確認、日本株への伝達精度を公開条件にする。本文へ掲載しない調査も `data/research-evidence.json` に記録する。

## Gate 1: Research Quality

固定Universe、当日ニュース横断、市場異常値からの逆引き、前日認識との差分の4方向を毎日確認する。

各項目は `取得済 / 十分調査したが取得不能 / 該当材料なし / 未調査` のいずれかとする。未調査は重要度にかかわらずFAIL。「該当材料なし」は1件以上の調査試行、「十分調査したが取得不能」は2件以上の調査試行と分析影響評価を必須とする。

| 強度 | 取得不能時の扱い |
|---|---|
| Critical | FAIL。公開不可 |
| Required | 複数の調査証跡と影響評価がある場合だけ例外許容 |
| Supplemental | 調査証跡があれば全体を止めない |

アナリストの格上げ・格下げ・新規カバレッジ・目標株価・EPS/業績予想変更はRequired。網羅できない日は「変更なし」と断定しない。

## Gate 2: Analysis Quality

重要材料ごとに、確認された事実と出典、実際の市場反応、市場内部、市場の織り込み、解釈と確信度、日本株への途中経路、相反材料、観測可能な変更条件、時系列確認を順に記録する。

ニュースの発生と、そのニュースによる市場反応を分離する。確信度は `confirmed / supported / tentative / unknown`、織り込みは `priced / partially_priced / unpriced / unknown` で内部管理する。

Cross-Asset監査は株・金利・為替・商品・暗号資産を必須対象とし、同時に起きた一見矛盾する値動きを記録・説明する。単一資産だけの結論は不可。

## Gate 3: Independent / Counter-Evidence Audit

主要結論ごとに、結論を否定・弱化する確認対象、両方向の力の比較、残る不確実性を記録する。「反証なし」は空欄ではなく、何を確認したかを残す。

## テンプレート劣化監査

今日固有の分析、前日レポートとの比較、実際の市場反応、複数資産、相反材料、日本株への伝達経路、観測可能な変更条件をすべて確認し、前日文章から何を変えたかを `comparison_note` に記録する。

## 公開条件

Research Coverage / Source Quality / Data Integrity / Analysis Logic / Cross-Asset Consistency / Japan Transmission / Counter-Evidence Audit / Previous-Day Change / Final Content Audit の9項目がすべてPASSでなければ `scripts/prepare_publish.py` は公開候補を `data/` へ配置しない。

新しい日次作業は `python scripts/create_research_evidence.py` でFAIL状態のワークシートを作る。調査者が証拠と分析を入力し、全ゲートを明示的にPASSへ変えるまで公開できない。

## レーティング情報源の実装判断

| 候補 | 網羅性・更新 | 自動取得 | 利用条件・判断 |
|---|---|---|---|
| QUICK Analyst Rating and Target Price / QUICK Consensus | 日本上場企業向け。旧新レーティング・旧新目標株価・更新日時。Consensusは日次 | 契約データ/API | 日本株日次運用の第一候補。契約・再配信条件確認後に実装 |
| IFIS News / Consensus Data Service | レーティング、目標株価、業績予想変更。日本株特化 | 契約サービス、バルク等 | 有力候補。契約・Web掲載権を確認後に実装 |
| LSEG I/B/E/S | グローバルな明細・コンセンサス | API/Workspace | 網羅性は高いが、日本株だけの用途には費用・契約が過大になり得る |
| 無料公開サイト・報道 | 確認できた変更の補足 | 安定自動取得を保証できない | 網羅性、更新速度、権利を保証できないため「変更なし」の根拠にはしない |

証券レポート本文や公開サイトを無断で収集・再配信する設計にはしない。契約前は、公開情報で確認できた重要変更のみ出典付きで掲載する。

## 回帰テスト

- 個別株調査を `未調査` にするとResearch GateがFAIL
- SOXだけを確認し、日本側への途中経路・反証・時系列を欠くとAnalysis GateがFAIL
- Requiredの取得不能で調査試行が1件だけ、または影響評価が空ならFAIL
- Counter-Evidence Auditが空ならFAIL
- 調査証跡ファイルが無い公開候補はFAIL
- 最終9ゲートの1項目でもFAILなら、既存ファイルを変更しない
